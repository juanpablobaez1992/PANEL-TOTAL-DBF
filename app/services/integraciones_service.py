"""Servicios de diagnóstico para integraciones externas."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.facebook_service import _graph_url
from app.services.twitter_service import _oauth_header

logger = logging.getLogger(__name__)


async def check_instagram() -> dict[str, str | bool | None]:
    """Verifica acceso básico a la cuenta de Instagram configurada."""

    if not settings.meta_access_token or not settings.meta_ig_account_id:
        return {
            "nombre": "instagram",
            "ok": False,
            "detalle": "Faltan META_ACCESS_TOKEN y/o META_IG_ACCOUNT_ID en .env",
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                _graph_url(str(settings.meta_ig_account_id)),
                params={
                    "fields": "id,username",
                    "access_token": settings.meta_access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "nombre": "instagram",
                "ok": True,
                "detalle": f"Cuenta accesible: {data.get('username', data.get('id', 'sin username'))}",
            }
    except Exception as error:  # noqa: BLE001
        logger.warning("Check de Instagram falló: %s", error)
        return {"nombre": "instagram", "ok": False, "detalle": str(error)}


async def check_twitter() -> dict[str, str | bool | None]:
    """Verifica acceso básico a la cuenta de X configurada."""

    required = [
        settings.twitter_api_key,
        settings.twitter_api_secret,
        settings.twitter_access_token,
        settings.twitter_access_secret,
    ]
    if not all(required):
        return {
            "nombre": "twitter",
            "ok": False,
            "detalle": (
                "Faltan TWITTER_API_KEY, TWITTER_API_SECRET, "
                "TWITTER_ACCESS_TOKEN y/o TWITTER_ACCESS_SECRET en .env"
            ),
        }

    try:
        url = "https://api.x.com/2/users/me"
        headers = _oauth_header(method="GET", url=url)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json().get("data", {})
            username = data.get("username") or data.get("id") or "sin username"
            return {"nombre": "twitter", "ok": True, "detalle": f"Cuenta accesible: {username}"}
    except Exception as error:  # noqa: BLE001
        logger.warning("Check de Twitter/X falló: %s", error)
        return {"nombre": "twitter", "ok": False, "detalle": str(error)}


async def check_integraciones() -> list[dict[str, str | bool | None]]:
    """Ejecuta todos los chequeos de integración disponibles."""

    instagram = await check_instagram()
    twitter = await check_twitter()
    return [instagram, twitter]


def get_missing_startup_configs() -> list[str]:
    """Resume variables clave faltantes para el arranque."""

    faltantes: list[str] = []
    if not settings.secret_key or settings.secret_key == "cambiar-esto":
        faltantes.append("SECRET_KEY")
    if not settings.public_base_url or "localhost" in settings.public_base_url:
        faltantes.append("PUBLIC_BASE_URL publico para Instagram")
    if not settings.meta_access_token:
        faltantes.append("META_ACCESS_TOKEN")
    if not settings.meta_ig_account_id:
        faltantes.append("META_IG_ACCOUNT_ID")
    if not all(
        [
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret,
        ]
    ):
        faltantes.append("Credenciales completas de Twitter/X")
    return faltantes
