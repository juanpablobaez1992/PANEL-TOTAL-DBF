# CLAUDE.md — Despacho (Panel Total DBF)

## Project Overview

**Despacho** is a news publishing platform for *De Buena Fe Digital* that distributes content to multiple channels (WordPress, Facebook, Instagram, Twitter/X, Telegram, WhatsApp) with AI-assisted content generation and automation capabilities.

- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2, Python 3.11
- **Frontend:** React 19 + React Router 7 + Vite 8, Node 22
- **Database:** SQLite (default), configurable via `DATABASE_URL`
- **Deployment:** Docker Compose (backend + nginx-fronted frontend) on VPS

---

## Development Setup

### Backend

```bash
# Create virtual environment & install deps
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env       # Fill in required vars

# Run dev server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # Starts on :5173, proxies /api and /uploads to :8000
```

### Docker (Production)

```bash
docker compose up --build -d
# Backend on :8000 (internal), Frontend/Nginx on :8080
```

### Tests

```bash
python -m unittest discover -s tests -v
```

### Linting

```bash
cd frontend && npm run lint   # ESLint
```

---

## Repository Structure

```
PANEL-TOTAL-DBF/
├── main.py                    # ASGI entry point → imports app from app/main.py
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── Dockerfile                 # Backend container (Python 3.11 slim)
├── docker-compose.yml         # Orchestrates backend + frontend containers
├── .githooks/pre-commit       # Runs check_secrets.py before every commit
│
├── app/                       # Backend (strict MVC)
│   ├── main.py                # FastAPI factory, lifespan, router mounting
│   ├── config.py              # Settings via Pydantic BaseSettings + legacy fallback
│   ├── database.py            # SQLAlchemy engine & session factory
│   │
│   ├── models/                # SQLAlchemy ORM models + Pydantic schemas
│   │   ├── enums.py           # All enums (states, channel types, roles, categories)
│   │   ├── noticia.py         # News articles with state machine
│   │   ├── canal.py           # Publishing channels (config_json is encrypted)
│   │   ├── publicacion.py     # Per-channel publication records
│   │   ├── panel_user.py      # Admin panel users
│   │   ├── panel_session.py   # JWT session tokens
│   │   ├── automation_*.py    # Automation rules, accounts, logs, settings
│   │   └── schemas.py         # Pydantic v2 request/response schemas
│   │
│   ├── controllers/           # Business logic (no DB access from views)
│   │   ├── auth_controller.py
│   │   ├── noticia_controller.py     # News workflow (400 lines)
│   │   ├── publicacion_controller.py # Publication routing (276 lines)
│   │   ├── automation_controller.py  # Automation execution (481 lines)
│   │   ├── canal_controller.py
│   │   ├── dashboard_controller.py
│   │   ├── panel_user_controller.py
│   │   ├── panel_session_controller.py
│   │   └── system_controller.py
│   │
│   ├── services/              # External API integrations (pure I/O, no DB)
│   │   ├── ai_service.py      # Gemini / Claude content generation
│   │   ├── facebook_service.py
│   │   ├── twitter_service.py # OAuth 1.0a
│   │   ├── wordpress_service.py
│   │   ├── telegram_service.py
│   │   ├── whatsapp_service.py
│   │   ├── imagen_service.py  # Pillow image processing
│   │   ├── integraciones_service.py  # Credential verification
│   │   └── automation_*.py
│   │
│   ├── views/api/             # FastAPI route handlers (thin — delegate to controllers)
│   │   ├── panel_router.py    # Auth, dashboard, noticias, usuarios, sesiones
│   │   ├── noticias_router.py
│   │   ├── canales_router.py
│   │   ├── publicaciones_router.py
│   │   ├── automation_router.py
│   │   └── system_router.py
│   │
│   └── utils/                 # Shared helpers
│       ├── auth.py            # JWT creation/validation
│       ├── credentials.py     # Fernet encrypt/decrypt for channel configs
│       ├── passwords.py       # Bcrypt hashing
│       ├── permissions.py     # Role-based access control decorators
│       ├── scheduler.py       # Async background loop for scheduled publishing
│       ├── file_storage.py    # File upload handling
│       ├── oauth1.py          # OAuth 1.0a signing (Twitter)
│       ├── db_schema.py       # DB schema migrations
│       ├── http_result.py     # HTTP response helpers
│       └── json_tools.py
│
├── frontend/                  # React SPA
│   ├── Dockerfile             # Multi-stage: Node build → Nginx runtime
│   ├── nginx.conf             # SPA routing + /api and /uploads proxying
│   ├── vite.config.js         # Dev proxy: /api → :8000, /uploads → :8000
│   ├── eslint.config.js
│   └── src/
│       ├── main.jsx           # React DOM entry
│       ├── App.jsx            # Route definitions
│       ├── api.js             # Unified API client with auto token refresh (251 lines)
│       ├── context/AuthContext.jsx  # Auth state & token management
│       ├── pages/             # Page-level components
│       │   ├── LoginPage.jsx
│       │   ├── DashboardPage.jsx
│       │   ├── NewsPage.jsx          # News list + detail editor
│       │   ├── AutomationPage.jsx    # Automation UI (565 lines)
│       │   ├── CanalesPage.jsx
│       │   ├── UsersPage.jsx
│       │   └── SessionsPage.jsx
│       ├── components/        # Reusable UI components
│       │   ├── AppShell.jsx   # Layout with sidebar
│       │   ├── NewsDetail.jsx
│       │   ├── NewsList.jsx
│       │   ├── ProtectedRoute.jsx  # Route guard (requireAdmin support)
│       │   └── ...
│       └── hooks/usePolling.js
│
├── tests/
│   ├── test_app.py            # Smoke tests: endpoints + full news workflow
│   ├── test_credentials.py    # Encrypt/decrypt tests
│   └── test_services.py
│
├── scripts/
│   ├── check_secrets.py       # Pre-commit secret scanner (126 lines)
│   ├── check_integrations.py  # Validates API credentials
│   ├── deploy.ps1             # PowerShell VPS deployment via SSH
│   └── import_autopublicate_seed.py  # Legacy data migration
│
└── deploy/nginx/hostinger.conf   # VPS reverse proxy example
```

