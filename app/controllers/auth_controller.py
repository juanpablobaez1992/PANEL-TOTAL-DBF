"""Controlador de autenticación simple para el panel."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.controllers.panel_session_controller import (
    _as_utc,
    create_session,
    get_session_by_refresh_token,
    revoke_session,
    touch_session,
)
from app.controllers.panel_user_controller import get_user_by_username
from app.models.schemas import AuthTokenResponse, PanelUserRead
from app.utils.auth import create_access_token
from app.utils.passwords import verify_password


def login_panel(db: Session, username: str, password: str, user_agent: str | None) -> AuthTokenResponse:
    """Valida credenciales del panel y emite un token firmado."""

    user = get_user_by_username(db, username)
    if user is None or not user.activo or not verify_password(password, user.password_hash):
        raise ValueError("Credenciales inválidas.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    session, refresh_token = create_session(db, user_id=user.id, user_agent=user_agent)
    token, expires_at = create_access_token(user.id, user.username, user.role.value, session.id)
    return AuthTokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user=PanelUserRead.model_validate(user),
    )


def refresh_panel_session(db: Session, refresh_token: str) -> AuthTokenResponse:
    """Renueva access y refresh token para una sesión activa."""

    session = get_session_by_refresh_token(db, refresh_token)
    if session is None or session.revoked_at is not None or _as_utc(session.expires_at) <= datetime.now(timezone.utc):
        raise ValueError("Refresh token inválido o expirado.")
    user = session.user
    if user is None or not user.activo:
        raise ValueError("Usuario inactivo o inexistente.")

    revoke_session(db, session)
    new_session, new_refresh_token = create_session(db, user_id=user.id, user_agent=session.user_agent)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    token, expires_at = create_access_token(user.id, user.username, user.role.value, new_session.id)
    return AuthTokenResponse(
        access_token=token,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
        user=PanelUserRead.model_validate(user),
    )


def logout_panel_session(db: Session, refresh_token: str) -> None:
    """Revoca una sesión de panel usando refresh token."""

    session = get_session_by_refresh_token(db, refresh_token)
    if session is None:
        raise ValueError("Sesión no encontrada.")
    revoke_session(db, session)
