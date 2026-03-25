"""Servicio de generación de contenido con IA."""

from __future__ import annotations

import json
import logging
from textwrap import shorten
from typing import Any

import httpx

from app.config import settings
from app.models.enums import CategoriaNoticia, UrgenciaNoticia
from app.models.schemas import GeneracionContenido
from app.utils.json_tools import normalize_json_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Sos un redactor experto de un diario digital católico argentino llamado
"De Buena Fe Digital", basado en San Rafael, Mendoza, Argentina.
Recibís un hecho noticioso crudo y generás contenido profesional adaptado
a múltiples plataformas.

Reglas:
- Estilo periodístico argentino, profesional pero accesible
- Pirámide invertida para el cuerpo
- Tono informativo, nunca sensacionalista
- Temas de Iglesia con respeto y conocimiento
- Hashtags de Instagram relevantes y en español
- Tweet contundente aprovechando cada carácter
- Alerta WhatsApp breve que genere urgencia de lectura

Formato de respuesta: JSON puro con:
{
  "titular": "max 70 chars, SEO",
  "bajada": "subtítulo en 1 oración",
  "cuerpo": "3-5 párrafos pirámide invertida",
  "facebook": "2-3 oraciones + invitación a leer",
  "instagram": "caption + 5-7 hashtags",
  "twitter": "max 260 chars",
  "whatsapp": "2 oraciones máximo",
  "telegram": "breve con emoji relevante"
}
""".strip()


def _build_user_prompt(
    *,
    hecho: str,
    lugar: str | None,
    categoria: CategoriaNoticia,
    urgencia: UrgenciaNoticia,
) -> str:
    """Arma el prompt de usuario para la IA."""

    return (
        f"Hecho: {hecho}\n"
        f"Lugar: {lugar or 'No especificado'}\n"
        f"Categoría: {categoria.value}\n"
        f"Urgencia: {urgencia.value}\n"
    )


def _fallback_generation(
    *,
    hecho: str,
    lugar: str | None,
    categoria: CategoriaNoticia,
    urgencia: UrgenciaNoticia,
) -> GeneracionContenido:
    """Genera contenido base cuando no hay proveedor configurado."""

    lugar_texto = lugar or "San Rafael"
    titular = shorten(f"{hecho} en {lugar_texto}", width=68, placeholder="...")
    bajada = f"El hecho fue reportado en {lugar_texto} y se sigue de cerca dentro de la categoría {categoria.value}."
    cuerpo = (
        f"{hecho}. El episodio fue informado en {lugar_texto} y se encuentra en etapa de seguimiento periodístico.\n\n"
        f"Según los primeros datos disponibles, la noticia se encuadra en la categoría {categoria.value} "
        f"y fue clasificada con urgencia {urgencia.value} para su cobertura.\n\n"
        "Desde De Buena Fe Digital se ampliará la información a medida que surjan nuevos datos confirmados."
    )
    return GeneracionContenido(
        titular=titular,
        bajada=bajada,
        cuerpo=cuerpo,
        facebook=f"{titular}. {bajada} Leé la nota completa en De Buena Fe Digital.",
        instagram=f"{titular}\n\n{bajada}\n\n#SanRafael #Mendoza #Noticias #Actualidad #DeBuenaFeDigital",
        twitter=shorten(f"{titular}. {bajada}", width=250, placeholder="..."),
        whatsapp=shorten(f"{titular}. Más información en De Buena Fe Digital.", width=120, placeholder="..."),
        telegram=f"📰 {titular}\n{bajada}",
    )


async def _call_gemini(user_prompt: str) -> dict[str, Any]:
    """Invoca Gemini y devuelve el JSON parseado."""

    if not settings.resolved_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY no configurada.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, params={"key": settings.resolved_gemini_api_key}, json=payload)
        response.raise_for_status()
        data = response.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return normalize_json_text(text)


async def _call_claude(user_prompt: str) -> dict[str, Any]:
    """Invoca Claude Sonnet y devuelve el JSON parseado."""

    if not settings.claude_api_key:
        raise RuntimeError("CLAUDE_API_KEY no configurada.")

    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1600,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
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

    text_chunks = [item["text"] for item in data.get("content", []) if item.get("type") == "text"]
    return normalize_json_text("\n".join(text_chunks))


async def generar_contenido(
    *,
    hecho: str,
    lugar: str | None,
    categoria: CategoriaNoticia,
    urgencia: UrgenciaNoticia,
) -> GeneracionContenido:
    """Genera contenido periodístico usando el proveedor configurado."""

    user_prompt = _build_user_prompt(
        hecho=hecho,
        lugar=lugar,
        categoria=categoria,
        urgencia=urgencia,
    )

    try:
        if settings.ai_provider.lower() == "claude":
            data = await _call_claude(user_prompt)
        else:
            try:
                data = await _call_gemini(user_prompt)
            except Exception as gemini_error:  # noqa: BLE001
                logger.warning("Gemini falló, se intentará Claude: %s", gemini_error)
                data = await _call_claude(user_prompt)
        return GeneracionContenido.model_validate(data)
    except Exception as error:  # noqa: BLE001
        logger.warning("Se usará generación local de respaldo: %s", error)
        return _fallback_generation(
            hecho=hecho,
            lugar=lugar,
            categoria=categoria,
            urgencia=urgencia,
        )
