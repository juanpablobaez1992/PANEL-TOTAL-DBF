"""Utilidades de almacenamiento de archivos."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


async def save_upload_file(upload: UploadFile, subdir: str = "original") -> str:
    """Guarda un archivo subido y devuelve su path absoluto."""

    suffix = Path(upload.filename or "archivo.bin").suffix.lower() or ".bin"
    target_dir = settings.upload_path / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid.uuid4().hex}{suffix}"

    content = await upload.read()
    max_size = settings.max_image_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise ValueError(f"El archivo supera el máximo permitido de {settings.max_image_size_mb} MB.")

    target_path.write_bytes(content)
    logger.info("Archivo guardado en %s", target_path)
    return str(target_path)
