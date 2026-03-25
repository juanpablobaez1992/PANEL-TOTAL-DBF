"""Servicio de procesamiento de imágenes por plataforma."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

PLATFORM_SIZES: dict[str, tuple[int, int]] = {
    "wordpress": (1200, 630),
    "facebook": (1200, 630),
    "instagram": (1080, 1080),
    "twitter": (1200, 675),
    "whatsapp": (800, 418),
    "telegram": (800, 418),
}


def _cover_resize(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """Redimensiona una imagen haciendo crop tipo cover sin deformar."""

    target_width, target_height = target_size
    source_width, source_height = image.size
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        new_height = target_height
        new_width = int(new_height * source_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / source_ratio)

    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = max((new_width - target_width) // 2, 0)
    top = max((new_height - target_height) // 2, 0)
    return resized.crop((left, top, left + target_width, top + target_height))


def procesar_imagenes_por_canal(original_path: str) -> dict[str, str]:
    """Procesa una imagen original y genera versiones por plataforma."""

    output_dir = settings.upload_path / "procesadas"
    output_dir.mkdir(parents=True, exist_ok=True)

    original = Path(original_path)
    generated: dict[str, str] = {}

    with Image.open(original) as image:
        if image.mode in {"RGBA", "LA", "P"}:
            image = image.convert("RGB")
        elif image.mode != "RGB":
            image = image.convert("RGB")

        for platform, size in PLATFORM_SIZES.items():
            processed = _cover_resize(image, size)
            target = output_dir / f"{original.stem}_{platform}.jpg"
            processed.save(target, format="JPEG", quality=85, optimize=True)
            generated[platform] = str(target)
            logger.info("Imagen procesada para %s en %s", platform, target)

    return generated
