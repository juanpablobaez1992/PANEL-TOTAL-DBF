"""Helpers para resultados de servicios externos."""

from __future__ import annotations


def build_result(
    *,
    exito: bool,
    external_id: str | None = None,
    url: str | None = None,
    error: str | None = None,
) -> dict[str, str | bool | None]:
    """Construye la respuesta estándar de un servicio externo."""

    return {
        "id": external_id,
        "url": url,
        "exito": exito,
        "error": error,
    }
