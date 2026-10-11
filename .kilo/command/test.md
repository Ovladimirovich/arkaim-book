---
description: Запустить все тесты
agent: code
---
# Тесты

Запуск всех тестов проекта:

## Backend (pytest)
```bash
cd runtime
python -m pytest tests/ -v
```

## Frontend (vitest)
```bash
cd arkaim-web
npx vitest run
```

## Через Makefile
```bash
make test          # все тесты
make test-backend  # только backend
make test-frontend # только frontend
```
