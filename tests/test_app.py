"""Pruebas básicas de humo para Despacho."""

from __future__ import annotations

import unittest
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import close_all_sessions

from app.controllers.noticia_controller import procesar_noticias_programadas
from app.database import SessionLocal, engine
from app.main import create_app
from app.models.canal import Canal
from app.models.noticia import Noticia
from app.models.panel_session import PanelSession
from app.models.panel_user import PanelUser
from app.models.publicacion import Publicacion
from app.utils.credentials import encrypt_config


class DespachoAppTests(unittest.TestCase):
    """Verifica que la API principal responda y orqueste el flujo base."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client_manager = TestClient(self.app)
        self.client = self.client_manager.__enter__()
        self._reset_data()

    def tearDown(self) -> None:
        self.client_manager.__exit__(None, None, None)
        close_all_sessions()
        engine.dispose()

    @classmethod
    def tearDownClass(cls) -> None:
        close_all_sessions()
        engine.dispose()

    def _reset_data(self) -> None:
        """Limpia noticias/publicaciones y regenera seed de canales si hace falta."""

        db = SessionLocal()
        try:
            db.execute(delete(PanelSession))
            db.execute(delete(PanelUser).where(PanelUser.username != "admin"))
            db.execute(delete(Publicacion))
            db.execute(delete(Noticia))
            db.commit()
            for canal in db.query(Canal).all():
                canal.config_json = encrypt_config({})
            db.commit()
            canales = db.query(Canal).count()
            if canales == 0:
                self.client.post("/api/canales/seed")
        finally:
            db.close()

    def test_root_health_and_seed(self) -> None:
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["app"], "Despacho")

        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "healthy")

        canales = self.client.get("/api/canales/")
        self.assertEqual(canales.status_code, 200)
        self.assertEqual(len(canales.json()), 6)
        self.assertEqual(canales.json()[0]["config"], {})

        integraciones = self.client.get("/api/sistema/integraciones")
        self.assertEqual(integraciones.status_code, 200)
        self.assertEqual(len(integraciones.json()), 2)

    def test_crear_generar_y_publicar_noticia(self) -> None:
        creada = self.client.post(
            "/api/noticias/",
            json={
                "hecho": "Temporal de granizo afectó viñedos en zona este",
                "lugar": "San Rafael",
                "categoria": "sociedad",
                "urgencia": "breaking",
            },
        )
        self.assertEqual(creada.status_code, 201)
        noticia_id = creada.json()["id"]

        generada = self.client.post(f"/api/noticias/{noticia_id}/generar")
        self.assertEqual(generada.status_code, 200)
        self.assertEqual(generada.json()["estado"], "generado")
        self.assertEqual(len(generada.json()["publicaciones"]), 6)

        publicar_sin_aprobar = self.client.post(f"/api/publicaciones/noticia/{noticia_id}/publicar")
        self.assertEqual(publicar_sin_aprobar.status_code, 400)
        self.assertIn("aprobada", publicar_sin_aprobar.json()["detail"])

        aprobada = self.client.post(f"/api/noticias/{noticia_id}/aprobar")
        self.assertEqual(aprobada.status_code, 200)
        self.assertEqual(aprobada.json()["estado"], "aprobado")

        publicada = self.client.post(f"/api/publicaciones/noticia/{noticia_id}/publicar")
        self.assertEqual(publicada.status_code, 200)
        self.assertEqual(len(publicada.json()), 6)

    def test_filtro_estado_invalido_devuelve_400(self) -> None:
        response = self.client.get("/api/noticias/?estado=inexistente")
        self.assertEqual(response.status_code, 400)

    def test_no_permite_crear_canales_duplicados(self) -> None:
        response = self.client.post(
            "/api/canales/",
            json={
                "nombre": "Otro WordPress",
                "tipo": "wordpress",
                "activo": True,
                "auto_publicar": False,
                "config_json": "{}",
                "orden": 99,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_preflight_devuelve_estado_por_canal(self) -> None:
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Prueba preflight", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        self.client.post(f"/api/noticias/{noticia_id}/generar")

        preflight = self.client.get(f"/api/noticias/{noticia_id}/preflight")
        self.assertEqual(preflight.status_code, 200)
        payload = preflight.json()
        self.assertEqual(payload["noticia_id"], noticia_id)
        self.assertEqual(len(payload["canales"]), 6)
        self.assertFalse(payload["lista_para_publicar"])

    def test_dashboard_requiere_auth_y_login_funciona(self) -> None:
        sin_auth = self.client.get("/api/panel/dashboard")
        self.assertEqual(sin_auth.status_code, 401)

        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]

        dashboard = self.client.get(
            "/api/panel/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("noticias_por_estado", dashboard.json())
        self.assertIn("integraciones", dashboard.json())
        self.assertEqual(login.json()["user"]["role"], "admin")

        refresh = self.client.post(
            "/api/panel/auth/refresh",
            json={"refresh_token": login.json()["refresh_token"]},
        )
        self.assertEqual(refresh.status_code, 200)

        logout = self.client.post(
            "/api/panel/auth/logout",
            json={"refresh_token": refresh.json()["refresh_token"]},
        )
        self.assertEqual(logout.status_code, 204)

        refresh_again = self.client.post(
            "/api/panel/auth/refresh",
            json={"refresh_token": refresh.json()["refresh_token"]},
        )
        self.assertEqual(refresh_again.status_code, 401)

    def test_panel_usuarios_crud_basico(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        crear = self.client.post(
            "/api/panel/usuarios",
            headers=headers,
            json={"username": "editor1", "password": "secreto123", "role": "editor", "activo": True},
        )
        self.assertEqual(crear.status_code, 201)
        user_id = crear.json()["id"]

        listar = self.client.get("/api/panel/usuarios?page=1&page_size=10", headers=headers)
        self.assertEqual(listar.status_code, 200)
        self.assertGreaterEqual(listar.json()["total"], 1)

        actualizar = self.client.put(
            f"/api/panel/usuarios/{user_id}",
            headers=headers,
            json={"role": "admin", "activo": False},
        )
        self.assertEqual(actualizar.status_code, 200)
        self.assertEqual(actualizar.json()["role"], "admin")
        self.assertFalse(actualizar.json()["activo"])

    def test_editor_no_puede_gestionar_usuarios(self) -> None:
        admin_login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        self.client.post(
            "/api/panel/usuarios",
            headers=admin_headers,
            json={"username": "editor2", "password": "secreto123", "role": "editor", "activo": True},
        )

        editor_login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "editor2", "password": "secreto123"},
        )
        editor_headers = {"Authorization": f"Bearer {editor_login.json()['access_token']}"}
        forbidden = self.client.get("/api/panel/usuarios", headers=editor_headers)
        self.assertEqual(forbidden.status_code, 403)

    def test_panel_listado_y_detalle_noticias(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Detalle panel", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        self.client.post(f"/api/noticias/{noticia_id}/generar")
        self.client.post(f"/api/noticias/{noticia_id}/aprobar")

        listado = self.client.get("/api/panel/noticias?page=1&page_size=5&q=Detalle", headers=headers)
        self.assertEqual(listado.status_code, 200)
        self.assertGreaterEqual(listado.json()["total"], 1)

        detalle = self.client.get(f"/api/panel/noticias/{noticia_id}", headers=headers)
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.json()["noticia"]["id"], noticia_id)
        self.assertGreaterEqual(len(detalle.json()["timeline"]), 2)

    def test_acciones_rapidas_dashboard(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Acciones rápidas", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]

        generar = self.client.post(f"/api/panel/noticias/{noticia_id}/acciones/generar", headers=headers)
        self.assertEqual(generar.status_code, 200)

        aprobar = self.client.post(f"/api/panel/noticias/{noticia_id}/acciones/aprobar", headers=headers)
        self.assertEqual(aprobar.status_code, 200)

        preflight = self.client.get(f"/api/panel/noticias/{noticia_id}/acciones/preflight", headers=headers)
        self.assertEqual(preflight.status_code, 200)

        publicar = self.client.post(f"/api/panel/noticias/{noticia_id}/acciones/publicar", headers=headers)
        self.assertEqual(publicar.status_code, 200)

    def test_panel_puede_actualizar_estado_editorial_permitido(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Cambio de estado", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        self.client.post(f"/api/noticias/{noticia_id}/generar")
        self.client.post(f"/api/noticias/{noticia_id}/aprobar")

        response = self.client.patch(
            f"/api/panel/noticias/{noticia_id}/estado",
            headers=headers,
            json={"estado": "borrador"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["noticia"]["estado"], "borrador")

    def test_panel_puede_filtrar_usuarios_y_sesiones(self) -> None:
        admin_login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        self.client.post(
            "/api/panel/usuarios",
            headers=headers,
            json={"username": "buscable", "password": "secreto123", "role": "editor", "activo": False},
        )

        usuarios = self.client.get("/api/panel/usuarios?q=busca&activo=false", headers=headers)
        self.assertEqual(usuarios.status_code, 200)
        self.assertGreaterEqual(usuarios.json()["total"], 1)

        sesiones = self.client.get("/api/panel/sesiones?solo_activas=true", headers=headers)
        self.assertEqual(sesiones.status_code, 200)
        self.assertGreaterEqual(sesiones.json()["total"], 1)

    def test_panel_puede_editar_editorial_y_copy(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Editar contenido", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        generada = self.client.post(f"/api/noticias/{noticia_id}/generar")
        publicacion_id = generada.json()["publicaciones"][0]["id"]

        editorial = self.client.patch(
            f"/api/panel/noticias/{noticia_id}/editorial",
            headers=headers,
            json={"titular": "Titular manual", "bajada": "Bajada manual", "cuerpo": "Cuerpo manual"},
        )
        self.assertEqual(editorial.status_code, 200)
        self.assertEqual(editorial.json()["noticia"]["titular"], "Titular manual")

        publicacion = self.client.patch(
            f"/api/panel/publicaciones/{publicacion_id}",
            headers=headers,
            json={"contenido": "Copy manual actualizado"},
        )
        self.assertEqual(publicacion.status_code, 200)
        self.assertEqual(publicacion.json()["noticia"]["publicaciones"][0]["contenido"], "Copy manual actualizado")

    def test_panel_puede_actualizar_estado_manual_de_publicacion_con_guardrails(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Estado manual publicacion", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        generada = self.client.post(f"/api/noticias/{noticia_id}/generar")
        publicacion_id = generada.json()["publicaciones"][0]["id"]

        error_response = self.client.patch(
            f"/api/panel/publicaciones/{publicacion_id}/estado",
            headers=headers,
            json={"estado": "error"},
        )
        self.assertEqual(error_response.status_code, 400)

        marcada = self.client.patch(
            f"/api/panel/publicaciones/{publicacion_id}/estado",
            headers=headers,
            json={"estado": "error", "error_log": "Fallo manual de prueba"},
        )
        self.assertEqual(marcada.status_code, 200)
        self.assertEqual(marcada.json()["noticia"]["publicaciones"][0]["estado"], "error")

    def test_panel_puede_publicar_y_reintentar_publicacion_individual(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Publicacion individual", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        generada = self.client.post(f"/api/noticias/{noticia_id}/generar")
        self.client.post(f"/api/noticias/{noticia_id}/aprobar")
        publicacion_id = generada.json()["publicaciones"][4]["id"]

        publicada = self.client.post(
            f"/api/panel/publicaciones/{publicacion_id}/publicar",
            headers=headers,
        )
        self.assertEqual(publicada.status_code, 200)
        self.assertIn("publicaciones_timeline", publicada.json())

        error_manual = self.client.patch(
            f"/api/panel/publicaciones/{publicacion_id}/estado",
            headers=headers,
            json={"estado": "error", "error_log": "Error de reproceso"},
        )
        self.assertEqual(error_manual.status_code, 200)

        reintento = self.client.post(
            f"/api/panel/publicaciones/{publicacion_id}/reintentar",
            headers=headers,
        )
        self.assertEqual(reintento.status_code, 200)

    def test_sesiones_listado_y_revocacion(self) -> None:
        login = self.client.post(
            "/api/panel/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        refresh = self.client.post(
            "/api/panel/auth/refresh",
            json={"refresh_token": login.json()["refresh_token"]},
        )
        headers = {"Authorization": f"Bearer {refresh.json()['access_token']}"}

        sesiones = self.client.get("/api/panel/sesiones?page=1&page_size=10", headers=headers)
        self.assertEqual(sesiones.status_code, 200)
        self.assertGreaterEqual(sesiones.json()["total"], 1)
        session_id = sesiones.json()["items"][0]["id"]

        revocar = self.client.post(f"/api/panel/sesiones/revocar/{session_id}", headers=headers)
        self.assertEqual(revocar.status_code, 204)

    def test_programacion_y_scheduler_publican_noticia(self) -> None:
        creada = self.client.post(
            "/api/noticias/",
            json={"hecho": "Prueba scheduler", "lugar": "San Rafael", "categoria": "general"},
        )
        noticia_id = creada.json()["id"]
        generada = self.client.post(f"/api/noticias/{noticia_id}/generar").json()
        self.client.post(f"/api/noticias/{noticia_id}/aprobar")

        for publicacion in generada["publicaciones"]:
            self.client.post(f"/api/publicaciones/{publicacion['id']}/omitir")

        futura = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        programada = self.client.post(
            f"/api/noticias/{noticia_id}/programar",
            json={"programada_para": futura},
        )
        self.assertEqual(programada.status_code, 200)
        self.assertIsNotNone(programada.json()["programada_para"])

        db = SessionLocal()
        try:
            noticia = db.get(Noticia, noticia_id)
            assert noticia is not None
            noticia.programada_para = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
            procesadas = asyncio.run(procesar_noticias_programadas(db))
            self.assertIn(noticia_id, procesadas)
            db.refresh(noticia)
            self.assertIsNone(noticia.programada_para)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
