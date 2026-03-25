"""Routers HTTP para publicaciones."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers import publicacion_controller
from app.database import get_db
from app.models.schemas import PublicacionRead, PublicacionUpdate

router = APIRouter(prefix="/api/publicaciones", tags=["Publicaciones"])


@router.post("/noticia/{noticia_id}/publicar", response_model=list[PublicacionRead])
async def publicar_noticia(noticia_id: int, db: Session = Depends(get_db)) -> list[PublicacionRead]:
    """Publica todas las publicaciones de una noticia."""

    try:
        return await publicacion_controller.publicar_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{publicacion_id}/publicar", response_model=PublicacionRead)
async def publicar_individual(publicacion_id: int, db: Session = Depends(get_db)) -> PublicacionRead:
    """Publica una publicación individual."""

    try:
        return await publicacion_controller.publicar_individual(db, publicacion_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.patch("/{publicacion_id}", response_model=PublicacionRead)
async def editar_publicacion(
    publicacion_id: int,
    payload: PublicacionUpdate,
    db: Session = Depends(get_db),
) -> PublicacionRead:
    """Edita el contenido de una publicación."""

    try:
        return publicacion_controller.update_publicacion(db, publicacion_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{publicacion_id}/omitir", response_model=PublicacionRead)
async def omitir_publicacion(publicacion_id: int, db: Session = Depends(get_db)) -> PublicacionRead:
    """Marca una publicación como omitida."""

    try:
        return publicacion_controller.omitir_publicacion(db, publicacion_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
