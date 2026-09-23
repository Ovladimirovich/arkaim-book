# Changelog

## [2.0.0] — 2026-07-20

### Major
- **World Engine** — вычислимая модель мира книги
  - 547 сущностей мира в 13 категориях
  - 287 связей между сущностями (8 типов)
  - 55 форм для визуализации (11 категорий)
  - 5 правил консистентности мира
  - 10 режимов работы
  - 10 API эндпоинтов на `/book/world/`
- **34 страницы** интерфейса (полностью реализованы)
- **Knowledge Expansion Pipeline** — 11 модулей обогащения, 168 тем
- **ReaderProfile + Adaptive Responses** — 4 уровня, стили обучения, адаптация

### Added
- Interactive Map + Timeline (страница `/map`)
- Community страницы (Interpretations, Artifacts)
- Streaming чат (`/ask`)
- Краудфандинг интеграция
- World Engine CLI (`world_cli.py`)
- Batch processing (`world_batch.py`)

### Changed
- Pulse расширен с 4 до 10 слоёв
- API эндпоинты: 195 → 219
- База знаний: 40+ JSON-файлов

### Fixed
- ServiceRegistry — единый DI-контейнер
- WebSocket LiveFeedPanel (7 типов событий)
- RAG dense mode — 2123 чанка

---

## [1.0.0] — 2026-07-09

### Major
- **BookPulse** — живое ядро (4 слоя: Knowledge, Meaning, Identity, Mission)
- **BookVoice** — LLM как микрофон, не личность
- **ReaderMemory** — книга помнит читателей (SQLite)
- **Presence** — наблюдение + предложения автору
- **EvolutionTracker** — версионирование генома

### Added
- 34 теста Auth (Telegram, Google, API Keys, JWT, RBAC)
- 15 тестов Memory
- 19 тестов Contract
- 14 тестов Identity
- ~60 тестов Core isolation
- 20 тестов Gateway
- 26 тестов Provider reliability
- 50+ тестов Book UI
- **349 тестов** общее покрытие
- NSSM-службы (ArkaimCore, ArkaimGateway)
- WebSocket real-time уведомления
- Jinja2 + HTMX Web UI (5 страниц)
 - GigaChat, OpenRouter провайдеры

### Infrastructure
- Gateway :8080 + Core :8642 (NSSM, автозапуск)
- Cloudflare Tunnel / Tailscale Funnel (HTTPS)
- health_monitor (Telegram-алёрты)

---

## [0.1.0] — 2026-06

### Initial
- Первый прототип: FastAPI + Next.js
- RAG на ChromaDB (1037 чанков)
- Book Intelligence — базовые слои Pulse
- Docker Compose для разработки
- CLI инструменты

