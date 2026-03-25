"""Controlador del dashboard del panel."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.controllers.noticia_controller import get_noticia, obtener_preflight_noticia
from app.services.integraciones_service import check_integraciones
from app.models.enums import EstadoNoticia
from app.models.noticia import Noticia
from app.models.publicacion import Publicacion
from app.models.schemas import (
    DashboardResumen,
    PanelFeedItem,
    PanelNoticiaDetalle,
    PanelNoticiasPage,
    PublicacionTimeline,
    TimelineEvento,
)


def _as_utc(value: datetime) -> datetime:
    """Normaliza datetimes naive a UTC aware para timelines y ordenamientos."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def obtener_dashboard(db: Session) -> DashboardResumen:
    """Construye el resumen principal del panel."""

    noticias_por_estado_rows = db.execute(
        select(Noticia.estado, func.count(Noticia.id)).group_by(Noticia.estado)
    ).all()
    publicaciones_por_estado_rows = db.execute(
        select(Publicacion.estado, func.count(Publicacion.id)).group_by(Publicacion.estado)
    ).all()

    programadas_stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .where(Noticia.programada_para.is_not(None))
        .order_by(Noticia.programada_para.asc())
        .limit(10)
    )
    recientes_stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .order_by(Noticia.created_at.desc())
        .limit(10)
    )

    programadas = list(db.scalars(programadas_stmt).unique())
    recientes = list(db.scalars(recientes_stmt).unique())
    return DashboardResumen(
        noticias_por_estado={row[0].value: row[1] for row in noticias_por_estado_rows},
        publicaciones_por_estado={row[0].value: row[1] for row in publicaciones_por_estado_rows},
        noticias_programadas=programadas,
        noticias_recientes=recientes,
        integraciones=await check_integraciones(),
    )


def listar_noticias_panel(
    db: Session,
    *,
    page: int,
    page_size: int,
    estado: str | None,
    categoria: str | None,
    q: str | None,
    solo_programadas: bool,
) -> PanelNoticiasPage:
    """Lista noticias con filtros y paginación para el panel."""

    stmt = select(Noticia).options(
        selectinload(Noticia.publicaciones).selectinload(Publicacion.canal)
    )
    count_stmt = select(func.count()).select_from(Noticia)

    filters = []
    if estado:
        filters.append(Noticia.estado == estado)
    if categoria:
        filters.append(Noticia.categoria == categoria)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Noticia.hecho.ilike(pattern),
                Noticia.titular.ilike(pattern),
                Noticia.lugar.ilike(pattern),
            )
        )
    if solo_programadas:
        filters.append(Noticia.programada_para.is_not(None))

    for condition in filters:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(Noticia.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).unique())
    return PanelNoticiasPage(items=items, total=total, page=page, page_size=page_size)


def obtener_detalle_noticia_panel(db: Session, noticia_id: int) -> PanelNoticiaDetalle:
    """Devuelve detalle completo de una noticia para el panel."""

    noticia = get_noticia(db, noticia_id)
    if noticia is None:
        raise ValueError("Noticia no encontrada.")

    timeline: list[TimelineEvento] = [
        TimelineEvento(evento="creada", fecha=noticia.created_at, detalle="Noticia creada en borrador."),
    ]
    if noticia.generado_at:
        timeline.append(
            TimelineEvento(
                evento="generada",
                fecha=noticia.generado_at,
                detalle="Contenido generado y publicaciones derivadas creadas.",
            )
        )
    if noticia.aprobado_at:
        timeline.append(
            TimelineEvento(
                evento="aprobada",
                fecha=noticia.aprobado_at,
                detalle="Noticia aprobada para publicación.",
            )
        )
    if noticia.programada_para:
        timeline.append(
            TimelineEvento(
                evento="programada",
                fecha=noticia.programada_para,
                detalle="Publicación diferida por scheduler.",
            )
        )
    for publicacion in sorted(
        [pub for pub in noticia.publicaciones if pub.publicado_at is not None],
        key=lambda item: item.publicado_at or item.created_at,
    ):
        assert publicacion.publicado_at is not None
        timeline.append(
            TimelineEvento(
                evento="publicada",
                fecha=publicacion.publicado_at,
                detalle=f"Canal {publicacion.canal.nombre}: {publicacion.estado.value}.",
            )
        )

    timeline.sort(key=lambda item: _as_utc(item.fecha))
    publicaciones_timeline: list[PublicacionTimeline] = []
    for publicacion in sorted(noticia.publicaciones, key=lambda item: item.id):
        eventos = [
            TimelineEvento(
                evento="creada",
                fecha=publicacion.created_at,
                detalle=f"Publicacion creada para {publicacion.canal.nombre}.",
            )
        ]
        if publicacion.estado.value == "omitido":
            eventos.append(
                TimelineEvento(
                    evento="omitida",
                    fecha=noticia.updated_at,
                    detalle="El canal fue omitido manualmente.",
                )
            )
        if publicacion.estado.value == "error" and publicacion.error_log:
            eventos.append(
                TimelineEvento(
                    evento="error",
                    fecha=noticia.updated_at,
                    detalle=publicacion.error_log,
                )
            )
        if publicacion.publicado_at:
            eventos.append(
                TimelineEvento(
                    evento="publicada",
                    fecha=publicacion.publicado_at,
                    detalle=f"Publicacion enviada a {publicacion.canal.nombre}.",
                )
            )
        eventos.sort(key=lambda item: _as_utc(item.fecha))
        publicaciones_timeline.append(
            PublicacionTimeline(
                publicacion_id=publicacion.id,
                canal_nombre=publicacion.canal.nombre,
                canal_tipo=publicacion.canal.tipo,
                eventos=eventos,
            )
        )
    preflight = obtener_preflight_noticia(db, noticia_id)
    return PanelNoticiaDetalle(
        noticia=noticia,
        timeline=timeline,
        publicaciones_timeline=publicaciones_timeline,
        preflight=preflight,
    )


