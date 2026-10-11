SCRIPTS — Arkaim Runtime
========================

Все скрипты запускаются из корня проекта.


ЗАПУСК СЕРВИСОВ
----------------

..\start_all.bat
  Главный лаунчер. Запускает все сервисы:
    1) Очищает порты 8642, 3000
    2) Core (Backend :8642) — FastAPI + Book API + Telegram Bot + WebSocket
    3) Frontend (Next.js :3000)
  Проверяет наличие runtime\.venv и arkaim-web\node_modules.
  Показывает статус запуска и ссылки.

start_core.bat
  Запускает только Core (Backend :8642).
  uvicorn core.main:app --host 127.0.0.1 --port 8642
  Включает: Book API, Telegram Bot, WebSocket, X-Ray.

start_frontend.bat
  Запускает только Frontend (Next.js :3000).
  npm run dev


ОСТАНОВКА
----------

stop_all.bat
  Останавливает все сервисы:
    1) По заголовку окна (Arkaim Core, Arkaim Frontend)
    2) Принудительно освобождает порты 8642, 3000

stop-arkaim-services.bat
  Останавливает Windows-сервисы ArkaimCore, ArkaimGateway (требует админ-прав).


ПРОВЕРКА
---------

health_check.py
  Проверяет доступность сервисов.
  Запуск: python scripts/health_check.py


АРХИТЕКТУРА
------------

  Порт 8642 — Core (оркестратор + Book Intelligence + Telegram + UI)
  Порт 3000 — Frontend (Next.js)

  Gateway (:8080) и отдельный Book API (:9090) упразднены.
  Telegram Bot встроен в Core (lifespan → init_bot → poll).


БРАУЗЕРНЫЕ ССЫЛКИ (после запуска)
----------------------------------

  http://127.0.0.1:8642/_ui/book   — Web UI (Jinja2 + HTMX)
  http://127.0.0.1:8642/docs       — API Docs (Swagger)
  http://127.0.0.1:8642/book       — Book API endpoints
  http://127.0.0.1:8642/health     — Core health
  http://localhost:3000            — Frontend (Next.js)