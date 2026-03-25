"""Generacion de copies para automation usando Gemini/Claude."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.utils.json_tools import normalize_json_text

logger = logging.getLogger(__name__)

BASE_PROMPT = """
Actua como un copywriter senior especializado en redes sociales y periodismo digital.
A partir de un titulo y un resumen de una noticia, redacta dos textos persuasivos.

Reglas para Facebook:
1. Primera linea con gancho claro.
2. Desarrollo conciso pero intrigante.
3. Mantene lectura fluida y natural.
4. Usa emojis con moderacion.
5. Cerrá con CTA para entrar o debatir.

Reglas para Instagram:
1. Primera linea magnetica.
2. Tono un poco mas conversacional.
3. Parrafos cortos y aireados.
4. CTA para guardar o ir al link en bio.
5. Solo 3 a 5 hashtags especificos.

Responde unicamente JSON con esta forma:
{
  "facebook_copy": "...",
  "instagram_copy": "..."
}
""".strip()


def _build_prompt(*, title: str, excerpt: str, custom_instructions: str, is_evergreen: bool) -> str:
    """Arma el prompt final."""

    evergreen_block = ""
    if is_evergreen:
        evergreen_block = """

INSTRUCCION EVERGREEN:
Esta es una noticia antigua que vuelve a publicarse.
Redactala con tono de recuerdo, contexto o vigencia actual.
No la trates como breaking news.
""".strip()

    custom_block = ""
    if custom_instructions:
        custom_block = f"""

INSTRUCCIONES ESPECIALES POR CATEGORIA:
{custom_instructions}
""".strip()

    return (
        f"{BASE_PROMPT}\n\n"
        f"Titulo: {title}\n"
        f"Resumen: {excerpt}\n"
        f"{evergreen_block}\n"
        f"{custom_block}\n"
    ).strip()


async def _call_gemini(prompt: str) -> dict[str, str]:
    """Invoca Gemini directamente por HTTP."""

    if not settings.resolved_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY no configurada.")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, params={"key": settings.resolved_gemini_api_key}, json=payload)
        response.raise_for_status()
        data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = normalize_json_text(text)
    return {
        "facebook_copy": str(parsed.get("facebook_copy", "")).strip(),
        "instagram_copy": str(parsed.get("instagram_copy", "")).strip(),
    }


async def _call_claude(prompt: str) -> dict[str, str]:
    """Invoca Claude como fallback."""

    if not settings.claude_api_key:
        raise RuntimeError("CLAUDE_API_KEY no configurada.")

    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1400,
        "system": "Sos un copywriter senior de redes sociales. Responde solo JSON valido.",
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": settings.claude_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    text = "\n".join(item["text"] for item in data.get("content", []) if item.get("type") == "text")
    parsed = normalize_json_text(text)
    return {
        "facebook_copy": str(parsed.get("facebook_copy", "")).strip(),
        "instagram_copy": str(parsed.get("instagram_copy", "")).strip(),
    }


async def generate_copies(
    *,
    title: str,
    excerpt: str,
    custom_instructions: str = "",
    is_evergreen: bool = False,
) -> dict[str, str]:
    """Genera copies usando Gemini y fallback opcional a Claude."""

    prompt = _build_prompt(
        title=title,
        excerpt=excerpt,
        custom_instructions=custom_instructions,
        is_evergreen=is_evergreen,
    )
    try:
        return await _call_gemini(prompt)
    except Exception as error:  # noqa: BLE001
        logger.warning("Gemini fallo, usando Claude como fallback. Error: %s", error)
        return await _call_claude(prompt)
