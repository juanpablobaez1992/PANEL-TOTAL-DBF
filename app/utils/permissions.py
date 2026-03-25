"""Permisos simples por rol para el panel."""

from __future__ import annotations

from app.models.enums import RolPanel

ROLE_PERMISSIONS: dict[RolPanel, set[str]] = {
    RolPanel.admin: {
        "dashboard.view",
        "noticias.view",
        "noticias.generate",
        "noticias.approve",
        "noticias.schedule",
        "noticias.publish",
        "noticias.preflight",
        "noticias.edit_state",
        "noticias.edit_content",
        "publicaciones.edit",
        "publicaciones.edit_state",
        "publicaciones.publish",
        "users.manage",
        "sessions.view",
        "sessions.revoke",
    },
    RolPanel.editor: {
        "dashboard.view",
        "noticias.view",
        "noticias.generate",
        "noticias.approve",
        "noticias.schedule",
        "noticias.publish",
        "noticias.preflight",
        "noticias.edit_state",
        "noticias.edit_content",
        "publicaciones.edit",
        "publicaciones.edit_state",
        "publicaciones.publish",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Determina si un rol tiene un permiso."""

    try:
        rol = RolPanel(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(rol, set())


def list_permissions(role: str) -> list[str]:
    """Lista permisos del rol indicado."""

    try:
        rol = RolPanel(role)
    except ValueError:
        return []
    return sorted(ROLE_PERMISSIONS.get(rol, set()))
