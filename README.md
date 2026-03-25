# Despacho — Panel de Distribución de Noticias

Plataforma de publicación multicanal para **De Buena Fe Digital**. Un periodista ingresa el hecho con un mínimo de datos, la IA genera el contenido para cada canal, y el sistema distribuye automáticamente (o con aprobación manual) a WordPress, Facebook, Instagram, Twitter/X, Telegram y WhatsApp.

---

## Cómo funciona

```
Periodista ingresa el hecho
        ↓
   IA genera contenido adaptado por canal
        ↓
  Editor aprueba (o se auto-publica si está configurado)
        ↓
  Distribución simultánea a todos los canales activos
```

Cada canal recibe su versión optimizada: artículo largo para WordPress, copy corto para Twitter/X, caption para Instagram, etc.

---

## Inicio rápido

### Opción A — Con Make (recomendado)

```bash
# 1. Configurar entorno
cp .env.example .env          # editar con tus credenciales
make install                  # instala Python + Node deps

# 2. Levantar
make dev-back                 # FastAPI en :8000
make dev-front                # React en :5173 (otra terminal)
```

### Opción B — Manual

```bash
# Backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # completar credenciales
uvicorn main:app --reload --port 8000

# Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

### Opción C — Docker (producción)

```bash
cp .env.example .env          # completar credenciales
docker compose up -d --build
# Frontend en :8080, backend interno en :8000
```

---

## Panel web

Abrí el navegador en `http://localhost:5173` (dev) o `http://localhost:8080` (Docker).

| Ruta | Acceso | Descripción |
|------|--------|-------------|
| `/login` | Público | Inicio de sesión |
| `/dashboard` | Todos | Métricas y actividad reciente |
| `/noticias` | Todos | Crear, generar, aprobar y publicar noticias |
| `/automation` | Admin | Reglas de publicación automática |
| `/canales` | Admin | Configurar credenciales de cada canal |
| `/usuarios` | Admin | Gestión de cuentas del panel |
| `/sesiones` | Admin | Sesiones activas y revocación |

**Credenciales por defecto:** `admin` / `admin` (cambialas en `.env` antes de producción).

---

## Stack

**Backend**
- Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2
- SQLite (dev) / PostgreSQL (producción Docker)
- httpx · Pillow · cryptography · slowapi

**Frontend**
- React 19 · React Router 7 · Vite 8
- Sin UI framework externo — CSS propio

**Infraestructura**
- Docker Compose (backend + PostgreSQL + Nginx/frontend)
- Nginx como reverse proxy en el VPS

---

## Configuración de canales

Todas las credenciales de canales se guardan **cifradas** en la base de datos con `SECRET_KEY`. Se configuran desde el panel web (sección Canales) sin necesidad de tocar el `.env`.

Las variables de entorno son solo para el arranque inicial. Ver `.env.example` para la lista completa.

**Variables mínimas para empezar:**

```env
SECRET_KEY=una-clave-larga-y-aleatoria
APP_ENV=development
AI_PROVIDER=gemini          # o claude
GEMINI_API_KEY=tu-api-key
PANEL_ADMIN_USERNAME=admin
PANEL_ADMIN_PASSWORD=una-contraseña-segura
PUBLIC_BASE_URL=http://localhost:8000   # debe ser URL pública en producción
```

> **Importante:** `PUBLIC_BASE_URL` debe ser una URL accesible desde internet para que Instagram pueda descargar las imágenes. En desarrollo local, Instagram no funcionará.

---

## Canales soportados

| Canal | Tipo de contenido | Auth |
|-------|-------------------|------|
| WordPress | Artículo completo con imagen | Basic Auth (App Password) |
| Facebook | Post con foto o texto | Meta Graph API |
| Instagram | Imagen + caption | Meta Graph API |
| Twitter / X | Tweet corto con imagen | OAuth 1.0a |
| Telegram | Mensaje con o sin imagen | Bot API |
| WhatsApp | Copy listo para pegar | Manual |

---

## Flujo editorial

```
borrador → generando → generado → aprobado → publicado
                                            ↘ error
```

1. **Crear** noticia con hecho, lugar y categoría
2. **Generar** — la IA produce titular, bajada, cuerpo y copy por canal
3. **Aprobar** — el editor valida el contenido
4. **Publicar** — inmediatamente o programado para más tarde

Las noticias con `urgencia: breaking` pueden configurarse para **auto-publicarse** sin aprobación manual si `AUTO_PUBLISH_GLOBAL=true`.

