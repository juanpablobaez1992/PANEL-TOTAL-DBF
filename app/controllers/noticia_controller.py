"""Controlador de noticias."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.controllers.canal_controller import list_canales
from app.models.noticia import Noticia
from app.models.noticia_log import NoticiaLog
from app.models.publicacion import Publicacion
from app.models.enums import EstadoNoticia, EstadoPublicacion, TipoCanal
from app.models.schemas import (
    DespachoFormData,
    NoticiaCreate,
    NoticiaUpdate,
    PreflightCanalStatus,
    PreflightNoticiaStatus,
)
from app.services.ai_service import generar_contenido
from app.services.imagen_service import procesar_imagenes_por_canal
from app.utils.file_storage import save_upload_file

def _log(db: Session, noticia_id: int, accion: str, detalle: str | None = None, usuario: str = "sistema") -> None:
    """Registra una entrada de auditoría para una noticia."""

    db.add(NoticiaLog(noticia_id=noticia_id, accion=accion, detalle=detalle, usuario=usuario))


CHANNEL_CONTENT_MAP = {
    "wordpress": "cuerpo",
    "facebook": "facebook",
    "instagram": "instagram",
    "twitter": "twitter",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
}


def list_noticias(db: Session, estado: str | None = None) -> Sequence[Noticia]:
    """Lista noticias con filtro opcional por estado."""

    stmt = select(Noticia).options(
        selectinload(Noticia.publicaciones).selectinload(Publicacion.canal),
    ).order_by(Noticia.created_at.desc())
    if estado:
        stmt = stmt.where(Noticia.estado == EstadoNoticia(estado))
    return list(db.scalars(stmt).unique())


def aprobar_noticia(db: Session, noticia_id: int) -> Noticia:
    """Marca una noticia como aprobada para publicación manual."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    if noticia.estado == EstadoNoticia.borrador:
        raise ValueError("La noticia todavía está en borrador y no puede aprobarse.")
    if noticia.estado == EstadoNoticia.generando:
        raise ValueError("La noticia sigue generándose y no puede aprobarse todavía.")
    if not noticia.titular or not noticia.bajada or not noticia.cuerpo:
        raise ValueError("La noticia debe tener titular, bajada y cuerpo antes de aprobarse.")

    noticia.estado = EstadoNoticia.aprobado
    noticia.aprobado_at = datetime.now(timezone.utc)
    _log(db, noticia_id, "aprobar", f"estado anterior: {noticia.estado.value}")
    db.commit()
    return get_noticia(db, noticia_id) or noticia


def programar_noticia(db: Session, noticia_id: int, programada_para: datetime) -> Noticia:
    """Programa la publicación futura de una noticia ya aprobada."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    if noticia.estado != EstadoNoticia.aprobado:
        raise ValueError("Solo se pueden programar noticias aprobadas.")
    if programada_para <= datetime.now(timezone.utc):
        raise ValueError("La fecha de programación debe estar en el futuro.")

    noticia.programada_para = programada_para
    _log(db, noticia_id, "programar", f"programada_para: {programada_para.isoformat()}")
    db.commit()
    return get_noticia(db, noticia_id) or noticia


def cancelar_programacion_noticia(db: Session, noticia_id: int) -> Noticia:
    """Cancela una programación pendiente de una noticia."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    noticia.programada_para = None
    db.commit()
    return get_noticia(db, noticia_id) or noticia


def cambiar_estado_editorial_noticia(
    db: Session,
    noticia_id: int,
    nuevo_estado: EstadoNoticia,
) -> Noticia:
    """Actualiza manualmente un estado editorial permitido desde el panel."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")

    if noticia.estado == nuevo_estado:
        return get_noticia(db, noticia_id) or noticia

    if noticia.estado == EstadoNoticia.publicado:
        raise ValueError("No se puede cambiar manualmente el estado de una noticia ya publicada.")

    if nuevo_estado == EstadoNoticia.aprobado:
        return aprobar_noticia(db, noticia_id)

    if nuevo_estado == EstadoNoticia.generado:
        if not noticia.titular or not noticia.bajada or not noticia.cuerpo:
            raise ValueError("La noticia debe tener contenido generado antes de marcarse como generado.")
        noticia.estado = EstadoNoticia.generado
        noticia.aprobado_at = None
        noticia.programada_para = None
        db.commit()
        return get_noticia(db, noticia_id) or noticia

    if nuevo_estado == EstadoNoticia.borrador:
        noticia.estado = EstadoNoticia.borrador
        noticia.aprobado_at = None
        noticia.programada_para = None
        db.commit()
        return get_noticia(db, noticia_id) or noticia

    raise ValueError("Solo se permite actualizar manualmente a borrador, generado o aprobado.")


def get_noticia(db: Session, noticia_id: int) -> Noticia | None:
    """Devuelve una noticia con publicaciones."""

    stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .where(Noticia.id == noticia_id)
    )
    return db.scalar(stmt)


def create_noticia(db: Session, payload: NoticiaCreate) -> Noticia:
    """Crea una noticia en estado borrador."""

    data = payload.model_dump(exclude_none=True)
    noticia = Noticia(**data)
    db.add(noticia)
    db.commit()
    db.refresh(noticia)
    _log(db, noticia.id, "crear")
    db.commit()
    return get_noticia(db, noticia.id) or noticia


def update_noticia(db: Session, noticia_id: int, payload: NoticiaUpdate) -> Noticia:
    """Actualiza una noticia editable."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(noticia, field, value)

    db.commit()
    return get_noticia(db, noticia_id) or noticia


