"""Servicio de publicación hacia WordPress REST API."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.utils.http_result import build_result

logger = logging.getLogger(__name__)


def _auth_header() -> dict[str, str]:
    raw = f"{settings.wp_user}:{settings.wp_app_password}".encode("utf-8")
    return {"Authorization": f"Basic {base64.b64encode(raw).decode('utf-8')}"}


async def publicar_en_wordpress(
    *,
    titulo: str,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Publica una entrada en WordPress."""

    if not settings.resolved_wp_url or not settings.wp_user or not settings.wp_app_password:
        return build_result(exito=False, error="WordPress requiere WP_URL, WP_USER y WP_APP_PASSWORD.")

    headers = _auth_header()
    media_id: int | None = None

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            if imagen_path:
                media_headers = headers | {
                    "Content-Disposition": f'attachment; filename="{Path(imagen_path).name}"',
                    "Content-Type": "image/jpeg",
                }
                media_response = await client.post(
                    f"{settings.resolved_wp_url.rstrip('/')}/wp-json/wp/v2/media",
                    headers=media_headers,
                    content=Path(imagen_path).read_bytes(),
                )
                media_response.raise_for_status()
                media_id = media_response.json().get("id")

            payload = {
                "title": titulo,
                "content": contenido,
                "status": "publish",
            }
            if media_id:
                payload["featured_media"] = media_id

            response = await client.post(
                f"{settings.resolved_wp_url.rstrip('/')}/wp-json/wp/v2/posts",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return build_result(exito=True, external_id=str(data.get("id")), url=data.get("link"))
    except Exception as error:  # noqa: BLE001
        logger.exception("Error publicando en WordPress")
        return build_result(exito=False, error=str(error))
