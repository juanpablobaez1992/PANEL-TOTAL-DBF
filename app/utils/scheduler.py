"""Scheduler liviano para publicaciones programadas."""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.controllers.noticia_controller import procesar_noticias_programadas
from app.database import SessionLocal

logger = logging.getLogger(__name__)


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    """Loop periódico para procesar noticias programadas."""

    while not stop_event.is_set():
        db = SessionLocal()
        try:
            processed = await procesar_noticias_programadas(db)
            if processed:
                logger.info("Scheduler procesó noticias programadas: %s", processed)
        except Exception as error:  # noqa: BLE001
            logger.exception("Fallo en scheduler de publicaciones: %s", error)
        finally:
            db.close()

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.scheduler_interval_seconds)
        except TimeoutError:
            continue