---

## Comandos útiles

```bash
make test                     # corre todos los tests de Python
make lint                     # ESLint en el frontend
make check-integrations       # verifica credenciales de APIs externas
make logs                     # tail de logs Docker en tiempo real
make up / make down           # levantar / bajar contenedores
make rotate-key NEW_KEY=xxx   # rotar SECRET_KEY sin perder datos
```

Ver `make help` para la lista completa.

---

## Deploy en VPS (Hostinger / cualquier VPS con Docker)

### Pasos iniciales

```bash
# En el VPS
git clone <repo> /docker/panel-total-dbf
cd /docker/panel-total-dbf
cp .env.example .env
# Editar .env con credenciales reales
docker compose up -d --build
```

### Nginx en el host

Usar `deploy/nginx/hostinger.conf` como base. Solo ajustá el dominio:

```nginx
server_name despacho.tudominio.com;
proxy_pass http://127.0.0.1:8080;
```

Luego activar SSL:
```bash
certbot --nginx -d despacho.tudominio.com
```

### Deploy desde tu PC (PowerShell)

Si tenés el alias SSH `panel-vps` configurado:

```powershell
.\scripts\deploy.ps1          # deploy normal
.\scripts\deploy.ps1 -Push    # git push + deploy
.\scripts\deploy.ps1 -Logs    # ver logs en vivo
```

### Arquitectura Docker

```
Internet → Nginx (host) → :8080 (despacho_frontend/Nginx)
                                    ↓
                          /api, /uploads → :8000 (despacho_backend/FastAPI)
                                    ↓
                              despacho_db (PostgreSQL)
```

---

## Webhook de ingesta

Si querés que sistemas externos (feeds RSS, bots, redactores remotos) envíen noticias automáticamente:

```bash
# En .env
WEBHOOK_SECRET=un-token-secreto-largo

# Llamada desde el sistema externo
curl -X POST https://despacho.tudominio.com/api/webhooks/noticia \
  -H "X-Webhook-Secret: un-token-secreto-largo" \
  -H "Content-Type: application/json" \
  -d '{"hecho": "El intendente inauguró el nuevo hospital", "lugar": "San Rafael", "categoria": "sociedad"}'
```

La noticia llega en estado `borrador` y queda lista para que un editor la genere y apruebe.

---

## Seguridad

- Credenciales de canales cifradas con AES-128 (Fernet) usando `SECRET_KEY`
- Rate limiting en `/api/panel/auth/login`: máximo 5 intentos por minuto por IP
- Hook `pre-commit` escanea commits en busca de secretos hardcodeados
- Tokens JWT con refresh automático; sesiones revocables desde el panel
- Para rotar `SECRET_KEY` sin perder datos: `make rotate-key NEW_KEY=<nueva-clave>`

```bash
# Activar el hook de git (solo la primera vez)
git config core.hooksPath .githooks
```

---

## Health check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "scheduler": "running",
    "ai": "configured"
  }
}
```

---

## Tests

```bash
make test
# o directamente:
python -m unittest discover -s tests -v
```

Los tests cubren el flujo completo (crear → generar → aprobar → publicar) y los servicios externos con mocks (no requieren credenciales reales).

---

## Arquitectura del código

```
app/
├── models/       # SQLAlchemy + Pydantic schemas
├── controllers/  # toda la lógica de negocio
├── services/     # integraciones externas (solo I/O)
├── views/api/    # routers HTTP (thin — solo delegan a controllers)
└── utils/        # helpers: auth, encrypt, scheduler, permisos
```

**Regla:** la lógica de negocio vive **únicamente** en `controllers/`. Los routers no acceden a la DB ni llaman servicios directamente.

---

## Preguntas frecuentes

**¿Puedo usar Claude en lugar de Gemini?**
Sí. Cambiá `AI_PROVIDER=claude` y completá `CLAUDE_API_KEY` en `.env`.

**¿Qué pasa si cambio SECRET_KEY?**
Los `config_json` ya cifrados dejan de ser legibles. Usá `make rotate-key NEW_KEY=<nueva>` para re-encriptar todo antes de cambiarla.

**¿Instagram no publica en local?**
Necesita que `PUBLIC_BASE_URL` sea una URL pública accesible desde internet. Meta descarga la imagen desde esa URL. En desarrollo, usá un túnel como ngrok.

**¿WhatsApp publica solo?**
No. WhatsApp genera el copy listo para copiar/pegar. La publicación es manual desde la app.
