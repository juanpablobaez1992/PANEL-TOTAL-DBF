"""Routers HTTP para diagnóstico del sistema."""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers import system_controller
from app.models.schemas import IntegracionStatus

router = APIRouter(prefix="/api/sistema", tags=["Sistema"])


@router.get("/integraciones", response_model=list[IntegracionStatus])
async def estado_integraciones() -> list[IntegracionStatus]:
    """Devuelve el estado de las integraciones externas configuradas."""

    return await system_controller.obtener_estado_integraciones()
