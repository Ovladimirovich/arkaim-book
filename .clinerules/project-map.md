# ARKAIM — карта проекта и канонические команды

> Поведенческие правила — в `arkaim-engineer-mode.md`. Здесь только факты,
> чтобы их не переоткрывать каждую сессию.

## Монорепо (корень `C:\proect_arkaim\arkaim`)

| Путь | Стек | Роль |
|---|---|---|
| `runtime/` | Python | backend; точка входа `core.main:app`; venv — `runtime\.venv` |
| `arkaim-web/` | Node + Vite | frontend, порт 3000 |
| `arkaim-mobile/` | Node | мобильный клиент |
| `core/` | — | корневой слой (не путать с `runtime/core/`) |
| `docs/` | — | `ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` — план разработки |
| `ADR/`, `SCHEMAS/` | — | архитектурные решения и схемы |

`runtime/core/` — backend-модули: `routes`, `repositories`, `providers`,
`dto`, `identity`, `memory`, `data`.
Прочие backend-модули в `runtime/`: `narrative_engine`, `knowledge_base`,
`world_engine_backups`, `skills`, `auth`, `bot`, `cli`, `observability`,
`contracts`, `prompts`, `templates`, `xray_dashboard`.

## Команды — только через Makefile в корне

```bash
make test           # backend pytest + frontend vitest
make test-backend   # cd runtime && python -m pytest tests/ -v
make test-frontend  # cd arkaim-web && npx vitest run
make lint           # ruff + npm lint + tsc --noEmit
make ci             # lint + test
make dev-backend    # uvicorn core.main:app --port 8642 --reload
make dev-frontend   # cd arkaim-web && npm run dev
```

Порты: backend **8642**, frontend **3000**.

## Окружение

Backend: `runtime\.venv` (активировать перед python/pytest из `runtime/`).
Python-зависимости — через `pyproject.toml` в `runtime/`.
Node — `package.json` в `arkaim-web/` и `arkaim-mobile/`.
Конфигов в корне нет (`pyproject.toml`/`requirements.txt`/`pytest.ini` только в подпроектах).

## Запреты

- Не создавать параллельных механизмов запуска — команды живут в `Makefile`.
- Не читать `node_modules/`, `.venv/`, `arkaim_v1/`, `world_engine_backups/`.
- `arkaim_v1/` — старый срез, не источник истины.
- `.kilo/`, `.mimocode/` — кэши других ИИ-инструментов, не трогать.
