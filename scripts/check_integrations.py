"""Chequeo rápido de configuración y conectividad para Meta y X."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.integraciones_service import check_integraciones
from app.services.twitter_service import TWITTER_API_URL


async def main() -> None:
    """Ejecuta los chequeos de integraciones."""

    results = await check_integraciones()
    print(f"PUBLIC_BASE_URL={settings.public_base_url}")
    print(f"TWITTER_POST_URL={TWITTER_API_URL}")
    for result in results:
        estado = "OK" if result["ok"] else "ERROR"
        print(f"[{estado}] {result['nombre']}: {result['detalle']}")


if __name__ == "__main__":
    asyncio.run(main())
