"""Enums compartidos por los modelos y schemas."""

from __future__ import annotations

import enum


class CategoriaNoticia(str, enum.Enum):
    """Categorías editoriales de noticias."""

    politica = "politica"
    iglesia = "iglesia"
    sociedad = "sociedad"
    deportes = "deportes"
    general = "general"


class UrgenciaNoticia(str, enum.Enum):
    """Niveles de urgencia de una noticia."""

    breaking = "breaking"
    normal = "normal"
    programada = "programada"


class EstadoNoticia(str, enum.Enum):
    """Estados del flujo editorial de una noticia."""

    borrador = "borrador"
    generando = "generando"
    generado = "generado"
    aprobado = "aprobado"
    publicado = "publicado"
    error = "error"


class EstadoPublicacion(str, enum.Enum):
    """Estados de una publicación por canal."""

    pendiente = "pendiente"
    publicado = "publicado"
    error = "error"
    omitido = "omitido"


class TipoCanal(str, enum.Enum):
    """Tipos de canal soportados."""

    wordpress = "wordpress"
    facebook = "facebook"
    instagram = "instagram"
    twitter = "twitter"
    whatsapp = "whatsapp"
    telegram = "telegram"


class RolPanel(str, enum.Enum):
    """Roles básicos para el panel administrativo."""

    admin = "admin"
    editor = "editor"