async def upload_noticia_image(db: Session, noticia_id: int, upload: UploadFile) -> Noticia:
    """Guarda la imagen original de una noticia."""

    noticia = db.get(Noticia, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")

    noticia.imagen_original = await save_upload_file(upload, subdir="original")
    db.commit()
    return get_noticia(db, noticia_id) or noticia


def _ensure_publicaciones(
    db: Session,
    *,
    noticia: Noticia,
    generated_content: dict[str, str],
    image_variants: dict[str, str],
) -> None:
    """Crea o actualiza publicaciones según los canales activos."""

    canales = [canal for canal in list_canales(db) if canal.activo]
    existing_publicaciones = list(
        db.scalars(
            select(Publicacion)
            .options(selectinload(Publicacion.canal))
            .where(Publicacion.noticia_id == noticia.id)
        ).unique()
    )
    existing_by_tipo = {pub.canal.tipo.value: pub for pub in existing_publicaciones}

    for canal in canales:
        contenido_key = CHANNEL_CONTENT_MAP[canal.tipo.value]
        contenido = generated_content.get(contenido_key)
        imagen_path = image_variants.get(canal.tipo.value) if noticia.imagen_original else None
        auto_publicar = bool(canal.auto_publicar and settings.auto_publish_global)

        publicacion = existing_by_tipo.get(canal.tipo.value)
        if publicacion:
            publicacion.contenido = contenido
            publicacion.imagen_path = imagen_path
            publicacion.auto_publicar = auto_publicar
            publicacion.error_log = None
            continue

        db.add(
            Publicacion(
                noticia_id=noticia.id,
                canal_id=canal.id,
                contenido=contenido,
                imagen_path=imagen_path,
                auto_publicar=auto_publicar,
            )
        )
    db.flush()


async def generar_noticia(db: Session, noticia_id: int) -> Noticia:
    """Genera contenido IA y publicaciones derivadas."""

    noticia = get_noticia(db, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")

    noticia.estado = EstadoNoticia.generando
    db.commit()

    try:
        contenido = await generar_contenido(
            hecho=noticia.hecho,
            lugar=noticia.lugar,
            categoria=noticia.categoria,
            urgencia=noticia.urgencia,
        )
        image_variants = procesar_imagenes_por_canal(noticia.imagen_original) if noticia.imagen_original else {}
        noticia.titular = contenido.titular
        noticia.bajada = contenido.bajada
        noticia.cuerpo = contenido.cuerpo
        _ensure_publicaciones(
            db,
            noticia=noticia,
            generated_content=contenido.model_dump(),
            image_variants=image_variants,
        )
        noticia.estado = EstadoNoticia.generado
        noticia.generado_at = datetime.now(timezone.utc)
        _log(db, noticia_id, "generar", f"proveedor: {settings.ai_provider}")
        db.commit()
        db.expire_all()
        publicaciones = list(
            db.scalars(select(Publicacion).where(Publicacion.noticia_id == noticia.id))
        )
        if any(publicacion.auto_publicar for publicacion in publicaciones):
            from app.controllers.publicacion_controller import publicar_automaticas

            await publicar_automaticas(db, noticia.id)
    except Exception as error:  # noqa: BLE001
        noticia.estado = EstadoNoticia.error
        _log(db, noticia_id, "generar_error", str(error))
        db.commit()
        raise RuntimeError(f"No se pudo generar la noticia: {error}") from error

    return get_noticia(db, noticia_id) or noticia


def _validar_canal_para_preflight(
    *,
    noticia: Noticia,
    publicacion: Publicacion,
) -> PreflightCanalStatus:
    """Evalúa si una publicación está lista para dispararse por su canal."""

    canal = publicacion.canal
    razones: list[str] = []
    if publicacion.estado == EstadoPublicacion.omitido:
        razones.append("Canal omitido manualmente.")
    if not canal.activo:
        razones.append("Canal desactivado.")
    if not publicacion.contenido:
        razones.append("Falta contenido para el canal.")
    if canal.tipo in {TipoCanal.instagram, TipoCanal.twitter, TipoCanal.facebook} and not publicacion.imagen_path:
        razones.append("Falta imagen procesada para este canal.")
    if canal.tipo == TipoCanal.instagram:
        if "localhost" in settings.public_base_url:
            razones.append("PUBLIC_BASE_URL debe ser pública para Instagram.")
        if not settings.resolved_meta_access_token or not settings.resolved_meta_ig_account_id:
            razones.append("Faltan credenciales de Instagram/Meta.")
    if canal.tipo == TipoCanal.facebook and (not settings.resolved_meta_access_token or not settings.resolved_meta_page_id):
        razones.append("Faltan credenciales de Facebook/Meta.")
    if canal.tipo == TipoCanal.twitter and not all(
        [
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret,
        ]
    ):
        razones.append("Faltan credenciales de Twitter/X.")
    if canal.tipo == TipoCanal.telegram and (not settings.telegram_bot_token or not settings.telegram_chat_id):
        razones.append("Faltan credenciales de Telegram.")
    if canal.tipo == TipoCanal.wordpress and (
        not settings.resolved_wp_url or not settings.wp_user or not settings.wp_app_password
    ):
        razones.append("Faltan credenciales de WordPress.")

    listo = not razones
    return PreflightCanalStatus(
        canal_id=canal.id,
        canal_nombre=canal.nombre,
        canal_tipo=canal.tipo,
        listo=listo,
        auto_publicar=publicacion.auto_publicar,
        detalle="Lista para publicar." if listo else " ".join(razones),
        publicacion_id=publicacion.id,
    )


def obtener_preflight_noticia(db: Session, noticia_id: int) -> PreflightNoticiaStatus:
    """Valida si una noticia está lista para publicarse por canal."""

    noticia = get_noticia(db, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")
    if not noticia.publicaciones:
        raise ValueError("La noticia no tiene publicaciones generadas.")

    canales = [_validar_canal_para_preflight(noticia=noticia, publicacion=pub) for pub in noticia.publicaciones]
    faltantes_generales: list[str] = []
    if noticia.estado not in {EstadoNoticia.aprobado, EstadoNoticia.publicado}:
        faltantes_generales.append("La noticia todavía no está aprobada.")
    if not noticia.titular or not noticia.bajada or not noticia.cuerpo:
        faltantes_generales.append("La noticia debe tener titular, bajada y cuerpo completos.")

    lista = not faltantes_generales and all(item.listo or item.detalle == "Canal omitido manualmente." for item in canales)
    return PreflightNoticiaStatus(
        noticia_id=noticia.id,
        lista_para_publicar=lista,
        requiere_aprobacion=noticia.estado != EstadoNoticia.aprobado,
        programada_para=noticia.programada_para,
        detalle_general="Lista para publicar." if lista else " ".join(faltantes_generales) or "Hay canales con bloqueos.",
        canales=canales,
    )


async def procesar_noticias_programadas(db: Session) -> list[int]:
    """Publica noticias aprobadas cuya fecha programada ya venció."""

    from app.controllers.publicacion_controller import publicar_noticia

    ahora = datetime.now(timezone.utc)
    stmt = (
        select(Noticia.id)
        .where(
            Noticia.programada_para.is_not(None),
            Noticia.programada_para <= ahora,
            Noticia.estado == EstadoNoticia.aprobado,
        )
        .order_by(Noticia.programada_para.asc())
    )
    noticia_ids = list(db.scalars(stmt))
    procesadas: list[int] = []
    for noticia_id in noticia_ids:
        await publicar_noticia(db, noticia_id)
        noticia = db.get(Noticia, noticia_id)
        if noticia is not None:
            noticia.programada_para = None
            _log(db, noticia_id, "publicar_programada", "disparado por scheduler")
            db.commit()
        procesadas.append(noticia_id)
    return procesadas


async def despacho_rapido(
    db: Session,
    *,
    payload: DespachoFormData,
    upload: UploadFile | None,
) -> Noticia:
    """Crea una noticia, sube imagen y genera contenido en un flujo único."""

    noticia = create_noticia(
        db,
        NoticiaCreate(
            hecho=payload.hecho,
            lugar=payload.lugar,
            categoria=payload.categoria,
            urgencia=payload.urgencia,
        ),
    )

    if upload is not None:
        noticia = await upload_noticia_image(db, noticia.id, upload)

    return await generar_noticia(db, noticia.id)
