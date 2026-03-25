"""Schemas Pydantic para requests y responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    CategoriaNoticia,
    EstadoNoticia,
    EstadoPublicacion,
    RolPanel,
    TipoCanal,
    UrgenciaNoticia,
)


class CanalBase(BaseModel):
    """Datos base de un canal."""

    nombre: str = Field(max_length=100)
    tipo: TipoCanal
    activo: bool = True
    auto_publicar: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    orden: int = 0

    @model_validator(mode="before")
    @classmethod
    def _migrar_config_json(cls, values: Any) -> Any:
        """Acepta payloads legacy con config_json."""

        if isinstance(values, dict) and "config" not in values and "config_json" in values:
            values = dict(values)
            raw = values.pop("config_json")
            if isinstance(raw, str):
                import json

                values["config"] = json.loads(raw) if raw else {}
        return values


class CanalCreate(CanalBase):
    """Payload para crear un canal."""


class CanalUpdate(BaseModel):
    """Payload para actualizar un canal."""

    nombre: str | None = Field(default=None, max_length=100)
    activo: bool | None = None
    auto_publicar: bool | None = None
    config: dict[str, Any] | None = None
    orden: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrar_config_json(cls, values: Any) -> Any:
        """Acepta payloads legacy con config_json."""

        if isinstance(values, dict) and "config" not in values and "config_json" in values:
            values = dict(values)
            raw = values.pop("config_json")
            if isinstance(raw, str):
                import json

                values["config"] = json.loads(raw) if raw else {}
        return values


class CanalRead(CanalBase):
    """Respuesta pública de un canal."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class PublicacionBase(BaseModel):
    """Datos base editables de una publicación."""

    contenido: str | None = None


class PublicacionUpdate(PublicacionBase):
    """Payload para actualizar una publicación."""


class PublicacionRead(BaseModel):
    """Respuesta de publicación."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    noticia_id: int
    canal_id: int
    contenido: str | None
    imagen_path: str | None
    estado: EstadoPublicacion
    auto_publicar: bool
    external_id: str | None
    external_url: str | None
    publicado_at: datetime | None
    error_log: str | None
    created_at: datetime
    canal: CanalRead


class NoticiaBase(BaseModel):
    """Campos base de una noticia."""

    hecho: str
    lugar: str | None = Field(default=None, max_length=200)
    fecha_hecho: datetime | None = None
    categoria: CategoriaNoticia = CategoriaNoticia.general
    urgencia: UrgenciaNoticia = UrgenciaNoticia.normal


class NoticiaCreate(NoticiaBase):
    """Payload para crear una noticia."""


class NoticiaUpdate(BaseModel):
    """Payload para editar una noticia."""

    hecho: str | None = None
    lugar: str | None = Field(default=None, max_length=200)
    fecha_hecho: datetime | None = None
    categoria: CategoriaNoticia | None = None
    urgencia: UrgenciaNoticia | None = None
    titular: str | None = Field(default=None, max_length=200)
    bajada: str | None = None
    cuerpo: str | None = None
    programada_para: datetime | None = None
    estado: EstadoNoticia | None = None


class GeneracionContenido(BaseModel):
    """Respuesta estructurada del servicio de IA."""

    titular: str
    bajada: str
    cuerpo: str
    facebook: str
    instagram: str
    twitter: str
    whatsapp: str
    telegram: str


class NoticiaRead(BaseModel):
    """Respuesta de noticia con publicaciones."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hecho: str
    lugar: str | None
    fecha_hecho: datetime
    categoria: CategoriaNoticia
    urgencia: UrgenciaNoticia
    imagen_original: str | None
    titular: str | None
    bajada: str | None
    cuerpo: str | None
    generado_at: datetime | None
    aprobado_at: datetime | None
    programada_para: datetime | None
    estado: EstadoNoticia
    created_at: datetime
    updated_at: datetime
    publicaciones: list[PublicacionRead] = Field(default_factory=list)


class DespachoFormData(BaseModel):
    """Datos mínimos del flujo expreso."""

    hecho: str
    lugar: str | None = None
    categoria: CategoriaNoticia = CategoriaNoticia.general
    urgencia: UrgenciaNoticia = UrgenciaNoticia.normal


class PublicacionResultado(BaseModel):
    """Resultado unificado de publicación externa."""

    id: str | None
    url: str | None
    exito: bool
    error: str | None


class AppInfo(BaseModel):
    """Metadata básica de la aplicación."""

    app: str
    env: str
    version: str
    status: str


class IntegracionStatus(BaseModel):
    """Estado resumido de una integración externa."""

    nombre: str
    ok: bool
    detalle: str


