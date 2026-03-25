"""Schemas Pydantic para requests y responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


class AutomationKpis(BaseModel):
    """KPIs resumidos del modulo AUTOPUBLICATE."""

    total_ejecuciones: int
    exitos_fb: int
    exitos_ig: int
    posts_regulares: int
    posts_evergreen: int


class AutomationLogRead(BaseModel):
    """Registro visible de una ejecucion del bot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    post_id: int | None
    title: str
    is_evergreen: bool
    fb_success: bool
    ig_success: bool
    error_msg: str


class AutomationSchedulerState(BaseModel):
    """Estado operativo del scheduler de automation."""

    regular_enabled: bool
    regular_interval_minutes: int
    regular_next_run_at: datetime | None
    evergreen_enabled: bool
    evergreen_interval_minutes: int
    evergreen_next_run_at: datetime | None
    last_processed_post_id: int


class AutomationDashboardRead(BaseModel):
    """Respuesta principal del dashboard automation."""

    kpis: AutomationKpis
    recent_logs: list[AutomationLogRead]
    scheduler: AutomationSchedulerState
    integrations: list[IntegracionStatus]
    queue_count: int
    accounts_count: int
    rules_count: int


class AutomationQueueItem(BaseModel):
    """Post pendiente en la cola de WordPress."""

    id: int
    title: str
    excerpt: str
    link: str
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class AutomationPreparedPost(BaseModel):
    """Vista previa preparada para publicar."""

    post_id: int
    title: str
    excerpt: str
    link: str
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    utm_link: str
    fb_copy: str
    ig_copy: str
    is_evergreen: bool = False


class AutomationPreparedPublishPayload(BaseModel):
    """Payload editable para publicar una vista previa preparada."""

    post_id: int
    title: str
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    utm_link: str
    fb_copy: str
    ig_copy: str
    is_evergreen: bool = False


class AutomationRunResult(BaseModel):
    """Resultado resumido de una ejecucion manual."""

    message: str
    log: AutomationLogRead


class AutomationAccountCreate(BaseModel):
    """Alta de cuenta extra de Facebook o Instagram."""

    name: str = Field(min_length=2, max_length=120)
    platform: Literal["facebook", "instagram"]
    page_id: str = Field(min_length=2, max_length=120)
    access_token: str = Field(min_length=5)


class AutomationAccountRead(BaseModel):
    """Cuenta visible en UI sin exponer el token."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    page_id: str
    token_hint: str
    created_at: datetime


class AutomationRuleCreate(BaseModel):
    """Alta o actualizacion de regla IA por categoria."""

    category_slug: str = Field(min_length=1, max_length=120)
    prompt_rule: str = Field(min_length=3)


class AutomationRuleRead(BaseModel):
    """Regla IA persistida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_slug: str
    prompt_rule: str
    created_at: datetime
    updated_at: datetime


class AutomationWordPressCategory(BaseModel):
    """Categoria de WordPress para settings evergreen."""

    id: int
    name: str
    slug: str


class AutomationEvergreenSettingsRead(BaseModel):
    """Settings evergreen visibles desde UI."""

    category_ids: list[int]
    categories: list[AutomationWordPressCategory]


class AutomationEvergreenSettingsUpdate(BaseModel):
    """Payload para guardar categorias evergreen."""

    category_ids: list[int] = Field(default_factory=list)


class AutomationSchedulerUpdate(BaseModel):
    """Payload para ajustar el scheduler de automation."""

    regular_enabled: bool | None = None
    regular_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    evergreen_enabled: bool | None = None
    evergreen_interval_minutes: int | None = Field(default=None, ge=15, le=10080)


AuthTokenResponse.model_rebuild()