def listar_actividad_panel(db: Session, limit: int = 20) -> list[PanelFeedItem]:
    """Genera un feed simple de actividad reciente del panel."""

    stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .order_by(Noticia.updated_at.desc())
        .limit(limit)
    )
    noticias = list(db.scalars(stmt).unique())
    items: list[PanelFeedItem] = []
    for noticia in noticias:
        items.append(
            PanelFeedItem(
                id=f"noticia-{noticia.id}-updated",
                tipo="actividad",
                titulo=f"Noticia #{noticia.id} actualizada",
                descripcion=f"Estado actual: {noticia.estado.value}.",
                fecha=noticia.updated_at,
                severidad="info",
                noticia_id=noticia.id,
            )
        )
        if noticia.programada_para:
            items.append(
                PanelFeedItem(
                    id=f"noticia-{noticia.id}-scheduled",
                    tipo="actividad",
                    titulo=f"Noticia #{noticia.id} programada",
                    descripcion="Tiene una publicación programada pendiente.",
                    fecha=noticia.programada_para,
                    severidad="info",
                    noticia_id=noticia.id,
                )
            )
    items.sort(key=lambda item: item.fecha, reverse=True)
    return items[:limit]


def listar_notificaciones_panel(db: Session, limit: int = 20) -> list[PanelFeedItem]:
    """Genera notificaciones borrador para el panel a partir del estado actual."""

    stmt = (
        select(Noticia)
        .options(selectinload(Noticia.publicaciones).selectinload(Publicacion.canal))
        .order_by(Noticia.updated_at.desc())
        .limit(limit)
    )
    noticias = list(db.scalars(stmt).unique())
    notificaciones: list[PanelFeedItem] = []
    for noticia in noticias:
        if noticia.estado == EstadoNoticia.error:
            notificaciones.append(
                PanelFeedItem(
                    id=f"notif-error-{noticia.id}",
                    tipo="notificacion",
                    titulo=f"Noticia #{noticia.id} con errores",
                    descripcion="Hay fallos de publicación o generación para revisar.",
                    fecha=noticia.updated_at,
                    severidad="error",
                    noticia_id=noticia.id,
                )
            )
            continue
        if noticia.estado == EstadoNoticia.generado:
            notificaciones.append(
                PanelFeedItem(
                    id=f"notif-approval-{noticia.id}",
                    tipo="notificacion",
                    titulo=f"Noticia #{noticia.id} lista para revisión",
                    descripcion="El contenido ya fue generado y espera aprobación.",
                    fecha=noticia.updated_at,
                    severidad="warning",
                    noticia_id=noticia.id,
                )
            )
        if noticia.programada_para:
            notificaciones.append(
                PanelFeedItem(
                    id=f"notif-scheduled-{noticia.id}",
                    tipo="notificacion",
                    titulo=f"Noticia #{noticia.id} en cola",
                    descripcion="Hay una publicación programada pendiente en scheduler.",
                    fecha=noticia.programada_para,
                    severidad="info",
                    noticia_id=noticia.id,
                )
            )
    notificaciones.sort(key=lambda item: item.fecha, reverse=True)
    return notificaciones[:limit]
