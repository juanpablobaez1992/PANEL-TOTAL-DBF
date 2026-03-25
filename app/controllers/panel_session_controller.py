"""Controlador de sesiones revocables del panel."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.controllers.panel_user_controller import get_user_by_id
from app.models.panel_session import PanelSession


def _as_utc(value: datetime) -> datetime:
    """Normaliza datetimes naive a UTC aware."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_refresh_token(token: str) -> str:
    """Hashea un refresh token para persistirlo de forma segura."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, *, user_id: int, user_agent: str | None) -> tuple[PanelSession, str]:
    """Crea una sesión revocable y devuelve el token refresh en claro."""

    refresh_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.panel_token_ttl_minutes * 4)
    session = PanelSession(
        user_id=user_id,
        refresh_token_hash=_hash_refresh_token(refresh_token),
        user_agent=user_agent,
        expires_at=expires_at,
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, refresh_token


def get_session_by_refresh_token(db: Session, refresh_token: str) -> PanelSession | None:
    """Busca una sesión por refresh token."""

    return db.scalar(
        select(PanelSession).where(PanelSession.refresh_token_hash == _hash_refresh_token(refresh_token))
    )


def touch_session(db: Session, session: PanelSession) -> PanelSession:
    """Actualiza last_used_at de una sesión."""

    session.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, session: PanelSession) -> PanelSession:
    """Revoca una sesión."""

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


def revoke_by_refresh_token(db: Session, refresh_token: str) -> PanelSession:
    """Revoca una sesión a partir de su refresh token."""

    session = get_session_by_refresh_token(db, refresh_token)
    if session is None:
        raise ValueError("Sesión no encontrada.")
    return revoke_session(db, session)


def get_active_session(db: Session, session_id: int) -> PanelSession | None:
    """Devuelve una sesión activa y no vencida."""

    session = db.get(PanelSession, session_id)
    if session is None or session.revoked_at is not None:
        return None
    if _as_utc(session.expires_at) <= datetime.now(timezone.utc):
        return None
    user = get_user_by_id(db, session.user_id)
    if user is None or not user.activo:
        return None
    return session


def list_sessions_paginated(
    db: Session,
    page: int,
    page_size: int,
    *,
    q: str | None = None,
    solo_activas: bool = False,
) -> tuple[list[PanelSession], int]:
    """Lista sesiones del panel."""

    stmt = select(PanelSession)
    count_stmt = select(func.count()).select_from(PanelSession)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(PanelSession.user_agent.ilike(pattern))
        count_stmt = count_stmt.where(PanelSession.user_agent.ilike(pattern))
    if solo_activas:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(PanelSession.revoked_at.is_(None), PanelSession.expires_at > now)
        count_stmt = count_stmt.where(PanelSession.revoked_at.is_(None), PanelSession.expires_at > now)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(PanelSession.created_at.desc(), PanelSession.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total
