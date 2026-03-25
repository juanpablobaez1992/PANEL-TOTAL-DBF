"""Routers HTTP del panel administrativo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.utils.limiter import panel_limiter as _limiter

from app.controllers import (
    auth_controller,
    dashboard_controller,
    noticia_controller,
    panel_session_controller,
    panel_user_controller,
    publicacion_controller,
)
from app.database import get_db
from app.models.schemas import (
    AuthLoginPayload,
    AuthTokenResponse,
    DashboardResumen,
    LogoutPayload,
    NoticiaCreate,
    NoticiaRead,
    NoticiaUpdate,
    PanelEditorialUpdate,
    PanelFeedItem,
    PanelNoticiaEstadoUpdate,
    PanelNoticiaDetalle,
    PanelNoticiasPage,
    PanelProfile,
    PanelPublicacionEstadoUpdate,
    PanelSessionsPage,
    PanelUserCreate,
    PanelUserRead,
    PanelUsersPage,
    PanelUserUpdate,
    PreflightNoticiaStatus,
    PublicacionUpdate,
    ProgramacionPayload,
    QuickPublishResult,
    RefreshTokenPayload,
)
from app.views.dependencies import get_current_panel_user, require_permission
from app.utils.permissions import list_permissions

router = APIRouter(prefix="/api/panel", tags=["Panel"])


@router.post("/auth/login", response_model=AuthTokenResponse)
@_limiter.limit("5/minute")
async def login(
    payload: AuthLoginPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    """Autentica al usuario del panel. Máximo 5 intentos por minuto por IP."""

    try:
        return auth_controller.login_panel(db, payload.username, payload.password, request.headers.get("user-agent"))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.post("/auth/refresh", response_model=AuthTokenResponse)
async def refresh_session(payload: RefreshTokenPayload, db: Session = Depends(get_db)) -> AuthTokenResponse:
    """Renueva una sesión de panel."""

    try:
        return auth_controller.refresh_panel_session(db, payload.refresh_token)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_session(payload: LogoutPayload, db: Session = Depends(get_db)) -> None:
    """Revoca una sesión usando refresh token."""

    if not payload.refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token es requerido.")
    try:
        auth_controller.logout_panel_session(db, payload.refresh_token)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/me", response_model=PanelProfile)
async def me(
    user_payload: dict[str, object] = Depends(get_current_panel_user),
    db: Session = Depends(get_db),
) -> PanelProfile:
    """Devuelve el perfil actual del usuario autenticado."""

    user = panel_user_controller.get_user_by_id(db, int(user_payload["uid"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return PanelProfile(user=PanelUserRead.model_validate(user), permissions=list_permissions(user.role.value))


@router.get("/dashboard", response_model=DashboardResumen)
async def dashboard(
    _user: dict[str, object] = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> DashboardResumen:
    """Devuelve el resumen principal del panel."""

    return await dashboard_controller.obtener_dashboard(db)


@router.get("/actividad", response_model=list[PanelFeedItem])
async def actividad(
    _user: dict[str, object] = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> list[PanelFeedItem]:
    """Devuelve actividad reciente del panel."""

    return dashboard_controller.listar_actividad_panel(db)


@router.get("/notificaciones", response_model=list[PanelFeedItem])
async def notificaciones(
    _user: dict[str, object] = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> list[PanelFeedItem]:
    """Devuelve notificaciones borrador del panel."""

    return dashboard_controller.listar_notificaciones_panel(db)


@router.get("/sesiones", response_model=PanelSessionsPage)
async def listar_sesiones(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    solo_activas: bool = False,
    _user: dict[str, object] = Depends(require_permission("sessions.view")),
    db: Session = Depends(get_db),
) -> PanelSessionsPage:
    """Lista sesiones revocables del panel."""

    items, total = panel_session_controller.list_sessions_paginated(
        db,
        page,
        page_size,
        q=q,
        solo_activas=solo_activas,
    )
    return PanelSessionsPage(items=items, total=total, page=page, page_size=page_size)


@router.post("/sesiones/revocar/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revocar_sesion(
    session_id: int,
    _user: dict[str, object] = Depends(require_permission("sessions.revoke")),
    db: Session = Depends(get_db),
) -> None:
    """Revoca una sesión específica del panel."""

    session = panel_session_controller.get_active_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")
    panel_session_controller.revoke_session(db, session)


@router.get("/usuarios", response_model=PanelUsersPage)
async def listar_usuarios(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    activo: bool | None = None,
    _user: dict[str, object] = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> PanelUsersPage:
    """Lista usuarios del panel."""

    items, total = panel_user_controller.list_users_paginated(
        db,
        page,
        page_size,
        q=q,
        activo=activo,
    )
    return PanelUsersPage(items=items, total=total, page=page, page_size=page_size)


@router.post("/usuarios", response_model=PanelUserRead, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    payload: PanelUserCreate,
    _user: dict[str, object] = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> PanelUserRead:
    """Crea un usuario editor/admin del panel."""

    try:
        return panel_user_controller.create_user(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.put("/usuarios/{user_id}", response_model=PanelUserRead)
async def actualizar_usuario(
    user_id: int,
    payload: PanelUserUpdate,
    _user: dict[str, object] = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> PanelUserRead:
    """Actualiza un usuario del panel."""

    try:
        return panel_user_controller.update_user(db, user_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias", response_model=PanelNoticiaDetalle, status_code=status.HTTP_201_CREATED)
async def crear_noticia_panel(
    payload: NoticiaCreate,
    _user: dict[str, object] = Depends(require_permission("noticias.edit_content")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Crea una noticia en borrador desde el panel."""

    noticia = noticia_controller.create_noticia(db, payload)
    return dashboard_controller.obtener_detalle_noticia_panel(db, noticia.id)