---

## Architecture Patterns

### Strict MVC (Backend)

The codebase enforces a hard layering rule:

- **Models** (`app/models/`): SQLAlchemy ORM + Pydantic schemas. No business logic.
- **Controllers** (`app/controllers/`): All business logic lives here. Orchestrate models and services.
- **Views** (`app/views/api/`): FastAPI route handlers only. Must be thin — receive request, call controller, return response. No business logic or direct DB access.
- **Services** (`app/services/`): External API integrations only. Pure I/O functions, no DB access.

**Do not** put business logic in route handlers. **Do not** call services directly from route handlers.

### News State Machine

News articles flow through these states in order:

```
borrador → generando → generado → aprobado → publicado
                                           ↘ error
```

State transitions are managed exclusively in `noticia_controller.py`. When a news article is approved, 6 `Publicacion` records are created (one per configured channel type).

### Channel Credential Encryption

`Canal.config_json` is always stored **encrypted** using Fernet (AES-128-CBC) with the `SECRET_KEY` env var. Use `utils/credentials.py` functions:

```python
from app.utils.credentials import encrypt_config, decrypt_config

# Store
canal.config_json = encrypt_config({"api_key": "..."})

# Read (via property)
config = canal.config  # auto-decrypts
```

**Never** store plaintext credentials in `config_json`. **Never** change `SECRET_KEY` in production without re-encrypting all channel configs.

### Token Authentication

- JWT tokens issued on login; refresh tokens for session renewal.
- Frontend stores both in `localStorage`.
- On any 401, `api.js` automatically retries with the refresh token before failing.
- Role system: `admin` has full access; `editor` cannot access channels, users, sessions, or automation.

---

## Key Conventions

### Python

- Use `async def` for all controller functions (called from async FastAPI handlers).
- SQLAlchemy sessions are provided via FastAPI dependency injection (`views/dependencies.py`).
- Use existing `http_result.py` helpers for consistent HTTP responses.
- All new models must be imported in `app/models/__init__.py` to be picked up by `db_schema.py`.
- Pydantic v2 syntax: use `model_config = ConfigDict(...)`, not `class Config:`.

### JavaScript / React

- No TypeScript — plain JSX throughout.
- All API calls go through `src/api.js` (`panelApi.*` methods). Never use `fetch`/`axios` directly in components.
- Auth state is managed exclusively via `AuthContext`. Access with `useContext(AuthContext)`.
- Admin-only routes: wrap with `<ProtectedRoute requireAdmin />` in `App.jsx`.
- Use `usePolling` hook for components that need auto-refresh.
- ESLint is configured — run `npm run lint` before committing frontend changes.

### Environment Variables

