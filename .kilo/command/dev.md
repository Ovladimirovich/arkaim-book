---
description: Запустить dev-среду (backend + frontend)
agent: code
---
# Dev режим

Запуск локальной dev-среды для проекта «Наследие Аркаима»:

## Backend (FastAPI :8642)
```bash
cd runtime
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn core.main:app --port 8642 --reload
```

## Frontend (Next.js :3000)
```bash
cd arkaim-web
npm install
npm run dev
```

## Альтернатива: Docker
```bash
docker compose up --build
```
- Frontend: http://localhost:3000
- Backend:  http://localhost:8642
- Swagger:  http://localhost:8642/docs

Перед запуском убедитесь, что `.env` создан из `.env.example` и заполнен (особенно `SESSION_SECRET` и `ALLOWED_ORIGINS`).
