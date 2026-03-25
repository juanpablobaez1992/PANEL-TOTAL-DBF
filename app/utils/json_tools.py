"""Ayudas para serialización JSON."""

from __future__ import annotations

import json
from typing import Any


def normalize_json_text(raw_text: str) -> dict[str, Any]:
    """Intenta convertir texto JSON o pseudo-JSON en un diccionario."""

    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)
