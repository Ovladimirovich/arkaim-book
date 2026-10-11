---
description: Запустить линтеры
agent: code
---
# Линтеры

Проверка качества кода:

## Backend (ruff)
```bash
cd runtime
ruff check .
ruff format --check .
```

## Frontend (eslint + tsc)
```bash
cd arkaim-web
npm run lint
npx tsc --noEmit
```

## Через Makefile
```bash
make lint          # все линтеры
make lint-backend  # только backend
make lint-frontend # только frontend
make format        # авто-форматирование
```
