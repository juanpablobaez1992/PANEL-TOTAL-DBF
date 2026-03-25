"""Webhook de ingesta de noticias desde sistemas externos."""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.controllers.noticia_controller import create_noticia
from app.database import get_db
from app.models.enums import CategoriaNoticia, UrgenciaNoticia
from app.models.schemas import NoticiaCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class WebhookNoticiaPayload(BaseModel):
    """Payload de ingesta de noticia externa."""

    hecho: str
    lugar: str | None = None
    categoria: CategoriaNoticia = CategoriaNoticia.general
    urgencia: UrgenciaNoticia = UrgenciaNoticia.normal


def _verificar_token(x_webhook_secret: str | None) -> None:
    """Valida el token secreto del webhook."""

    if not settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook no habilitado. Configurá WEBHOOK_SECRET en el entorno.",
        )
    if not x_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Webhook-Secret requerido.",
        )
    # Comparación segura contra timing attacks
    if not hmac.compare_digest(
        hashlib.sha256(x_webhook_secret.encode()).digest(),
        hashlib.sha256(settings.webhook_secret.encode()).digest(),
    ):
        logger.warning("Intento de webhook con token inválido.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido.",
        )


@router.post("/noticia", status_code=status.HTTP_201_CREATED)
async def recibir_noticia(
    payload: WebhookNoticiaPayload,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, object]:
    """Ingesta una noticia externa y la crea en estado borrador.

    Autenticación: Header `X-Webhook-Secret` con el valor de WEBHOOK_SECRET.

    La noticia se crea en estado `borrador`. Para publicarla, un editor
    debe generarla, aprobarla y publicarla desde el panel.
    """

    _verificar_token(x_webhook_secret)

    noticia = create_noticia(
        db,
        NoticiaCreate(
            hecho=payload.hecho,
            lugar=payload.lugar,
            categoria=payload.categoria,
            urgencia=payload.urgencia,
        ),
    )
    logger.info("Noticia %d creada vía webhook (hecho: %.60s...)", noticia.id, payload.hecho)
    return {"id": noticia.id, "estado": noticia.estado.value, "mensaje": "Noticia recibida correctamente."}
