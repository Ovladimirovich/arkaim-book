# Arkaim Digital Consciousness — СТАТУС ПРОЕКТА

**Дата:** 09.07.2026  
**Версия:** 1.0.0  
**Книга:** «Наследие Аркаима» (ОВладимирович), ~266 181 символ

---

## 1. АРХИТЕКТУРА (текущая)

```
                           ┌── Читатель (браузер)
                           │
                    Tailscale Funnel :443
                           │
                     Gateway :8080
                    ┌──────┴──────┐
                    │             │
              auth/ (RBAC)   Core Runtime :8642
                    │             │
              ┌─────┴─────┐ ┌─────┴──────────┐
              │Telegram    │ │  Pulse         │
              │  Google    │ │  Voice         │
              │  API keys  │ │  ReaderMemory  │
              └───────────┘ │  KnowledgeGraph │
                            │  ChromaDB(1037) │
                            │  Presence       │
                            │  Evolution      │
                            │  X-Ray          │
                            └────────────────┘
```

---

## 2. ЧТО СДЕЛАНО

### Архитектурное улучшение (Фазы 0-7, выполнено)
- **Сеть**: конфигурируемые host/port, стандартизация порта 8080
- **Туннель**: Tailscale Funnel, HTTPS, без проброса портов
- **OAuth**: Telegram Login + Google OIDC
- **RBAC**: reader / editor / admin на всех эндпоинтах
- **Web UI**: Jinja2 + HTMX (книга, профиль, загрузка, админка)
- **WebSocket**: real-time уведомления дашборда
- **NSSM**: службы ArkaimCore, ArkaimGateway (автозапуск)
- **Документация**: гайды, архитектура, варианты доступа

### Аватар Книги (5 этапов, выполнено)
- **Pulse** — живое ядро: 4 активных слоя, ответы без LLM
- **Voice** — LLM как микрофон, не личность
- **Memory** — книга помнит каждого читателя
- **Presence** — наблюдение + предложения автору
- **Evolution** — версионирование генома, иммутабельные слои

### BOOK OS (инфраструктура данных)
- **Source Store** — неизменяемое хранилище документов (SHA-256)
- **Knowledge Graph** — EntityStore, FactStore, RelationshipStore + GraphEngine
- **Provenance Tracker** — трассировка фактов до строки книги
- **Index Engine** — ChromaDB (1037 чанков: 258 книга + 779 enriched)
- **Ingestion Pipeline** — полный цикл: загрузка → чанкинг → извлечение → индексация
- **Provider** — единый интерфейс для всех хранилищ

### Инфраструктура Runtime
- FastAPI Gateway + Core (асинхронный, connection pooling)
- Circuit breaker, rate limiting, retry с exponential backoff
- X-Ray observability (трейсы, спаны, SSE-стриминг)
- Skills framework + Telegram/VK адаптеры
- 349 тестов (3 предварительных — провайдеры)

---

## 3. ТЕСТЫ

| Категория | Файлы | Количество |
|-----------|-------|-----------:|
| Auth | `test_auth.py` | 34 |
| Memory | `test_memory.py` | 15 |
| Contract | `test_contract.py` | 19 |
| Identity | `test_identity.py` | 14 |
| Core isolation | `test_core.py`, `test_isolation.py` | ~60 |
| Gateway | `test_gateway_runtime.py` | 20 |
| Provider chain | `test_provider_reliability.py` | 26 |
| Book UI | `test_book_ui_integration.py` | 50+ |
| **Итого** | | **349** ✅ |

3 предварительных падения — тесты провайдеров, требующие настроенного GigaChat.

---

## 4. СТАТИСТИКА

| Метрика | Значение |
|---------|----------|
| Python-файлов | ~100+ |
| Тестовых функций | 349 |
| Пользователей в БД | динамически |
| Чанков в ChromaDB | 1037 |
| Персонажей в геноме | 27 |
| Тем в геноме | 138 |
| RAG-текстов в геноме | 100 |
| Подписчиков Email | динамически |

---

## 5. ИНФРАСТРУКТУРА

| Компонент | Статус |
|-----------|--------|
| Gateway :8080 | ✅ NSSM-служба, автозапуск |
| Core :8642 | ✅ NSSM-служба, автозапуск |
| Tailscale Funnel | ✅ Служба Automatic, персистентный конфиг |
| health_monitor | ✅ Фоновая проверка, Telegram-алёрты |
| Логи | `runtime/logs/` |
| Бэкап | Документация (`DEPLOYMENT.md`) |

---

## 6. ЧТО ПЛАНИРУЕТСЯ

### Короткая перспектива
- WebSocket уведомления в дашборде
- Автоматическое извлечение сущностей из PDF (пайплайн)
- Индексация enriched_chunks (1037 → 2000+)
- Отдельная страница `/book/ask` в дашборде

### Средняя перспектива (Эпоха 3)
- Telegram Presence — книга слышит чат
- Email-рассылка с шаблонами из Pulse
- Краудфандинг-интеграция
- Мобильная вёрстка

### Долгая перспектива (Эпоха 4)
- Мульти-книга (платформа)
- Мобильное приложение
- API для издателей
- Рекомендательная система
