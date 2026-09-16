# FORENSIC AUDIT: Universal AI Gateway — Current State (Post D-10)

**Дата:** 2026-09-16  
**Режим:** READ-ONLY  
**Контекст:** После закрытия D-10 (PROVIDER_CHAIN, PROVIDER_FAILURE_THRESHOLD, PROVIDER_COOLDOWN_SECONDS добавлены в shared_config.py)

---

## Простыми словами

**Цель аудита:** Определить, что Gateway уже умеет, что ещё нужно, и какой milestone реально следующий — без догадок, по фактическому состоянию кода.

**Результат:** Gateway — это не универсальный шлюз для произвольных LLM-провайдеров, а **специализированный HTTP-адаптер GigaChat + OpenRouter** с fallback-цепочкой. Архитектурно готов к новым провайдерам (абстракция BaseProvider), но фактически зафиксирован на двух. Production-путь работает только с GigaChat (OpenRouter блокируется 403). Следующий необходимый milestone — **model discovery / capability map**, чтобы Gateway знал какие модели доступны и мог выбирать оптимальную.

---

## 1. Capability Table

| Capability | Реализовано | Проверено кодом | Runtime | Документ |
|-----------|:-----------:|:---------------:|:-------:|----------|
| Provider abstraction (BaseProvider) | ✅ | base.py:1–12 | ✅ | shared_config.py |
| ProviderRegistry с circuit breaker | ✅ | provider_registry.py | ✅ | D-10 фикс |
| PROVIDER_CHAIN | ✅ | shared_config.py:82 | ✅ | D-10 фикс |
| Fallback chain (orchestrator) | ✅ | orchestrator.py:127–191 | ✅ (GigaChat) | — |
| Health/probe для провайдеров | ✅ | provider_registry.py:161–172 | ✅ (stub) | — |
| Retry с классификацией ошибок | ✅ | retry.py:1–90 | ✅ | — |
| A/B тестирование провайдеров | ✅ | ab_testing.py | ✅ (stub) | — |
| X-Ray observability | ✅ | aethon.xray imports | ✅ | — |
| IdentityLayer validation | ✅ | identity/sanitizer.py | ✅ | — |
| GigaChat adapter | ✅ | gigachat.py:1–125 | ✅ (live) | CHANGELOG 2.0.0 |
| OpenRouter adapter | ✅ | openrouter.py:1–74 | ⚠️ (403) | D-10 фикс |
| Model discovery | ❌ | НЕ НАЙДЕНО | — | — |
| Local llama.cpp | ❌ | НЕ НАЙДЕНО | — | — |
| OpenAI-compatible /v1/chat/completions | ❌ | book.py — кастомный DTO | — | — |
| API key management (runtime) | ⚠️ | dto: ApiKeyResponse есть, но нет route | — | — |
| Rate limiting (per-provider) | ❌ | RATE_LIMIT_REQUESTS_PER_MINUTE есть в конфиге | — | — |
| Provider auto-discovery | ⚠️ | register() — ручной | — | — |

---

## 2. Production Path Analysis

### Реальный request path (orchestrator.py):

```
Request (BookAskRequest)
  ↓
Route /book/ask (routes/book.py)
  ↓
Orchestrator.chat() (orchestrator.py:37)
  ↓
ProviderRegistry.select_provider() → ab_testing.py
  ↓
ProviderRegistry.chain_healthy(requested) → [name]
  ↓
for name in chain:
    ProviderRegistry.get(name) → GigaChatProvider()
    provider.chat(messages) → httpx.post(gigachat.devices.sberbank.ru)
    → response["choices"][0]["message"]["content"]
  ↓
identity_sanitize(response, provider=name)
  ↓
return BookAskResponse(answer=..., layers_used=..., provenance=...)
```

### Status:
- **GigaChat**: ✅ Работает (факт: запросы проходят, токен обновляется, SSL verify)
- **OpenRouter**: ⚠️ Код существует, но возвращает 403 (внешний блокер, не Gateway)
- **Fallback**: ✅ Работает (если первый provider падает, пробует следующий)
- **Circuit breaker**: ✅ Работает (PROVIDER_FAILURE_THRESHOLD=3, PROVIDER_COOLDOWN_SECONDS=60)

---

## 3. CRITICAL GAPs

### GAP-1: Отсутствует Model Discovery

