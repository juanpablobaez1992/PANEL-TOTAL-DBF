"""Autenticación simple con token firmado para el panel."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.config import settings


def _sign(raw: bytes) -> str:
    """Firma un payload con HMAC-SHA256."""

    digest = hmac.new(settings.secret_key.encode("utf-8"), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def create_access_token(user_id: int, username: str, role: str, session_id: int) -> tuple[str, datetime]:
    """Crea un token firmado con expiración."""

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.panel_token_ttl_minutes)
    payload = {
        "sub": username,
        "uid": user_id,
        "role": role,
        "sid": session_id,
        "exp": int(expires_at.timestamp()),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    token = f"{base64.urlsafe_b64encode(raw).decode('utf-8')}.{_sign(raw)}"
    return token, expires_at


def verify_access_token(token: str) -> dict[str, object]:
    """Valida un token del panel y devuelve su payload."""

    try:
        encoded_payload, signature = token.split(".", 1)
        raw = base64.urlsafe_b64decode(encoded_payload.encode("utf-8"))
        expected_signature = _sign(raw)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Firma inválida.")
        payload = json.loads(raw.decode("utf-8"))
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expirado.")
        return payload
    except Exception as error:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {error}",
        ) from error
