"""Factory principal de FastAPI para Despacho."""

from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.controllers.panel_user_controller import seed_admin_user
from app.controllers.canal_controller import migrate_legacy_channel_configs, seed_default_canales
from app.database import Base, SessionLocal, engine
from app.models.enums import RolPanel
from app.models.schemas import AppInfo
from app.services.integraciones_service import get_missing_startup_configs
from app.utils.db_schema import ensure_database_schema
from app.utils.passwords import hash_password
from app.utils.scheduler import scheduler_loop
from app.views.api.automation_router import router as automation_router
from app.views.api.canales_router import router as canales_router
from app.views.api.noticias_router import router as noticias_router
from app.views.api.panel_router import router as panel_router
from app.views.api.publicaciones_router import router as publicaciones_router
from app.views.api.system_router import router as system_router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar la aplicación."""

    _ = app
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_database_schema(engine)
    db = SessionLocal()
    try:
        seed_default_canales(db)
        migrate_legacy_channel_configs(db)
        seed_admin_user(
            db,
            username=settings.panel_admin_username,
            password_hash=hash_password(settings.panel_admin_password),
            role=RolPanel.admin,
        )
    finally:
        db.close()
    faltantes = get_missing_startup_configs()
    if faltantes:
        logger.warning("Configuración incompleta para integraciones externas: %s", ", ".join(faltantes))
    stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(scheduler_loop(stop_event))
    app.state.scheduler_stop_event = stop_event
    app.state.scheduler_task = scheduler_task
    yield
    stop_event.set()
    await scheduler_task


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/", response_model=AppInfo)
    async def root() -> AppInfo:
        """Información básica de la app."""

        return AppInfo(app=settings.app_name, env=settings.app_env, version="0.1.0", status="ok")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check simple."""

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy"}

    app.include_router(canales_router)
    app.include_router(noticias_router)
    app.include_router(publicaciones_router)
    app.include_router(system_router)
    app.include_router(panel_router)
    app.include_router(automation_router)
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")
    return app