```text
GAP:
Gateway не знает какие модели доступны у каждого провайдера.
Нет эндпоинта GET /providers/{name}/models или类似.
Нет capability map (чат vs генерация vs embedding).

CURRENT:
Провайдер hardcodes model: "GigaChat-Pro" (gigachat.py:72),
"qwen/qwen-2.5-7b-instruct" (openrouter.py:24).
Нет API для перечисления моделей.

EXPECTED:
GET /providers/gigachat/models → [{"id": "GigaChat-Pro", "context_window": 32000, "modalities": ["text"]}]
GET /providers → [{name, models[], health}]
POST /v1/models (OpenAI-compatible)

EVIDENCE:
- gigachat.py:72 hardcoded "GigaChat-Pro"
- openrouter.py:24 hardcoded model из settings
- shared_config.py: OPENROUTER_MODEL
- Нет файлов: **/models.py, model_discovery.py

IMPACT:
Клиент не может узнать доступные модели.
Невозможно делать smart routing по характеристикам модели.
OpenAI-compatible интерфейс невозможен без discovery.

DEPENDENCIES:
Низкая — требует добавить 1 эндпоинт + 1 метод в BaseProvider
```

### GAP-2: Нет OpenAI-compatible Endpoints

```text
GAP:
Gateway не предоставляет стандартный OpenAI API.
Все роуты кастомные (/book/ask, /book/generate).
Фронтенд использует кастомные DTO (ChatRequest, BookAskRequest).

CURRENT:
book.py имеет /ask и /generate — нестандартный формат.
Нет /v1/chat/completions, /v1/models, /v1/embeddings.

EXPECTED:
POST /v1/chat/completions → OpenAI format
GET /v1/models → list available models
Стандартный response: {"id":"chatcmpl-...","choices":[{"message":{"role":"assistant","content":"..."}}]}

EVIDENCE:
- routes/book.py: все эндпоинты кастомные
- core/dto/requests.py: ChatRequest, BookAskRequest — свои форматы
- Нет импортов openai или аналогов

IMPACT:
Низкая совместимость с экосистемой (LangChain, LlamaIndex, OpenAI SDK).
Фронтенд завязан на кастомный API.
Для Universal Gateway это fundamental gap.

DEPENDENCIES:
Средняя — требуется адаптер-транслятор между BookAskRequest и OpenAI format
```

### GAP-3: Rate Limiting Не Реализован для Провайдеров

```text
GAP:
RATE_LIMIT_REQUESTS_PER_MINUTE есть в конфиге,
но нет реализации rate limiter для провайдеров.

CURRENT:
shared_config.py:77 — RATE_LIMIT_REQUESTS_PER_MINUTE: 6000
Но в orchestrator.py нет проверки лимита перед вызовом провайдера.

EXPECTED:
Decorator или middleware, который считает запросы на провайдера
и бросает 429 при превышении.

EVIDENCE:
- shared_config.py:77 — поле есть
- orchestrator.py — нет вызова rate limiter
- Нет файлов: rate_limiter.py, throttling.py

IMPACT:
Средняя — при перегрузке провайдера Gateway не защитит его.
OpenRouter 403 может усугубиться без rate limiting.

DEPENDENCIES:
Низкая — sliding window counter + Redis/in-memory dict
```

### GAP-4: Нет Standalone Health Endpoint for Chain

```text
GAP:
ProviderRegistry.health() возвращает список,
но нет HTTP-эндпоинта /providers/health.

CURRENT:
orchestrator.py:308 — provider_health() существует,
но не экспортирован в routes.

EXPECTED:
GET /providers/health → [{"name": "gigachat", "status": "ok", "healthy": true}]
GET /health → включает health всех провайдеров

EVIDENCE:
- orchestrator.py:308 — метод есть
- Нет routes/providers.py с этим эндпоинтом

IMPACT:
Низкая — health check недоступен извне.
Monitoring не может проверить цепочку.

DEPENDENCIES:
Минимальная — добавить 1 route
```

---

## 4. Roadmap Validation

Из `docs/CURRENT_DEVELOPMENT_STATE.md`:

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| MD-5 integration | DEFERRED | Требует owner-GO |
| M4.2.3 video-провайдеры | PENDING | Требует owner-GO |
| C2 provenance | ✅ CLOSED | Исправлено в f1d5d60 |
| D-10 SharedSettings | ✅ CLOSED | Исправлено в 132ec9a |
| F3 frontend | ✅ CLOSED | 85/85 тестов |
| M10.2 temporal API | ✅ CLOSED | 16/16 тестов |
| Media Contract v1.0 | DRAFT | Ждёт owner-GO |
| Local llama.cpp | ❌ НЕ ПЛАНИРУЕТСЯ | Вне scope Gateway |

