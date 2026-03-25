"""Controlador de publicaciones multi-canal."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (60, 300, 900)  # 1 min, 5 min, 15 min

from app.models.enums import EstadoNoticia, EstadoPublicacion, TipoCanal
from app.models.noticia import Noticia
from app.models.publicacion import Publicacion
from app.models.schemas import PanelPublicacionEstadoUpdate, PublicacionUpdate
from app.services.facebook_service import publicar_en_facebook, publicar_en_instagram
from app.services.telegram_service import publicar_en_telegram
from app.services.twitter_service import publicar_en_twitter
from app.services.whatsapp_service import publicar_en_whatsapp
from app.services.wordpress_service import publicar_en_wordpress


def get_publicacion(db: Session, publicacion_id: int) -> Publicacion | None:
    """Obtiene una publicación con canal y noticia."""

    stmt = (
        select(Publicacion)
        .options(
            selectinload(Publicacion.canal),
            selectinload(Publicacion.noticia),
        )
        .where(Publicacion.id == publicacion_id)
    )
    return db.scalar(stmt)


def update_publicacion(db: Session, publicacion_id: int, payload: PublicacionUpdate) -> Publicacion:
    """Actualiza el copy de una publicación."""

    publicacion = db.get(Publicacion, publicacion_id)
    if publicacion is None:
        raise ValueError("Publicación no encontrada.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(publicacion, field, value)
    db.commit()
    return get_publicacion(db, publicacion_id) or publicacion


def cambiar_estado_publicacion_panel(
    db: Session,
    publicacion_id: int,
    payload: PanelPublicacionEstadoUpdate,
) -> Publicacion:
    """Actualiza manualmente un estado de publicacion con guardrails de operacion."""

    publicacion = get_publicacion(db, publicacion_id)
    if publicacion is None:
        raise ValueError("Publicación no encontrada.")

    nuevo_estado = payload.estado
    if nuevo_estado == publicacion.estado:
        if payload.external_url is not None:
            publicacion.external_url = payload.external_url
        if payload.error_log is not None:
            publicacion.error_log = payload.error_log
        db.commit()
        return get_publicacion(db, publicacion_id) or publicacion

    if nuevo_estado == EstadoPublicacion.pendiente:
        raise ValueError("No se permite volver manualmente una publicación a pendiente.")

    if nuevo_estado == EstadoPublicacion.omitido:
        if publicacion.estado == EstadoPublicacion.publicado:
            raise ValueError("No se puede omitir una publicación que ya figura como publicada.")
        publicacion.estado = EstadoPublicacion.omitido
        publicacion.error_log = payload.error_log or publicacion.error_log
        publicacion.publicado_at = None
    elif nuevo_estado == EstadoPublicacion.publicado:
        if not publicacion.contenido:
            raise ValueError("La publicación necesita contenido antes de marcarse como publicada.")
        if publicacion.canal.tipo in {TipoCanal.facebook, TipoCanal.instagram, TipoCanal.twitter} and not publicacion.imagen_path:
            raise ValueError("Este canal necesita imagen antes de marcarse como publicado.")
        publicacion.estado = EstadoPublicacion.publicado
        publicacion.publicado_at = publicacion.publicado_at or datetime.now(timezone.utc)
        publicacion.external_url = payload.external_url or publicacion.external_url
        publicacion.error_log = None
    elif nuevo_estado == EstadoPublicacion.error:
        if not payload.error_log:
            raise ValueError("Para marcar error manualmente se debe registrar error_log.")
        publicacion.estado = EstadoPublicacion.error
        publicacion.error_log = payload.error_log
        publicacion.publicado_at = None
    else:
        raise ValueError("Estado manual no soportado para publicaciones.")

    db.commit()
    _actualizar_estado_noticia(db, publicacion.noticia_id)
    return get_publicacion(db, publicacion_id) or publicacion


def omitir_publicacion(db: Session, publicacion_id: int) -> Publicacion:
    """Marca una publicación como omitida."""

    publicacion = db.get(Publicacion, publicacion_id)
    if publicacion is None:
        raise ValueError("Publicación no encontrada.")

    publicacion.estado = EstadoPublicacion.omitido
    db.commit()
    return get_publicacion(db, publicacion_id) or publicacion


async def _dispatch_publicacion(publicacion: Publicacion) -> dict[str, str | bool | None]:
    """Envía una publicación al servicio correcto según su canal."""

    canal_tipo = publicacion.canal.tipo
    contenido = publicacion.contenido or ""
    imagen = publicacion.imagen_path

    if canal_tipo == TipoCanal.wordpress:
        return await publicar_en_wordpress(
            titulo=publicacion.noticia.titular or "Nueva publicación",
            contenido=publicacion.noticia.cuerpo or contenido,
            imagen_path=imagen,
        )
    if canal_tipo == TipoCanal.facebook:
        return await publicar_en_facebook(contenido=contenido, imagen_path=imagen)
    if canal_tipo == TipoCanal.instagram:
        return await publicar_en_instagram(contenido=contenido, imagen_path=imagen)
    if canal_tipo == TipoCanal.twitter:
        return await publicar_en_twitter(contenido=contenido, imagen_path=imagen)
    if canal_tipo == TipoCanal.whatsapp:
        return await publicar_en_whatsapp(contenido=contenido, imagen_path=imagen)
    if canal_tipo == TipoCanal.telegram:
        return await publicar_en_telegram(contenido=contenido, imagen_path=imagen)
    return {"id": None, "url": None, "exito": False, "error": "Canal no soportado."}


_RETRYABLE_ERRORS = ("timeout", "connection", "connect", "network", "temporar", "503", "502", "429")


def _es_error_reintentable(error_msg: str | None) -> bool:
    """Determina si un error es transitorio y merece reintento."""

    if not error_msg:
        return False
    lower = error_msg.lower()
    return any(keyword in lower for keyword in _RETRYABLE_ERRORS)


async def _dispatch_con_reintentos(publicacion: Publicacion) -> dict[str, str | bool | None]:
    """Intenta publicar con hasta 3 reintentos solo ante errores transitorios de red."""

    last_result: dict[str, str | bool | None] = {"id": None, "url": None, "exito": False, "error": "Sin intentos"}
    for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
        last_result = await _dispatch_publicacion(publicacion)
        if last_result["exito"]:
            return last_result
        # Solo reintentar si el error parece transitorio (red, timeout, rate limit)
        if not _es_error_reintentable(str(last_result.get("error") or "")):
            logger.warning(
                "Publicación %d falló con error permanente (sin reintento): %s",
                publicacion.id,
                last_result.get("error"),
            )
            break
        if delay is None:
            break
        logger.warning(
            "Publicación %d falló (intento %d/%d). Reintentando en %ds. Error: %s",
            publicacion.id,
            attempt,
            len(_RETRY_DELAYS) + 1,
            delay,
            last_result.get("error"),
        )
        await asyncio.sleep(delay)
    logger.error(
        "Publicación %d falló definitivamente. Error: %s",
        publicacion.id,
        last_result.get("error"),
    )
    return last_result


def _actualizar_estado_noticia(db: Session, noticia_id: int) -> None:
    """Consolida el estado global de una noticia según sus publicaciones."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        return

    publicaciones = list(
        db.scalars(select(Publicacion).where(Publicacion.noticia_id == noticia.id))
    )
    if not publicaciones:
        db.commit()
        return

    # Si hay publicaciones aún pendientes, no cambiar estado todavía
    has_pending = any(pub.estado == EstadoPublicacion.pendiente for pub in publicaciones)
    if has_pending:
        db.commit()
        return

    # Todas procesadas (publicado, omitido, error)
    if all(pub.estado in {EstadoPublicacion.publicado, EstadoPublicacion.omitido} for pub in publicaciones):
        noticia.estado = EstadoNoticia.publicado
        noticia.programada_para = None
    else:
        # Alguna falló (puede haber mix de publicado+error, o todo error)
        noticia.estado = EstadoNoticia.error
    db.commit()


