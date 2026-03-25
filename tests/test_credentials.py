"""Pruebas de cifrado y exposición de configuración de canales."""

from __future__ import annotations

import unittest

from app.controllers.canal_controller import update_canal
from sqlalchemy.orm import close_all_sessions

from app.database import SessionLocal, engine
from app.models.canal import Canal
from app.models.schemas import CanalUpdate
from app.utils.credentials import decrypt_config, encrypt_config


class CredentialTests(unittest.TestCase):
    """Verifica cifrado y descifrado de config_json."""

    def test_encrypt_roundtrip(self) -> None:
        payload = {"token": "secreto", "page_id": "123"}
        encrypted = encrypt_config(payload)
        self.assertTrue(encrypted.startswith("enc::"))
        self.assertEqual(decrypt_config(encrypted), payload)

    def test_legacy_plain_json_still_reads(self) -> None:
        self.assertEqual(decrypt_config('{"token":"abc"}'), {"token": "abc"})

    def test_controller_persists_encrypted_and_model_exposes_decrypted(self) -> None:
        db = SessionLocal()
        try:
            canal = db.query(Canal).first()
            self.assertIsNotNone(canal)
            assert canal is not None
            original = canal.config_json
            updated = update_canal(
                db,
                canal.id,
                CanalUpdate(config={"usuario": "admin", "password": "clave"}),
            )
            stored = db.get(Canal, updated.id)
            assert stored is not None
            self.assertTrue(stored.config_json.startswith("enc::"))
            self.assertEqual(stored.config["usuario"], "admin")
        finally:
            if "canal" in locals() and canal is not None:
                canal.config_json = original
                db.commit()
            db.commit()
            db.close()

    @classmethod
    def tearDownClass(cls) -> None:
        close_all_sessions()
        engine.dispose()