**Вывод:** Roadmap сфокусирована на media-контуре (MD-линейка), а не на Universal Gateway. Gateway — подсистема, не основная дорожка.

---

## 5. Next Recommended Milestone

```text
NEXT MILESTONE: G0 — Model Discovery & OpenAI-Compatible Layer

ЧТО:
1. Добавить BaseProvider.list_models() → List[ModelInfo]
2. Добавить GET /providers/health → chain health status
3. Добавить POST /v1/chat/completions → транслятор BookAskRequest → OpenAI format
4. Добавить GET /v1/models → агрегация моделей из всех провайдеров
5. Добавить simple in-memory rate limiter per provider

ПОЧЕМУ ЭТО СЛЕДУЮЩИЙ:
- Закрывает GAP-1 (Model Discovery) — фундамент для smart routing
- Закрывает GAP-2 (OpenAI-compatible) — стандарт де-факто для AI gateways
- Закрывает GAP-3 (Rate Limiting) — защита провайдеров
- Закрывает GAP-4 (Health endpoint) — мониторинг
- НЕ требует новых провайдеров
- НЕ конфликтует с MD-линейкой (другой домен)
- Может быть реализован за 1–2 small PR

НЕ ТРОГАТЬ СЕЙЧАС:
- MD-линейка (media-project) — требует separate GO
- Новые провайдеры (HuggingFace, HF, Pollinations) — удалены по решению владельца
- OpenRouter fix — внешний 403, не проблема Gateway
- Local llama.cpp — вне scope Universal Gateway
```

---

## 6. Summary

```text
UNIVERSAL AI GATEWAY — CURRENT STATE

G0: ❌ Not started — Model Discovery отсутствует
G1: ❌ Not started — OpenAI-compatible interface отсутствует
G2: ⚠️ Partial — Provider chain работает, но без discovery
G3: ✅ Done — Core orchestrator + fallback + circuit breaker
G4: ✅ Done — GigaChat adapter (working)
D-10: ✅ Closed — SharedSettings fixed (PROVIDER_CHAIN, thresholds)

Production path: ✅ WORKING for GigaChat
  - Request → Orchestrator → GigaChatProvider → Response
  - Fallback к OpenRouter существует, но OpenRouter 403
  - Circuit breaker работает (threshold=3, cooldown=60s)
  - Retry logic работает (classify_error + exponential backoff)

Provider abstraction: ✅ ARCHITECTED
  - BaseProvider: chat(), stream(), health(), close()
  - ProviderRegistry: register(), get(), chain(), health()
  - A/B selector: chain/ab_test/latency_aware modes

Provider chain: ✅ CONFIGURED
  - PROVIDER_CHAIN=["gigachat", "openrouter"]
  - Healthy chain: [name for name in chain if is_healthy(name)]

Fallback: ✅ IMPLEMENTED
  - orchestrator.py:127–191 — try each provider in chain
  - record_failure / record_success → circuit breaker
  - last_error propagated to client on total failure

Circuit breaker: ✅ IMPLEMENTED
  - _CircuitBreakerState: failure_count, cooldown_until
  - Threshold=3, Cooldown=60s (shared_config.py:83–84)
  - Async-safe: areport_failure, areport_success

Model discovery: ❌ ABSENT
  - Нет методов list_models() в BaseProvider
  - Нет эндпоинтов /v1/models или /providers/{name}/models
  - Модели захардкожены в провайдерах

Local LLM: ❌ NOT IN SCOPE
  - Никаких упоминаний llama.cpp, local AI, Ollama
  - В requirement.txt только transformers (библиотека, не runtime)

External providers: ⚠️ TWO (GigaChat ✅, OpenRouter ⚠️403)
  - GigaChat: fully working
  - OpenRouter: code exists, credentials configured, but 403

Observability: ✅ IMPLEMENTED
  - aethon.xray: events, spans, metrics
  - provider_latency, provider_failures, fallback_count
  - Logging with trace_id propagation

Security: ⚠️ PARTIAL
  - Auth: JWT + RBAC (require_role)
  - API keys: DTO exists, но нет runtime management route
  - Credentials: env-based (GIGACHAT_CLIENT_ID/SECRET, OPENROUTER_API_KEY)
  - No mTLS, no provider-level auth rotation
```

---

## Stop. Аудит завершён. Жду GO владельца.
