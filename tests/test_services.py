"""Pruebas unitarias para servicios externos con mocks."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.services.facebook_service import publicar_en_instagram
from app.services.twitter_service import publicar_en_twitter


class FakeResponse:
    """Respuesta fake de httpx con interfaz mínima."""

    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    """Cliente async fake basado en una cola de respuestas."""

    responses: list[FakeResponse] = []

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, D401
        _ = (args, kwargs)

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        _ = (exc_type, exc, tb)

    async def post(self, *args, **kwargs) -> FakeResponse:  # noqa: ANN002
        _ = (args, kwargs)
        return self.responses.pop(0)

    async def get(self, *args, **kwargs) -> FakeResponse:  # noqa: ANN002
        _ = (args, kwargs)
        return self.responses.pop(0)


class ServiceTests(unittest.TestCase):
    """Valida integración básica de servicios reales con mocks."""

    def test_publicar_en_instagram_realiza_flujo_container_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            uploads = Path(tmp) / "uploads"
            uploads.mkdir(parents=True, exist_ok=True)
            image = uploads / "ig.jpg"
            image.write_bytes(b"fake-image")

            old_upload_dir = settings.upload_dir
            old_base = settings.public_base_url
            old_ig_id = settings.meta_ig_account_id
            old_token = settings.meta_access_token
            try:
                settings.upload_dir = str(uploads)
                settings.public_base_url = "https://public.example.com"
                settings.meta_ig_account_id = "ig-user-1"
                settings.meta_access_token = "token-meta"
                FakeAsyncClient.responses = [
                    FakeResponse({"id": "creation-1"}),
                    FakeResponse({"id": "media-1"}),
                    FakeResponse({"id": "media-1", "permalink": "https://instagram.com/p/abc"}),
                ]
                with patch("app.services.facebook_service.httpx.AsyncClient", FakeAsyncClient):
                    result = asyncio.run(
                        publicar_en_instagram(contenido="caption", imagen_path=str(image))
                    )
                self.assertTrue(result["exito"])
                self.assertEqual(result["id"], "media-1")
            finally:
                settings.upload_dir = old_upload_dir
                settings.public_base_url = old_base
                settings.meta_ig_account_id = old_ig_id
                settings.meta_access_token = old_token

    def test_publicar_en_twitter_publica_tweet_con_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "x.jpg"
            image.write_bytes(b"fake-image")

            old_values = (
                settings.twitter_api_key,
                settings.twitter_api_secret,
                settings.twitter_access_token,
                settings.twitter_access_secret,
            )
            try:
                settings.twitter_api_key = "api-key"
                settings.twitter_api_secret = "api-secret"
                settings.twitter_access_token = "access-token"
                settings.twitter_access_secret = "access-secret"
                FakeAsyncClient.responses = [
                    FakeResponse({"media_id_string": "999"}),
                    FakeResponse({"data": {"id": "123456"}}),
                ]
                with patch("app.services.twitter_service.httpx.AsyncClient", FakeAsyncClient):
                    result = asyncio.run(
                        publicar_en_twitter(contenido="tweet", imagen_path=str(image))
                    )
                self.assertTrue(result["exito"])
                self.assertEqual(result["id"], "123456")
            finally:
                (
                    settings.twitter_api_key,
                    settings.twitter_api_secret,
                    settings.twitter_access_token,
                    settings.twitter_access_secret,
                ) = old_values
