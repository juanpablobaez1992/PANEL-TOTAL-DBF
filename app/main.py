"""Factory principal de FastAPI para Despacho."""

from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import settings
from app.controllers.panel_user_controller import seed_admin_user
from app.utils.limiter import panel_limiter
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
from app.views.api.webhook_router import router as webhook_router

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar la aplicación."""

    _ = app
    # Resetear rate limiter al iniciar (importante en tests para aislar entre instancias)
    panel_limiter._storage.reset()
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

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/", response_model=AppInfo)
    async def root() -> AppInfo:
        """Información básica de la app."""

        return AppInfo(app=settings.app_name, env=settings.app_env, version="0.1.0", status="ok")

    @app.get("/health")
    async def health(request: Request) -> dict[str, object]:
        """Health check con verificación de dependencias."""

        checks: dict[str, object] = {}

        # Base de datos
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["database"] = f"error: {exc}"

        # Scheduler
        scheduler_task = getattr(app.state, "scheduler_task", None)
        if scheduler_task is None:
            checks["scheduler"] = "not started"
        elif scheduler_task.done():
            checks["scheduler"] = "stopped"
        else:
            checks["scheduler"] = "running"

        # Configuración de IA
        ai_configured = bool(
            settings.gemini_api_key or settings.claude_api_key
        )
        checks["ai"] = "configured" if ai_configured else "missing credentials"

        # Estado general
        all_ok = checks["database"] == "ok" and checks["scheduler"] == "running"
        status_code = 200 if all_ok else 503
        body = {"status": "healthy" if all_ok else "degraded", "checks": checks}

        if status_code != 200:
            return JSONResponse(content=body, status_code=status_code)
        return body

    app.include_router(canales_router)
    app.include_router(noticias_router)
    app.include_router(publicaciones_router)
    app.include_router(system_router)
    app.include_router(panel_router)
    app.include_router(automation_router)
    app.include_router(webhook_router)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")
    return app
