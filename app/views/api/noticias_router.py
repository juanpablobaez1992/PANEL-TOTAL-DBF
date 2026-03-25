"""Routers HTTP para noticias."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.controllers import noticia_controller
from app.database import get_db
from app.models.enums import CategoriaNoticia, UrgenciaNoticia
from app.models.schemas import (
    DespachoFormData,
    NoticiaCreate,
    NoticiaRead,
    NoticiaUpdate,
    PreflightNoticiaStatus,
    ProgramacionPayload,
)

router = APIRouter(prefix="/api/noticias", tags=["Noticias"])


@router.get("/", response_model=list[NoticiaRead])
async def listar_noticias(
    estado: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[NoticiaRead]:
    """Lista noticias con filtro opcional por estado."""

    try:
        return list(noticia_controller.list_noticias(db, estado=estado))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{noticia_id}", response_model=NoticiaRead)
async def obtener_noticia(noticia_id: int, db: Session = Depends(get_db)) -> NoticiaRead:
    """Devuelve una noticia por ID."""

    noticia = noticia_controller.get_noticia(db, noticia_id)
    if noticia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Noticia no encontrada.")
    return noticia


@router.post("/", response_model=NoticiaRead, status_code=status.HTTP_201_CREATED)
async def crear_noticia(payload: NoticiaCreate, db: Session = Depends(get_db)) -> NoticiaRead:
    """Crea una noticia borrador."""

    return noticia_controller.create_noticia(db, payload)


@router.patch("/{noticia_id}", response_model=NoticiaRead)
async def editar_noticia(
    noticia_id: int,
    payload: NoticiaUpdate,
    db: Session = Depends(get_db),
) -> NoticiaRead:
    """Edita una noticia."""

    try:
        return noticia_controller.update_noticia(db, noticia_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{noticia_id}/imagen", response_model=NoticiaRead)
async def subir_imagen(
    noticia_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> NoticiaRead:
    """Sube la imagen original de una noticia."""

    try:
        return await noticia_controller.upload_noticia_image(db, noticia_id, archivo)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{noticia_id}/generar", response_model=NoticiaRead)
async def generar_noticia(noticia_id: int, db: Session = Depends(get_db)) -> NoticiaRead:
    """Genera contenido IA y previews por canal."""

    try:
        return await noticia_controller.generar_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{noticia_id}/aprobar", response_model=NoticiaRead)
async def aprobar_noticia(noticia_id: int, db: Session = Depends(get_db)) -> NoticiaRead:
    """Aprueba una noticia para publicación manual."""

    try:
        return noticia_controller.aprobar_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{noticia_id}/preflight", response_model=PreflightNoticiaStatus)
async def preflight_noticia(noticia_id: int, db: Session = Depends(get_db)) -> PreflightNoticiaStatus:
    """Valida si una noticia está lista para publicarse por canal."""

    try:
        return noticia_controller.obtener_preflight_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{noticia_id}/programar", response_model=NoticiaRead)
async def programar_noticia(
    noticia_id: int,
    payload: ProgramacionPayload,
    db: Session = Depends(get_db),
) -> NoticiaRead:
    """Programa una noticia aprobada para publicación futura."""

    try:
        return noticia_controller.programar_noticia(db, noticia_id, payload.programada_para)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{noticia_id}/cancelar-programacion", response_model=NoticiaRead)
async def cancelar_programacion(noticia_id: int, db: Session = Depends(get_db)) -> NoticiaRead:
    """Cancela la programación de una noticia."""

    try:
        return noticia_controller.cancelar_programacion_noticia(db, noticia_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/despacho", response_model=NoticiaRead, status_code=status.HTTP_201_CREATED)
async def despacho_rapido(
    hecho: str = Form(...),
    lugar: str | None = Form(default=None),
    categoria: CategoriaNoticia = Form(default=CategoriaNoticia.general),
    urgencia: UrgenciaNoticia = Form(default=UrgenciaNoticia.normal),
    fecha_hecho: datetime | None = Form(default=None),
    foto: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> NoticiaRead:
    """Ejecuta el flujo expreso de creación y generación."""

    try:
        payload = DespachoFormData(
            hecho=hecho,
            lugar=lugar,
            categoria=categoria,
            urgencia=urgencia,
        )
        noticia = await noticia_controller.despacho_rapido(db, payload=payload, upload=foto)
        if fecha_hecho is not None:
            noticia_controller.update_noticia(db, noticia.id, NoticiaUpdate(fecha_hecho=fecha_hecho))
            noticia = noticia_controller.get_noticia(db, noticia.id) or noticia
        return noticia
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
