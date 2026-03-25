"""Utilidades para cifrado y manejo de credenciales de canales."""

from __future__ import annotations

import base64
import json
import logging
from hashlib import sha256
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

ENCRYPTED_PREFIX = "enc::"


def _build_fernet() -> Fernet:
    """Construye una instancia Fernet derivada de SECRET_KEY."""

    key = base64.urlsafe_b64encode(sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_config(config: dict[str, Any]) -> str:
    """Cifra un diccionario y devuelve un string seguro para persistir."""

    raw = json.dumps(config, ensure_ascii=False, sort_keys=True).encode("utf-8")
    token = _build_fernet().encrypt(raw).decode("utf-8")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_config(raw_value: str | None) -> dict[str, Any]:
    """Descifra config_json; si viene en texto plano, lo interpreta como JSON legacy."""

    if not raw_value:
        return {}

    if raw_value.startswith(ENCRYPTED_PREFIX):
        token = raw_value[len(ENCRYPTED_PREFIX) :].encode("utf-8")
        try:
            decrypted = _build_fernet().decrypt(token).decode("utf-8")
            return json.loads(decrypted)
        except (InvalidToken, json.JSONDecodeError) as error:
            logger.warning("No se pudo descifrar config_json: %s", error)
            return {}

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning("config_json legacy inválido; se devolverá objeto vacío.")
        return {}


def coerce_config_payload(
    config: dict[str, Any] | None = None,
    config_json: str | None = None,
) -> dict[str, Any]:
    """Unifica payloads dict y JSON string hacia un dict consistente."""

    if config is not None:
        return config
    if not config_json:
        return {}
    try:
        loaded = json.loads(config_json)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError as error:
        raise ValueError("config_json debe ser un JSON válido.") from error
