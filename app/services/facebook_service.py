"""Servicio para Facebook e Instagram vía Meta Graph API."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import settings
from app.utils.assets import local_path_to_public_url
from app.utils.http_result import build_result

logger = logging.getLogger(__name__)


def _graph_url(path: str) -> str:
    """Construye una URL a Graph API con la versión configurada."""

    version = settings.meta_graph_version.lstrip("/")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


async def publicar_en_facebook(
    *,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Publica contenido en una página de Facebook."""

    if not settings.resolved_meta_page_id or not settings.resolved_meta_access_token:
        return build_result(exito=False, error="Facebook requiere META_PAGE_ID y META_ACCESS_TOKEN.")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            if imagen_path:
                files = {"source": (Path(imagen_path).name, Path(imagen_path).read_bytes(), "image/jpeg")}
                data = {"caption": contenido, "access_token": settings.resolved_meta_access_token}
                response = await client.post(
                    _graph_url(f"{settings.resolved_meta_page_id}/photos"),
                    data=data,
                    files=files,
                )
            else:
                response = await client.post(
                    _graph_url(f"{settings.resolved_meta_page_id}/feed"),
                    data={"message": contenido, "access_token": settings.resolved_meta_access_token},
                )
            response.raise_for_status()
            payload = response.json()
            post_id = payload.get("post_id") or payload.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            return build_result(exito=True, external_id=post_id, url=post_url)
    except Exception as error:  # noqa: BLE001
        logger.exception("Error publicando en Facebook")
        return build_result(exito=False, error=str(error))


async def publicar_en_instagram(
    *,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Publica una imagen en Instagram mediante media container + media_publish."""

    if not settings.resolved_meta_ig_account_id or not settings.resolved_meta_access_token:
        return build_result(
            exito=False,
            error="Instagram requiere META_IG_ACCOUNT_ID y META_ACCESS_TOKEN.",
        )
    if not imagen_path:
        return build_result(
            exito=False,
            error="Instagram requiere una imagen procesada accesible públicamente.",
        )

    try:
        image_url = local_path_to_public_url(imagen_path)
    except ValueError as error:
        return build_result(exito=False, error=str(error))

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            create_response = await client.post(
                _graph_url(f"{settings.resolved_meta_ig_account_id}/media"),
                data={
                    "image_url": image_url,
                    "caption": contenido,
                    "access_token": settings.resolved_meta_access_token,
                },
            )
            create_response.raise_for_status()
            creation_id = create_response.json().get("id")
            if not creation_id:
                return build_result(exito=False, error="Instagram no devolvió creation_id.")

            publish_response = await client.post(
                _graph_url(f"{settings.resolved_meta_ig_account_id}/media_publish"),
                data={
                    "creation_id": creation_id,
                    "access_token": settings.resolved_meta_access_token,
                },
            )
            publish_response.raise_for_status()
            media_id = publish_response.json().get("id")
            if not media_id:
                return build_result(exito=False, error="Instagram no devolvió media_id publicado.")

            permalink_response = await client.get(
                _graph_url(str(media_id)),
                params={
                    "fields": "id,permalink",
                    "access_token": settings.resolved_meta_access_token,
                },
            )
            permalink_response.raise_for_status()
            permalink = permalink_response.json().get("permalink")
            return build_result(exito=True, external_id=str(media_id), url=permalink)
    except Exception as error:  # noqa: BLE001
        logger.exception("Error publicando en Instagram")
        return build_result(exito=False, error=str(error))
