"""Servicio de publicación en Telegram Bot API."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import settings
from app.utils.http_result import build_result

logger = logging.getLogger(__name__)


async def publicar_en_telegram(
    *,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Publica un mensaje o foto en Telegram."""

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return build_result(exito=False, error="Telegram requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")

    base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            if imagen_path:
                files = {"photo": (Path(imagen_path).name, Path(imagen_path).read_bytes(), "image/jpeg")}
                data = {"chat_id": settings.telegram_chat_id, "caption": contenido}
                response = await client.post(f"{base_url}/sendPhoto", data=data, files=files)
            else:
                response = await client.post(
                    f"{base_url}/sendMessage",
                    json={"chat_id": settings.telegram_chat_id, "text": contenido},
                )
            response.raise_for_status()
            payload = response.json()
            message = payload.get("result", {})
            message_id = message.get("message_id")
            return build_result(exito=True, external_id=str(message_id) if message_id else None)
    except Exception as error:  # noqa: BLE001
        logger.exception("Error publicando en Telegram")
        return build_result(exito=False, error=str(error))
