"""Controlador para endpoints de sistema y diagnóstico."""

from __future__ import annotations

from app.services.integraciones_service import check_integraciones


async def obtener_estado_integraciones() -> list[dict[str, str | bool | None]]:
    """Devuelve el estado actual de integraciones externas."""

    return await check_integraciones()
