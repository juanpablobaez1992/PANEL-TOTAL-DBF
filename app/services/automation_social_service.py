"""Publicacion remota a Facebook/Instagram para AUTOPUBLICATE."""

from __future__ import annotations

import httpx

from app.config import settings
from app.services.facebook_service import _graph_url
from app.utils.http_result import build_result


async def post_to_facebook(
    *,
    message: str,
    link: str,
    image_url: str | None = None,
    page_id: str | None = None,
    access_token: str | None = None,
) -> dict[str, str | bool | None]:
    """Publica en una pagina de Facebook usando imagen remota o link."""

    current_page_id = page_id or settings.resolved_meta_page_id
    current_token = access_token or settings.resolved_meta_access_token
    if not current_page_id or not current_token:
        return build_result(exito=False, error="Facebook requiere PAGE_ID y ACCESS_TOKEN.")

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            if image_url:
                response = await client.post(
                    _graph_url(f"{current_page_id}/photos"),
                    data={
                        "url": image_url,
                        "message": f"{message}\n\n{link}".strip(),
                        "access_token": current_token,
                    },
                )
            else:
                response = await client.post(
                    _graph_url(f"{current_page_id}/feed"),
                    data={
                        "message": message,
                        "link": link,
                        "access_token": current_token,
                    },
                )
            response.raise_for_status()
            payload = response.json()
            post_id = payload.get("post_id") or payload.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            return build_result(exito=True, external_id=str(post_id) if post_id else None, url=post_url)
    except Exception as error:  # noqa: BLE001
        return build_result(exito=False, error=str(error))


async def post_to_instagram(
    *,
    image_urls: list[str],
    caption: str,
    account_id: str | None = None,
    access_token: str | None = None,
) -> dict[str, str | bool | None]:
    """Publica una imagen o carrusel en Instagram con URLs remotas."""

    current_account_id = account_id or settings.resolved_meta_ig_account_id
    current_token = access_token or settings.resolved_meta_access_token
    if not current_account_id or not current_token:
        return build_result(exito=False, error="Instagram requiere ACCOUNT_ID y ACCESS_TOKEN.")
    if not image_urls:
        return build_result(exito=False, error="Instagram requiere al menos una imagen.")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            if len(image_urls) == 1:
                create_response = await client.post(
                    _graph_url(f"{current_account_id}/media"),
                    data={
                        "image_url": image_urls[0],
                        "caption": caption,
                        "access_token": current_token,
                    },
                )
                create_response.raise_for_status()
                creation_id = create_response.json().get("id")
            else:
                children: list[str] = []
                for image_url in image_urls[:10]:
                    child_response = await client.post(
                        _graph_url(f"{current_account_id}/media"),
                        data={
                            "image_url": image_url,
                            "is_carousel_item": "true",
                            "access_token": current_token,
                        },
                    )
                    child_response.raise_for_status()
                    child_id = child_response.json().get("id")
                    if child_id:
                        children.append(str(child_id))
                container_response = await client.post(
                    _graph_url(f"{current_account_id}/media"),
                    data={
                        "media_type": "CAROUSEL",
                        "children": ",".join(children),
                        "caption": caption,
                        "access_token": current_token,
                    },
                )
                container_response.raise_for_status()
                creation_id = container_response.json().get("id")

            if not creation_id:
                return build_result(exito=False, error="Instagram no devolvio creation_id.")

            publish_response = await client.post(
                _graph_url(f"{current_account_id}/media_publish"),
                data={"creation_id": creation_id, "access_token": current_token},
            )
            publish_response.raise_for_status()
            media_id = publish_response.json().get("id")
            permalink = None
            if media_id:
                permalink_response = await client.get(
                    _graph_url(str(media_id)),
                    params={"fields": "id,permalink", "access_token": current_token},
                )
                permalink_response.raise_for_status()
                permalink = permalink_response.json().get("permalink")
            return build_result(exito=True, external_id=str(media_id) if media_id else None, url=permalink)
    except Exception as error:  # noqa: BLE001
        return build_result(exito=False, error=str(error))
