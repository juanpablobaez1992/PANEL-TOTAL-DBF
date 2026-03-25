"""Dependencias compartidas para vistas."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.controllers.panel_session_controller import get_active_session, touch_session
from app.database import get_db
from app.utils.auth import verify_access_token
from app.utils.permissions import has_permission

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_panel_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Valida el bearer token del panel y devuelve su payload."""

    payload = verify_access_token(credentials.credentials)
    session_id = int(payload.get("sid", 0))
    session = get_active_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o revocada.")
    touch_session(db, session)
    return payload


def require_permission(permission: str):
    """Devuelve una dependencia que exige un permiso concreto."""

    def dependency(user: dict[str, object] = Depends(get_current_panel_user)) -> dict[str, object]:
        role = str(user.get("role", ""))
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente: {permission}",
            )
        return user

    return dependency
