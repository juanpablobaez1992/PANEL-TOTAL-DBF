"""Controlador de usuarios del panel."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.panel_user import PanelUser
from app.models.schemas import PanelUserCreate, PanelUserUpdate
from app.utils.passwords import hash_password


def get_user_by_id(db: Session, user_id: int) -> PanelUser | None:
    """Busca un usuario del panel por ID."""

    return db.get(PanelUser, user_id)


def get_user_by_username(db: Session, username: str) -> PanelUser | None:
    """Busca un usuario del panel por username."""

    return db.scalar(select(PanelUser).where(PanelUser.username == username))


def get_user_by_id(db: Session, user_id: int) -> PanelUser | None:
    """Busca un usuario por ID."""

    return db.get(PanelUser, user_id)


def list_users_paginated(
    db: Session,
    page: int,
    page_size: int,
    *,
    q: str | None = None,
    activo: bool | None = None,
) -> tuple[list[PanelUser], int]:
    """Lista usuarios del panel de forma paginada."""

    stmt = select(PanelUser)
    count_stmt = select(func.count()).select_from(PanelUser)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(PanelUser.username.ilike(pattern))
        count_stmt = count_stmt.where(PanelUser.username.ilike(pattern))
    if activo is not None:
        stmt = stmt.where(PanelUser.activo.is_(activo))
        count_stmt = count_stmt.where(PanelUser.activo.is_(activo))

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(PanelUser.created_at.desc(), PanelUser.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def create_user(db: Session, payload: PanelUserCreate) -> PanelUser:
    """Crea un usuario del panel."""

    if get_user_by_username(db, payload.username) is not None:
        raise ValueError("Ya existe un usuario con ese nombre.")
    user = PanelUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        activo=payload.activo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: PanelUserUpdate) -> PanelUser:
    """Actualiza un usuario del panel."""

    user = db.get(PanelUser, user_id)
    if user is None:
        raise ValueError("Usuario no encontrado.")
    if payload.username and payload.username != user.username:
        existing = get_user_by_username(db, payload.username)
        if existing is not None:
            raise ValueError("Ya existe un usuario con ese nombre.")
        user.username = payload.username
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.activo is not None:
        user.activo = payload.activo
    db.commit()
    db.refresh(user)
    return user


def seed_admin_user(db: Session, username: str, password_hash: str, role) -> PanelUser:
    """Crea o ajusta el admin inicial del panel."""

    user = get_user_by_username(db, username)
    if user is None:
        user = PanelUser(username=username, password_hash=password_hash, role=role, activo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    changed = False
    if user.role != role:
        user.role = role
        changed = True
    if not user.activo:
        user.activo = True
        changed = True
    if changed:
        db.commit()
        db.refresh(user)
    return user