async def publicar_individual(
    db: Session,
    publicacion_id: int,
    *,
    validar_aprobacion: bool = True,
) -> Publicacion:
    """Publica una publicación individual en su canal."""

    publicacion = get_publicacion(db, publicacion_id)
    if publicacion is None:
        raise ValueError("Publicación no encontrada.")
    if publicacion.estado == EstadoPublicacion.omitido:
        raise ValueError("La publicación está omitida y no puede publicarse.")
    noticia_actual = db.get(Noticia, publicacion.noticia_id)
    if (
        validar_aprobacion
        and not publicacion.auto_publicar
        and (
            noticia_actual is None
            or noticia_actual.estado not in {EstadoNoticia.aprobado, EstadoNoticia.publicado}
        )
    ):
        raise ValueError("La noticia debe estar aprobada antes de publicar manualmente.")

    result = await _dispatch_con_reintentos(publicacion)
    publicacion.external_id = result["id"]
    publicacion.external_url = result["url"]
    publicacion.error_log = result["error"]

    if result["exito"]:
        publicacion.estado = EstadoPublicacion.publicado
        publicacion.publicado_at = datetime.now(timezone.utc)
    else:
        publicacion.estado = EstadoPublicacion.error

    db.commit()
    _actualizar_estado_noticia(db, publicacion.noticia_id)

    return get_publicacion(db, publicacion_id) or publicacion


