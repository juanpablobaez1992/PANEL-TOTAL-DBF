"""Pruebas unitarias para servicios externos con mocks."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.services.facebook_service import publicar_en_facebook, publicar_en_instagram
from app.services.twitter_service import publicar_en_twitter
from app.services.wordpress_service import publicar_en_wordpress
from app.services.telegram_service import publicar_en_telegram


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

    def test_publicar_en_facebook_publica_con_imagen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "fb.jpg"
            image.write_bytes(b"fake-image")

            old_token = settings.meta_access_token
            old_page_id = settings.meta_page_id
            try:
                settings.meta_access_token = "token-meta"
                settings.meta_page_id = "page-123"
                FakeAsyncClient.responses = [
                    FakeResponse({"id": "photo-1"}),
                    FakeResponse({"id": "post-1", "post_id": "post-1"}),
                ]
                with patch("app.services.facebook_service.httpx.AsyncClient", FakeAsyncClient):
                    result = asyncio.run(
                        publicar_en_facebook(contenido="texto del post", imagen_path=str(image))
                    )
                self.assertTrue(result["exito"])
                self.assertIn(result["id"], ("post-1", "photo-1", None))
            finally:
                settings.meta_access_token = old_token
                settings.meta_page_id = old_page_id

    def test_publicar_en_wordpress_publica_entrada(self) -> None:
        old_wp_url = settings.wp_url
        old_wp_user = settings.wp_user
        old_wp_pass = settings.wp_app_password
        try:
            settings.wp_url = "https://example.com"
            settings.wp_user = "editor"
            settings.wp_app_password = "app-pass"
            FakeAsyncClient.responses = [
                FakeResponse({"id": 42, "link": "https://example.com/?p=42"}),
            ]
            with patch("app.services.wordpress_service.httpx.AsyncClient", FakeAsyncClient):
                result = asyncio.run(
                    publicar_en_wordpress(
                        titulo="Noticia de prueba",
                        contenido="<p>Cuerpo de la noticia</p>",
                        imagen_path=None,
                    )
                )
            self.assertTrue(result["exito"])
            self.assertEqual(result["id"], "42")
        finally:
            settings.wp_url = old_wp_url
            settings.wp_user = old_wp_user
            settings.wp_app_password = old_wp_pass

    def test_publicar_en_telegram_envía_mensaje(self) -> None:
        old_token = settings.telegram_bot_token
        old_chat = settings.telegram_chat_id
        try:
            settings.telegram_bot_token = "bot-token"
            settings.telegram_chat_id = "-100123456"
            FakeAsyncClient.responses = [
                FakeResponse({"ok": True, "result": {"message_id": 77}}),
            ]
            with patch("app.services.telegram_service.httpx.AsyncClient", FakeAsyncClient):
                result = asyncio.run(
                    publicar_en_telegram(contenido="Mensaje de prueba", imagen_path=None)
                )
            self.assertTrue(result["exito"])
        finally:
            settings.telegram_bot_token = old_token
            settings.telegram_chat_id = old_chat

    def test_publicar_en_instagram_sin_credenciales_devuelve_error(self) -> None:
        old_token = settings.meta_access_token
        old_ig = settings.meta_ig_account_id
        try:
            settings.meta_access_token = ""
            settings.meta_ig_account_id = ""
            result = asyncio.run(
                publicar_en_instagram(contenido="sin creds", imagen_path=None)
            )
            self.assertFalse(result["exito"])
            self.assertIsNotNone(result["error"])
        finally:
            settings.meta_access_token = old_token
            settings.meta_ig_account_id = old_ig

    def test_publicar_en_wordpress_sin_credenciales_devuelve_error(self) -> None:
        old_wp_url = settings.wp_url
        old_wp_user = settings.wp_user
        old_wp_pass = settings.wp_app_password
        try:
            settings.wp_url = ""
            settings.wp_user = ""
            settings.wp_app_password = ""
            result = asyncio.run(
                publicar_en_wordpress(titulo="test", contenido="test", imagen_path=None)
            )
            self.assertFalse(result["exito"])
        finally:
            settings.wp_url = old_wp_url
            settings.wp_user = old_wp_user
            settings.wp_app_password = old_wp_pass
