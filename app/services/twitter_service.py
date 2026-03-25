"""Servicio real para Twitter/X con OAuth 1.0a."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import settings
from app.utils.http_result import build_result
from app.utils.oauth1 import build_oauth1_header

logger = logging.getLogger(__name__)

TWITTER_API_URL = "https://api.x.com/2/tweets"
TWITTER_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"


def _oauth_header(
    *,
    method: str,
    url: str,
    extra_params: dict[str, str] | None = None,
) -> dict[str, str]:
    """Construye el header Authorization OAuth 1.0a para X."""

    if not all(
        [
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret,
        ]
    ):
        raise RuntimeError(
            "Twitter/X requiere TWITTER_API_KEY, TWITTER_API_SECRET, "
            "TWITTER_ACCESS_TOKEN y TWITTER_ACCESS_SECRET."
        )

    return {
        "Authorization": build_oauth1_header(
            method=method,
            url=url,
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            token=settings.twitter_access_token,
            token_secret=settings.twitter_access_secret,
            extra_params=extra_params,
        )
    }


async def _upload_media(client: httpx.AsyncClient, image_path: str) -> str:
    """Sube una imagen a X y devuelve el media_id."""

    headers = _oauth_header(method="POST", url=TWITTER_UPLOAD_URL)
    files = {
        "media": (Path(image_path).name, Path(image_path).read_bytes(), "image/jpeg"),
    }
    response = await client.post(TWITTER_UPLOAD_URL, headers=headers, files=files)
    response.raise_for_status()
    payload = response.json()
    media_id = payload.get("media_id_string") or str(payload.get("media_id"))
    if not media_id:
        raise RuntimeError("Twitter/X no devolvió media_id al subir la imagen.")
    return media_id


async def publicar_en_twitter(
    *,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Publica un post en X usando OAuth 1.0a y upload opcional de media."""

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            payload: dict[str, object] = {"text": contenido}
            if imagen_path:
                media_id = await _upload_media(client, imagen_path)
                payload["media"] = {"media_ids": [media_id]}

            headers = _oauth_header(method="POST", url=TWITTER_API_URL)
            response = await client.post(TWITTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json().get("data", {})
            tweet_id = data.get("id")
            tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None
            return build_result(exito=True, external_id=tweet_id, url=tweet_url)
    except Exception as error:  # noqa: BLE001
        logger.exception("Error publicando en Twitter/X")
        return build_result(exito=False, error=str(error))
