.PHONY: help dev dev-back dev-front install install-back install-front \
        test test-back lint lint-front build up down logs restart \
        check-integrations check-secrets rotate-key

# ── Defaults ─────────────────────────────────────────────────────────────────
PYTHON   ?= python
VENV     ?= venv
PIP      ?= $(VENV)/bin/pip
PYTEST   ?= $(VENV)/bin/python -m unittest
PORT     ?= 8000

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────
install: install-back install-front  ## Instala todas las dependencias

install-back:  ## Instala dependencias Python en venv
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-front:  ## Instala dependencias npm del frontend
	cd frontend && npm install

# ── Desarrollo ────────────────────────────────────────────────────────────────
dev: dev-back dev-front  ## Inicia backend y frontend en paralelo (requiere GNU Make 4+)

dev-back:  ## Inicia el servidor FastAPI con recarga automática
	$(VENV)/bin/uvicorn main:app --reload --port $(PORT)

dev-front:  ## Inicia el servidor Vite del frontend
	cd frontend && npm run dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test: test-back  ## Corre todos los tests

test-back:  ## Corre los tests de Python
	$(VENV)/bin/python -m unittest discover -s tests -v

# ── Linting ───────────────────────────────────────────────────────────────────
lint: lint-front  ## Corre todos los linters

lint-front:  ## Corre ESLint en el frontend
	cd frontend && npm run lint

# ── Docker ────────────────────────────────────────────────────────────────────
build:  ## Construye los contenedores Docker
	docker compose build

up:  ## Levanta los contenedores en background
	docker compose up -d

down:  ## Detiene y elimina los contenedores
	docker compose down

logs:  ## Muestra logs en tiempo real de todos los contenedores
	docker compose logs -f

restart:  ## Reinicia todos los contenedores
	docker compose restart

# ── Utilidades ────────────────────────────────────────────────────────────────
check-integrations:  ## Verifica credenciales de integraciones externas
	$(VENV)/bin/python scripts/check_integrations.py

check-secrets:  ## Escanea archivos staged en busca de secretos hardcodeados
	$(VENV)/bin/python scripts/check_secrets.py

rotate-key:  ## Rota SECRET_KEY (requiere NEW_KEY=<valor>)
	@test -n "$(NEW_KEY)" || (echo "Uso: make rotate-key NEW_KEY=<nueva-clave>" && exit 1)
	$(VENV)/bin/python scripts/rotate_secret_key.py --new-key "$(NEW_KEY)"

rotate-key-dry:  ## Dry-run de rotación de SECRET_KEY (requiere NEW_KEY=<valor>)
	@test -n "$(NEW_KEY)" || (echo "Uso: make rotate-key-dry NEW_KEY=<nueva-clave>" && exit 1)
	$(VENV)/bin/python scripts/rotate_secret_key.py --new-key "$(NEW_KEY)" --dry-run