class PreflightCanalStatus(BaseModel):
    """Estado de preparación de una noticia para un canal."""

    canal_id: int
    canal_nombre: str
    canal_tipo: TipoCanal
    listo: bool
    auto_publicar: bool
    detalle: str
    publicacion_id: int | None = None


class PreflightNoticiaStatus(BaseModel):
    """Resultado completo de preflight por noticia."""

    noticia_id: int
    lista_para_publicar: bool
    requiere_aprobacion: bool
    programada_para: datetime | None
    detalle_general: str
    canales: list[PreflightCanalStatus]


class ProgramacionPayload(BaseModel):
    """Payload para programar una noticia."""

    programada_para: datetime


class PanelNoticiaEstadoUpdate(BaseModel):
    """Payload para actualizar manualmente el estado editorial desde el panel."""

    estado: EstadoNoticia


class PanelEditorialUpdate(BaseModel):
    """Payload para editar contenido editorial principal desde el panel."""

    titular: str | None = Field(default=None, max_length=200)
    bajada: str | None = None
    cuerpo: str | None = None


class PanelPublicacionEstadoUpdate(BaseModel):
    """Payload para actualizar manualmente el estado de una publicacion desde el panel."""

    estado: EstadoPublicacion
    external_url: str | None = None
    error_log: str | None = None


class AuthLoginPayload(BaseModel):
    """Credenciales simples del panel."""

    username: str
    password: str


class AuthTokenResponse(BaseModel):
    """Token de acceso para el panel."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: "PanelUserRead"


class RefreshTokenPayload(BaseModel):
    """Payload para renovar sesión del panel."""

    refresh_token: str


class LogoutPayload(BaseModel):
    """Payload para revocar una sesión del panel."""

    refresh_token: str | None = None


class DashboardResumen(BaseModel):
    """Resumen principal para el panel."""

    noticias_por_estado: dict[str, int]
    publicaciones_por_estado: dict[str, int]
    noticias_programadas: list[NoticiaRead]
    noticias_recientes: list[NoticiaRead]
    integraciones: list[IntegracionStatus]


class PanelUserBase(BaseModel):
    """Campos base de usuario del panel."""

    username: str = Field(min_length=3, max_length=100)
    role: RolPanel = RolPanel.editor
    activo: bool = True


class PanelUserCreate(PanelUserBase):
    """Payload para crear usuario del panel."""

    password: str = Field(min_length=6, max_length=200)


class PanelUserUpdate(BaseModel):
    """Payload para editar usuario del panel."""

    username: str | None = Field(default=None, min_length=3, max_length=100)
    password: str | None = Field(default=None, min_length=6, max_length=200)
    role: RolPanel | None = None
    activo: bool | None = None


class PanelUserRead(BaseModel):
    """Respuesta pública de usuario del panel."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: RolPanel
    activo: bool
    created_at: datetime
    last_login_at: datetime | None


class PanelProfile(BaseModel):
    """Perfil autenticado actual para hidratar el panel."""

    user: PanelUserRead
    permissions: list[str]


class PanelUsersPage(BaseModel):
    """Listado paginado de usuarios del panel."""

    items: list[PanelUserRead]
    total: int
    page: int
    page_size: int


class PanelSessionRead(BaseModel):
    """Sesión visible del panel."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None


class PanelSessionsPage(BaseModel):
    """Listado paginado de sesiones del panel."""

    items: list[PanelSessionRead]
    total: int
    page: int
    page_size: int


class PanelNoticiasPage(BaseModel):
    """Listado paginado de noticias para el panel."""

    items: list[NoticiaRead]
    total: int
    page: int
    page_size: int


class TimelineEvento(BaseModel):
    """Evento del timeline editorial."""

    evento: str
    fecha: datetime
    detalle: str


class PublicacionTimeline(BaseModel):
    """Timeline de una publicacion individual."""

    publicacion_id: int
    canal_nombre: str
    canal_tipo: TipoCanal
    eventos: list[TimelineEvento]


class PanelFeedItem(BaseModel):
    """Evento o notificación del panel."""

    id: str
    tipo: str
    titulo: str
    descripcion: str
    fecha: datetime
    severidad: str = "info"
    noticia_id: int | None = None


class PanelNoticiaDetalle(BaseModel):
    """Detalle completo de una noticia para el panel."""

    noticia: NoticiaRead
    timeline: list[TimelineEvento]
    publicaciones_timeline: list[PublicacionTimeline]
    preflight: PreflightNoticiaStatus


class QuickPublishResult(BaseModel):
    """Resultado rápido de publicación desde el panel."""

    noticia: NoticiaRead
    publicaciones: list[PublicacionRead]


AuthTokenResponse.model_rebuild()
