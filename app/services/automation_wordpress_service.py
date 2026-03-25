"""Lectura de cola y categorias desde WordPress para automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import re

import httpx

from app.config import settings


@dataclass
class AutomationSourcePost:
    """Post fuente obtenido desde WordPress."""

    id: int
    title: str
    excerpt: str
    link: str
    image_url: str | None = None
    image_urls: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


def _clean_html(raw: str) -> str:
    """Remueve tags HTML basicos."""

    return re.sub(r"<[^>]+>", "", raw or "").strip()


def _parse_post(post_data: dict) -> AutomationSourcePost:
    """Convierte un payload de WP en un objeto usable."""

    image_url = None
    if "_embedded" in post_data and "wp:featuredmedia" in post_data["_embedded"]:
        media = post_data["_embedded"]["wp:featuredmedia"]
        if media:
            image_url = media[0].get("source_url")

    content = post_data.get("content", {}).get("rendered", "")
    extracted_images = re.findall(r'<img[^>]+src="([^">]+)"', content)
    image_urls: list[str] = []
    if image_url:
        image_urls.append(image_url)
    for current in extracted_images:
        if current not in image_urls:
            image_urls.append(current)

    categories: list[str] = []
    if "_embedded" in post_data and "wp:term" in post_data["_embedded"]:
        for tax_array in post_data["_embedded"]["wp:term"]:
            for term in tax_array:
                if term.get("taxonomy") == "category" and term.get("slug"):
                    categories.append(term["slug"])

    return AutomationSourcePost(
        id=int(post_data.get("id", 0)),
        title=_clean_html(post_data.get("title", {}).get("rendered", "")),
        excerpt=_clean_html(post_data.get("excerpt", {}).get("rendered", "")),
        link=post_data.get("link", ""),
        image_url=image_url,
        image_urls=image_urls[:10],
        categories=categories,
    )


async def _fetch_json(path: str, *, params: dict[str, str | int] | None = None) -> list[dict]:
    """Ejecuta un GET contra WP REST API."""

    if not settings.resolved_wp_url:
        raise RuntimeError("WP_URL no configurado.")

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(f"{settings.resolved_wp_url.rstrip('/')}{path}", params=params)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else [data]


async def get_unprocessed_posts(last_id: int, limit: int = 50) -> list[AutomationSourcePost]:
    """Devuelve la cola pendiente mayor al ultimo ID procesado."""

    posts = await _fetch_json("/wp-json/wp/v2/posts", params={"per_page": limit, "_embed": 1})
    pending = [post for post in posts if int(post.get("id", 0)) > last_id]
    pending.sort(key=lambda item: int(item.get("id", 0)))
    return [_parse_post(post) for post in pending]


async def get_next_unprocessed_post(last_id: int) -> AutomationSourcePost | None:
    """Devuelve el siguiente post pendiente."""

    posts = await get_unprocessed_posts(last_id, limit=20)
    return posts[0] if posts else None


async def get_random_old_post(*, months: int = 6, allowed_categories: list[int] | None = None) -> AutomationSourcePost | None:
    """Devuelve un post viejo aleatorio para evergreen."""

    before_date = (datetime.now() - timedelta(days=months * 30)).isoformat()
    params: dict[str, str | int] = {"before": before_date, "per_page": 50, "_embed": 1}
    if allowed_categories:
        params["categories"] = ",".join(str(item) for item in allowed_categories)
    posts = await _fetch_json("/wp-json/wp/v2/posts", params=params)
    if not posts:
        return None
    return _parse_post(random.choice(posts))


async def get_all_categories() -> list[dict]:
    """Lista categorias disponibles de WordPress."""

    return await _fetch_json("/wp-json/wp/v2/categories", params={"per_page": 100})
