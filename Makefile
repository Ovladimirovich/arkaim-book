# Makefile — универсальные dev-команды для «Наследия Аркаима»

PYTHON  := python3
PIP     := $(PYTHON) -m pip
UVICORN := $(PYTHON) -m uvicorn

# ── Dev ─────────────────────────────────────────────────────
.PHONY: dev dev-backend dev-frontend docker-up docker-down

dev:
	@echo "▶ Запуск backend на :8642 и frontend на :3000"
	@cd runtime && $(PYTHON) -m venv .venv && . .venv/bin/activate 2>/dev/null || .venv/Scripts/activate && $(PIP) install -r requirements.txt && $(UVICORN) core.main:app --host 0.0.0.0 --port 8642 --reload &
	@cd arkaim-web && npm install && npm run dev

dev-backend:
	cd runtime && $(UVICORN) core.main:app --port 8642 --reload

dev-frontend:
	cd arkaim-web && npm run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down

# ── Тесты ───────────────────────────────────────────────────
.PHONY: test test-backend test-frontend

test: test-backend test-frontend
	@echo "✓ Все тесты пройдены"

test-backend:
	cd runtime && $(PYTHON) -m pytest tests/ -v

test-frontend:
	cd arkaim-web && npx vitest run

# ── Линтеры ─────────────────────────────────────────────────
.PHONY: lint lint-backend lint-frontend format format-backend format-frontend

lint: lint-backend lint-frontend
	@echo "✓ Все линтеры пройдены"

lint-backend:
	cd runtime && ruff check .

lint-frontend:
	cd arkaim-web && npm run lint && npx tsc --noEmit

format: format-backend format-frontend

format-backend:
	cd runtime && ruff format .

format-frontend:
	cd arkaim-web && npx prettier --write .

# ── Очистка ─────────────────────────────────────────────────
.PHONY: clean clean-backend clean-frontend

clean: clean-backend clean-frontend
	@echo "✓ Очистка завершена"

clean-backend:
	cd runtime && rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-frontend:
	cd arkaim-web && rm -rf node_modules .next out

# ── CI ──────────────────────────────────────────────────────
.PHONY: ci
ci: lint test
