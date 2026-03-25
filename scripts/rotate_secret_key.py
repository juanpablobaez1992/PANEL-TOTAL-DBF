"""Rota SECRET_KEY re-encriptando todos los config_json de canales.

Uso:
    python scripts/rotate_secret_key.py --new-key <NUEVA_CLAVE>

La clave actual se lee desde el entorno (SECRET_KEY).
El script actualiza la DB en el lugar y NO modifica el archivo .env.
Después de correrlo, actualizá SECRET_KEY en tu .env/.env de Docker.

Ejemplo de workflow seguro:
    1. Generá nueva clave:
       python -c "import secrets; print(secrets.token_hex(32))"
    2. Rotá la clave en la DB:
       SECRET_KEY=clave_actual python scripts/rotate_secret_key.py --new-key <nueva>
    3. Actualizá SECRET_KEY en .env con el valor nuevo.
    4. Reiniciá el servidor/contenedor.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.canal import Canal
from app.utils.credentials import decrypt_config, encrypt_config


def rotate_secret_key(new_key: str, *, dry_run: bool = False) -> None:
    """Re-encripta todos los config_json de canales con la nueva clave."""

    old_key = settings.secret_key
    if not old_key:
        print("ERROR: SECRET_KEY actual no configurada en el entorno.", file=sys.stderr)
        sys.exit(1)

    if new_key == old_key:
        print("La nueva clave es idéntica a la actual. No se realizaron cambios.")
        return

    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        canales = list(db.scalars(select(Canal)))
        print(f"Canales encontrados: {len(canales)}")

        rotados = 0
        for canal in canales:
            if not canal.config_json:
                print(f"  Canal {canal.id} ({canal.nombre}): sin config_json, omitido.")
                continue
            try:
                config = decrypt_config(canal.config_json)
            except Exception as exc:  # noqa: BLE001
                print(f"  Canal {canal.id} ({canal.nombre}): ERROR al desencriptar — {exc}", file=sys.stderr)
                continue

            if dry_run:
                print(f"  Canal {canal.id} ({canal.nombre}): se re-encriptaría ({len(config)} claves).")
            else:
                # Temporalmente cambiamos la clave para encriptar con la nueva
                original_key = settings.secret_key
                settings.secret_key = new_key
                try:
                    canal.config_json = encrypt_config(config)
                finally:
                    settings.secret_key = original_key
                rotados += 1
                print(f"  Canal {canal.id} ({canal.nombre}): re-encriptado.")

        if not dry_run:
            db.commit()
            print(f"\nRotación completada. {rotados}/{len(canales)} canales re-encriptados.")
            print("\nSiguiente paso: actualizá SECRET_KEY en tu .env con el nuevo valor y reiniciá el servidor.")
        else:
            print(f"\nDry-run completado. {len(canales)} canales serían procesados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rota SECRET_KEY re-encriptando config_json de canales.")
    parser.add_argument("--new-key", required=True, help="La nueva SECRET_KEY a usar.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué se haría sin modificar la DB.",
    )
    args = parser.parse_args()
    rotate_secret_key(args.new_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