Required variables (see `.env.example` for full list):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Fernet key for channel config encryption |
| `DATABASE_URL` | SQLite path or PostgreSQL URL |
| `AI_PROVIDER` | `gemini` or `claude` |
| `GEMINI_API_KEY` / `CLAUDE_API_KEY` | AI content generation |
| `PANEL_ADMIN_USERNAME` | Default admin username (seeded on startup) |
| `PANEL_ADMIN_PASSWORD` | Default admin password |
| `PUBLIC_BASE_URL` | Public URL for image serving (required for Instagram) |

Channel-specific vars (WordPress, Meta, Twitter, Telegram) are stored encrypted in the DB and managed via the Channels UI.

---

## API Endpoints Reference

All endpoints are prefixed with `/api`.

### Auth (panel)
- `POST /api/panel/auth/login` — username/password → access + refresh tokens
- `POST /api/panel/auth/refresh` — refresh token → new access token
- `POST /api/panel/auth/logout` — revoke refresh token
- `GET /api/panel/me` — current user profile

### News
- `GET /api/panel/noticias` — paginated list (params: `page`, `page_size`, `q`, `estado`, `solo_programadas`)
- `POST /api/panel/noticias` — create news (borrador state)
- `GET /api/panel/noticias/{id}`
- `PUT /api/panel/noticias/{id}`
- `POST /api/panel/noticias/{id}/acciones/generar` — AI generation
- `POST /api/panel/noticias/{id}/acciones/aprobar`
- `POST /api/panel/noticias/{id}/acciones/preflight` — dry-run publish check
- `POST /api/panel/noticias/{id}/acciones/programar` — schedule with `programada_para`
- `POST /api/panel/noticias/{id}/acciones/publicar` — immediate publish

### Channels
- `GET /api/canales`
- `PUT /api/canales/{id}`
- `POST /api/canales/{id}/toggle-activo`
- `POST /api/canales/{id}/toggle-auto`
- `POST /api/canales/seed` — initialize default channels

### Publications
- `GET /api/publicaciones/{noticia_id}`
- `POST /api/publicaciones/{id}/reintentar`

### Automation
- `GET /api/automation/dashboard`
- `GET/POST/DELETE /api/automation/rules`
- `GET /api/automation/queue`
- `GET/POST /api/automation/settings`
- `POST /api/automation/trigger`
- `POST /api/automation/trigger-evergreen`

### System
- `GET /` and `GET /health` — health check
- `GET /api/system/info`
- `GET /api/system/integraciones`

---

## Git Hooks & Security

The pre-commit hook in `.githooks/pre-commit` runs `scripts/check_secrets.py` automatically. It scans staged files for hardcoded secrets matching patterns like API keys, passwords, tokens, and private keys.

To activate the hooks after cloning:

```bash
git config core.hooksPath .githooks
```

**Never commit `.env` files.** The `.gitignore` excludes `.env`, `*.db`, `uploads/`, and `AUTOPUBLICATE/`.

---

## Deployment

### Docker Compose (Recommended)

```bash
docker compose up --build -d
```

- Backend: exposes port 8000 internally
- Frontend Nginx: maps host `:8080` → container `:80`
- VPS Nginx reverse proxy (see `deploy/nginx/hostinger.conf`) forwards external traffic to `:8080`
- Persistent volumes: `despacho_uploads`, `despacho_data`

### VPS Deployment via PowerShell

```powershell
.\scripts\deploy.ps1 -Push            # Push code + deploy
.\scripts\deploy.ps1 -Logs            # Stream Docker logs
.\scripts\deploy.ps1 -RemotePath /custom/path
```

Default remote path: `/docker/panel-total-dbf`

---

## Background Scheduler

`app/utils/scheduler.py` runs an async loop every `SCHEDULER_INTERVAL_SECONDS` (default: 30s) that:
1. Calls `procesar_noticias_programadas()` to publish news whose `programada_para` time has passed.
2. Executes automation rules if `AUTO_PUBLISH_GLOBAL=true`.

The scheduler starts automatically in the FastAPI lifespan (`app/main.py`).

---

## Legacy Migration

The project migrated from a system called `AUTOPUBLICATE`. The config loader (`app/config.py`) falls back to reading `AUTOPUBLICATE/.env` if a setting is missing from the primary `.env`. The `AUTOPUBLICATE/` directory is gitignored and should not be committed.

To import legacy data:

```bash
python scripts/import_autopublicate_seed.py
```

---

## Testing Guidance

- Tests use FastAPI's `TestClient` with an in-memory SQLite DB.
- The main smoke test (`tests/test_app.py`) covers: health check, channel seeding, full news workflow (create → generate → approve → publish).
- Run `python scripts/check_integrations.py` to verify external API credentials before testing real publishing.
- Do not mock external services in smoke tests — use test credentials or skip integration-dependent assertions.
