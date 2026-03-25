# Despacho

Backend API para publicar noticias de De Buena Fe Digital en múltiples canales a partir de un input mínimo.

## Stack

- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- SQLite
- httpx
- Pillow

## Estructura

La aplicación sigue un patrón MVC estricto:

- `app/models`: modelos SQLAlchemy y schemas Pydantic
- `app/controllers`: lógica de negocio y orquestación
- `app/services`: integraciones externas
- `app/views/api`: routers HTTP
- `app/utils`: helpers compartidos

## Puesta en marcha

1. Crear entorno virtual e instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Copiar variables de entorno:

```bash
copy .env.example .env
```

Si ya existe `.env`, completá ahí las credenciales reales.

3. Levantar la API:

```bash
uvicorn main:app --reload --port 8000
```

4. Levantar el panel React:

```bash
cd frontend
npm install
npm run dev
```

## Checks rápidos

```bash
python -c "from app import create_app; create_app()"
python -m unittest discover -s tests -v
python scripts/check_integrations.py
cd frontend && npm run build
```

## Endpoints principales

- `GET /`
- `GET /health`
- `GET /api/canales/`
- `POST /api/canales/seed`
- `GET /api/noticias/`
- `POST /api/noticias/`
- `POST /api/noticias/{id}/generar`
- `GET /api/noticias/{id}/preflight`
- `POST /api/noticias/{id}/programar`
- `POST /api/noticias/{id}/cancelar-programacion`
- `POST /api/noticias/despacho`
- `POST /api/publicaciones/noticia/{id}/publicar`
- `POST /api/panel/auth/login`
- `POST /api/panel/auth/refresh`
- `POST /api/panel/auth/logout`
- `GET /api/panel/me`
- `GET /api/panel/dashboard`
- `GET /api/panel/actividad`
- `GET /api/panel/notificaciones`
- `GET /api/panel/sesiones`
- `POST /api/panel/sesiones/revocar/{id}`
- `GET /api/panel/usuarios`
- `POST /api/panel/usuarios`
- `PUT /api/panel/usuarios/{id}`
- `GET /api/panel/noticias`
- `GET /api/panel/noticias/{id}`
- `PATCH /api/panel/noticias/{id}/estado`
- `POST /api/panel/noticias/{id}/acciones/generar`
- `POST /api/panel/noticias/{id}/acciones/aprobar`
- `GET /api/panel/noticias/{id}/acciones/preflight`
- `POST /api/panel/noticias/{id}/acciones/programar`
- `POST /api/panel/noticias/{id}/acciones/cancelar-programacion`
- `POST /api/panel/noticias/{id}/acciones/publicar`
- `GET /api/sistema/integraciones`

## Panel React

- Rutas disponibles: `/login`, `/dashboard`, `/noticias/:id?`, `/usuarios`, `/sesiones`
- El panel hidrata perfil y permisos con `GET /api/panel/me`
- Dashboard y vistas operativas usan refresh automÃ¡tico periÃ³dico para reflejar cambios de estado sin recargar manualmente
- La pantalla de noticias permite generar, aprobar, revalidar preflight, programar y publicar desde acciones rÃ¡pidas
- La pantalla de usuarios ya usa formulario real para crear cuentas persistidas

## Notas

- Si no hay credenciales de IA configuradas, el sistema usa una generación local de respaldo.
- `config_json` se guarda cifrado en la base de datos usando `SECRET_KEY`; la API trabaja con `config`.
- Si cambiás `SECRET_KEY`, los `config_json` ya cifrados dejan de ser legibles y hay que volver a cargar las credenciales de canales.
- Instagram requiere `PUBLIC_BASE_URL` apuntando a una URL pública real para que Meta pueda leer la imagen.
- Twitter/X publica vía OAuth 1.0a con las credenciales ya definidas en `.env`.
- WhatsApp queda resuelto como publicación manual con copy listo para copiar y pegar.

## Prueba real de Instagram y X

1. Completar `.env` con credenciales reales de Meta y X.
2. Asegurar que `PUBLIC_BASE_URL` sea accesible desde internet.
3. Ejecutar:

```bash
python scripts/check_integrations.py
uvicorn main:app --reload --port 8000
```

4. Crear una noticia, generarla, aprobarla y publicar:

```bash
curl -X POST http://localhost:8000/api/noticias/ ^
  -H "Content-Type: application/json" ^
  -d "{\"hecho\":\"Prueba de publicación real\",\"lugar\":\"San Rafael\",\"categoria\":\"general\"}"

curl -X POST http://localhost:8000/api/noticias/1/generar
curl -X POST http://localhost:8000/api/noticias/1/aprobar
curl -X POST http://localhost:8000/api/publicaciones/noticia/1/publicar
```