async def publicar_noticia(db: Session, noticia_id: int) -> list[Publicacion]:
    """Publica todas las publicaciones pendientes de una noticia."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    if noticia.estado not in {EstadoNoticia.aprobado, EstadoNoticia.publicado}:
        raise ValueError("La noticia debe estar aprobada antes de publicar.")

    stmt = (
        select(Publicacion)
        .options(selectinload(Publicacion.canal), selectinload(Publicacion.noticia))
        .where(Publicacion.noticia_id == noticia_id)
        .order_by(Publicacion.id)
    )
    publicaciones = list(db.scalars(stmt).unique())
    if not publicaciones:
        raise ValueError("La noticia no tiene publicaciones generadas.")

    publicacion_ids = [publicacion.id for publicacion in publicaciones]
    results: list[Publicacion] = []
    for publicacion_id in publicacion_ids:
        publicacion = get_publicacion(db, publicacion_id)
        if publicacion is None:
            continue
        if publicacion.estado == EstadoPublicacion.omitido:
            results.append(publicacion)
            continue
        results.append(
            await publicar_individual(db, publicacion.id, validar_aprobacion=False)
        )
    _actualizar_estado_noticia(db, noticia_id)
    return results


async def publicar_automaticas(db: Session, noticia_id: int) -> list[Publicacion]:
    """Publica solo las publicaciones marcadas para auto publicación."""

    stmt = (
        select(Publicacion)
        .options(selectinload(Publicacion.canal), selectinload(Publicacion.noticia))
        .where(Publicacion.noticia_id == noticia_id, Publicacion.auto_publicar.is_(True))
        .order_by(Publicacion.id)
    )
    publicaciones = list(db.scalars(stmt).unique())
    publicacion_ids = [publicacion.id for publicacion in publicaciones]
    results: list[Publicacion] = []
    for publicacion_id in publicacion_ids:
        publicacion = get_publicacion(db, publicacion_id)
        if publicacion is None:
            continue
        if publicacion.estado in {EstadoPublicacion.omitido, EstadoPublicacion.publicado}:
            results.append(publicacion)
            continue
        results.append(
            await publicar_individual(db, publicacion.id, validar_aprobacion=False)
        )
    _actualizar_estado_noticia(db, noticia_id)
    return results


async def ejecutar_publicacion_rapida(db: Session, noticia_id: int) -> tuple[Noticia, list[Publicacion]]:
    """Publica una noticia y devuelve noticia actualizada más publicaciones resultantes."""

    publicaciones = await publicar_noticia(db, noticia_id)
    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .where(Noticia.id == noticia_id)
    )
    noticia_detalle = db.scalar(stmt) or noticia
    return noticia_detalle, publicaciones
