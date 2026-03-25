"""Servicio para preparar copy de WhatsApp Channel."""

from __future__ import annotations

from app.utils.http_result import build_result


async def publicar_en_whatsapp(
    *,
    contenido: str,
    imagen_path: str | None,
) -> dict[str, str | bool | None]:
    """Marca la publicación como lista para copiar y pegar manualmente."""

    _ = imagen_path
    return build_result(
        exito=True,
        external_id="manual",
        url=None,
        error=None,
    )
