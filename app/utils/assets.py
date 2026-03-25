"""Helpers para convertir archivos locales en URLs públicas."""

from __future__ import annotations

from pathlib import Path

from app.config import settings


def local_path_to_public_url(file_path: str) -> str:
    """Convierte un archivo bajo uploads a una URL pública servida por FastAPI."""

    absolute = Path(file_path).resolve()
    uploads = settings.upload_path.resolve()
    try:
        relative = absolute.relative_to(uploads).as_posix()
    except ValueError as error:
        raise ValueError("La imagen debe existir dentro de UPLOAD_DIR para exponerse públicamente.") from error
    return f"{settings.public_base_url.rstrip('/')}/uploads/{relative}"
