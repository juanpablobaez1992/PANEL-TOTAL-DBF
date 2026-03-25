"""Routers HTTP para canales."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers import canal_controller
from app.database import get_db
from app.models.schemas import CanalCreate, CanalRead, CanalUpdate

router = APIRouter(prefix="/api/canales", tags=["Canales"])


@router.get("/", response_model=list[CanalRead])
async def listar_canales(db: Session = Depends(get_db)) -> list[CanalRead]:
    """Lista canales configurados."""

    return list(canal_controller.list_canales(db))


@router.post("/", response_model=CanalRead, status_code=status.HTTP_201_CREATED)
async def crear_canal(payload: CanalCreate, db: Session = Depends(get_db)) -> CanalRead:
    """Crea un canal nuevo."""

    try:
        return canal_controller.create_canal(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.put("/{canal_id}", response_model=CanalRead)
async def actualizar_canal(canal_id: int, payload: CanalUpdate, db: Session = Depends(get_db)) -> CanalRead:
    """Actualiza un canal existente."""

    try:
        return canal_controller.update_canal(db, canal_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{canal_id}/toggle-activo", response_model=CanalRead)
async def toggle_activo(canal_id: int, db: Session = Depends(get_db)) -> CanalRead:
    """Activa o desactiva un canal."""

    try:
        return canal_controller.toggle_canal_activo(db, canal_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{canal_id}/toggle-auto", response_model=CanalRead)
async def toggle_auto(canal_id: int, db: Session = Depends(get_db)) -> CanalRead:
    """Activa o desactiva auto publicación."""

    try:
        return canal_controller.toggle_canal_auto(db, canal_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/seed", response_model=list[CanalRead])
async def seed_canales(db: Session = Depends(get_db)) -> list[CanalRead]:
    """Crea canales por defecto si aún no existen."""

    return list(canal_controller.seed_default_canales(db))