@router.post("/noticias/{noticia_id}/imagen", response_model=NoticiaRead)
async def subir_imagen_panel(
    noticia_id: int,
    archivo: UploadFile = File(...),
    _user: dict[str, object] = Depends(require_permission("noticias.edit_content")),
    db: Session = Depends(get_db),
) -> NoticiaRead:
    """Sube o reemplaza la imagen original de una noticia desde el panel."""

    try:
        return await noticia_controller.upload_noticia_image(db, noticia_id, archivo)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/noticias", response_model=PanelNoticiasPage)
async def listar_noticias_panel(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = None,
    categoria: str | None = None,
    q: str | None = None,
    solo_programadas: bool = False,
    _user: dict[str, object] = Depends(require_permission("noticias.view")),
    db: Session = Depends(get_db),
) -> PanelNoticiasPage:
    """Lista paginada de noticias para el panel."""

    return dashboard_controller.listar_noticias_panel(
        db,
        page=page,
        page_size=page_size,
        estado=estado,
        categoria=categoria,
        q=q,
        solo_programadas=solo_programadas,
    )


@router.get("/noticias/{noticia_id}", response_model=PanelNoticiaDetalle)
async def detalle_noticia_panel(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.view")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Detalle editorial completo de una noticia para el panel."""

    try:
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/noticias/{noticia_id}/estado", response_model=PanelNoticiaDetalle)
async def actualizar_estado_noticia_panel(
    noticia_id: int,
    payload: PanelNoticiaEstadoUpdate,
    _user: dict[str, object] = Depends(require_permission("noticias.edit_state")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Actualiza manualmente el estado editorial de una noticia desde el panel."""

    try:
        noticia_controller.cambiar_estado_editorial_noticia(db, noticia_id, payload.estado)
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.patch("/noticias/{noticia_id}/editorial", response_model=PanelNoticiaDetalle)
async def actualizar_editorial_noticia_panel(
    noticia_id: int,
    payload: PanelEditorialUpdate,
    _user: dict[str, object] = Depends(require_permission("noticias.edit_content")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Actualiza titular, bajada y cuerpo de una noticia desde el panel."""

    try:
        noticia_controller.update_noticia(
            db,
            noticia_id,
            NoticiaUpdate(**payload.model_dump(exclude_unset=True)),
        )
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias/{noticia_id}/acciones/generar", response_model=PanelNoticiaDetalle)
async def accion_generar(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.generate")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Acción rápida: generar contenido de la noticia."""

    try:
        await noticia_controller.generar_noticia(db, noticia_id)
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias/{noticia_id}/acciones/aprobar", response_model=PanelNoticiaDetalle)
async def accion_aprobar(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.approve")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Acción rápida: aprobar noticia."""

    try:
        noticia_controller.aprobar_noticia(db, noticia_id)
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/noticias/{noticia_id}/acciones/preflight", response_model=PreflightNoticiaStatus)
async def accion_preflight(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.preflight")),
    db: Session = Depends(get_db),
) -> PreflightNoticiaStatus:
    """Acción rápida: obtener preflight completo."""

    try:
        return noticia_controller.obtener_preflight_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias/{noticia_id}/acciones/programar", response_model=PanelNoticiaDetalle)
async def accion_programar(
    noticia_id: int,
    payload: ProgramacionPayload,
    _user: dict[str, object] = Depends(require_permission("noticias.schedule")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Acción rápida: programar noticia."""

    try:
        noticia_controller.programar_noticia(db, noticia_id, payload.programada_para)
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias/{noticia_id}/acciones/cancelar-programacion", response_model=PanelNoticiaDetalle)
async def accion_cancelar_programacion(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.schedule")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Acción rápida: cancelar programación."""

    try:
        noticia_controller.cancelar_programacion_noticia(db, noticia_id)
        return dashboard_controller.obtener_detalle_noticia_panel(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/noticias/{noticia_id}/acciones/publicar", response_model=QuickPublishResult)
async def accion_publicar(
    noticia_id: int,
    _user: dict[str, object] = Depends(require_permission("noticias.publish")),
    db: Session = Depends(get_db),
) -> QuickPublishResult:
    """Acción rápida: publicar noticia y devolver resultado por canal."""

    try:
        noticia, publicaciones = await publicacion_controller.ejecutar_publicacion_rapida(db, noticia_id)
        return QuickPublishResult(noticia=noticia, publicaciones=publicaciones)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.patch("/publicaciones/{publicacion_id}", response_model=PanelNoticiaDetalle)
async def actualizar_publicacion_panel(
    publicacion_id: int,
    payload: PublicacionUpdate,
    _user: dict[str, object] = Depends(require_permission("publicaciones.edit")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Actualiza el copy de una publicación desde el panel."""

    try:
        publicacion = publicacion_controller.update_publicacion(db, publicacion_id, payload)
        return dashboard_controller.obtener_detalle_noticia_panel(db, publicacion.noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.patch("/publicaciones/{publicacion_id}/estado", response_model=PanelNoticiaDetalle)
async def actualizar_estado_publicacion_panel(
    publicacion_id: int,
    payload: PanelPublicacionEstadoUpdate,
    _user: dict[str, object] = Depends(require_permission("publicaciones.edit_state")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Actualiza manualmente el estado de una publicacion desde el panel."""

    try:
        publicacion = publicacion_controller.cambiar_estado_publicacion_panel(db, publicacion_id, payload)
        return dashboard_controller.obtener_detalle_noticia_panel(db, publicacion.noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/publicaciones/{publicacion_id}/publicar", response_model=PanelNoticiaDetalle)
async def publicar_publicacion_panel(
    publicacion_id: int,
    _user: dict[str, object] = Depends(require_permission("publicaciones.publish")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Publica un canal individual desde el panel."""

    try:
        publicacion = await publicacion_controller.publicar_individual(db, publicacion_id)
        return dashboard_controller.obtener_detalle_noticia_panel(db, publicacion.noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/publicaciones/{publicacion_id}/reintentar", response_model=PanelNoticiaDetalle)
async def reintentar_publicacion_panel(
    publicacion_id: int,
    _user: dict[str, object] = Depends(require_permission("publicaciones.publish")),
    db: Session = Depends(get_db),
) -> PanelNoticiaDetalle:
    """Reintenta una publicacion con error desde el panel."""

    publicacion = publicacion_controller.get_publicacion(db, publicacion_id)
    if publicacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada.")
    if publicacion.estado != publicacion_controller.EstadoPublicacion.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede reintentar una publicación en estado error.",
        )

    try:
        actualizada = await publicacion_controller.publicar_individual(
            db,
            publicacion_id,
            validar_aprobacion=False,
        )
        return dashboard_controller.obtener_detalle_noticia_panel(db, actualizada.noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
