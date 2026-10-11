# План Sprint 2 — доработка интеграций

**Дата:** 10.07.2026  
**Проект:** Наследие Аркаима (Arkaim Digital Consciousness)  
**Статус:** План (на основе анализа кодовой базы)

---

## 0. Текущее состояние (что УЖЕ есть)

| Фича | Статус | Детали |
|-------|--------|---------|
| PDF-загрузка | ⚠️ Частично | `upload.html` принимает только `.txt,.md,.json`; pipeline `POST /book/os/pipeline/ingest` есть |
| Email-рассылка | ⚠️ Частично | `SubscriberStore` + `EmailTemplates` (weekly_digest, topic_deep_dive) + API `/email/*` существуют, но НЕТ авто-генерации из Pulse и НЕТ отправки |
| Telegram Presence | ✅ Почти готово | `TelegramPresence.process_message()` УЖЕ парсит ключевые слова из генома и регистрирует хиты в Observer |
| Краудфандинг | ❌ Не начато | Нет ни модулей, ни API |

---

## 1. PDF-обработка (автоматическое извлечение)

### Проблема
`runtime/templates/upload.html` строка 15:
```html
<input type="file" ... accept=".txt,.md,.json">
```
Pipeline `book_os/api_routes.py::pipeline_ingest` (строка 111) сохраняет загруженный файл во временный файл с суффиксом `Path(file.filename).suffix` и передаёт в `IngestionOrchestrator.ingest(tmp_path, ...)`. Для PDF нужна пред-обработка: извлечение текста перед чанкингом.

### План реализации

**Шаг 1. Добавить PDF-экстрактор**
- Файл: `core/CORE/book_os/pipeline/pdf_extractor.py` (новый)
- Использовать `pdfplumber` (точное извлечение) с фоллбеком на `PyPDF2`
- Функция `extract_text(pdf_path: Path) -> str` с сохранением структуры (главы, страницы)
- Добавить в `requirements.txt` / `pyproject.toml`: `pdfplumber>=0.11.0`

**Шаг 2. Расширить IngestionOrchestrator**
- Файл: `core/CORE/book_os/pipeline/orchestrator.py`
- В `ingest()` добавить ветвление по расширению:
  ```python
  if tmp_path.suffix.lower() == ".pdf":
      text = pdf_extractor.extract_text(tmp_path)
      # сохранить как .txt и продолжить pipeline
  ```
- Обеспечить, чтобы метаданные чанка содержали `source_page` для Provenance

**Шаг 3. Обновить upload.html**
- Строка 15: `accept=".txt,.md,.json,.pdf"`
- Добавить индикатор типа файла (иконка PDF)
- Показывать прогресс для больших PDF

**Шаг 4. Тесты**
- `runtime/tests/test_pdf_ingest.py` — загрузка sample.pdf → проверка извлечения текста и чанкинга

**Оценка:** S (1-2 дня)

---

## 2. Email-рассылка (шаблоны из Pulse)

### Проблема
`core/CORE/presence/email.py::EmailTemplates` (строки 162-188) принимает `pulse_context: str` как готовую строку. Никто не вызывает `pulse.build_context()` для авто-заполнения. Нет механизма отправки (только создание черновиков + approve).

### План реализации

**Шаг 1. Авто-генерация контента из Pulse**
- Файл: `core/CORE/presence/email.py` — добавить метод:
  ```python
  async def build_from_pulse(self, pulse, topic=None, subscriber_name="") -> EmailDraft:
      ctx = pulse.build_context(topic=topic)  # или analyze_reader_trends()
      if topic:
          return EmailTemplates.topic_deep_dive(topic, ctx, subscriber_name)
      return EmailTemplates.weekly_digest(ctx, subscriber_name)
  ```
- Pulse должен иметь метод `build_context()` (проверить в `pulse/pulse.py`; если нет — добавить на основе слоёв)

**Шаг 2. Механизм отправки**
- Файл: `core/CORE/presence/email_sender.py` (новый)
- Поддержка SMTP (через `aiosmtpd` или `httpx` к API) + фоллбек на заглушку (логирование)
- Переменные окружения: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, или `SENDGRID_API_KEY`
- Функция `send_draft(draft: EmailDraft, to_email: str)`

**Шаг 3. Endpoint для отправки**
- Файл: `core/CORE/presence/email_api.py` — добавить:
  ```python
  @router.post("/drafts/{draft_id}/send", dependencies=[Depends(require_role("admin"))])
  async def send_draft(draft_id: int):
      # загрузить черновик, отправить всем active подписчикам
  ```
- Или массовая рассылка: `POST /email/broadcast/weekly`

**Шаг 4. Периодическая рассылка**
- В `runtime/core/main.py` lifespan добавить задачу (раз в неделю):
  ```python
  async def _weekly_email_loop():
      while True:
          await asyncio.sleep(7 * 24 * 3600)
          await send_weekly_digest()
  ```

**Шаг 5. Тесты**
- `runtime/tests/auth/test_email.py` — подписка, генерация, отправка (mock SMTP)

**Оценка:** M (3-4 дня)

---

## 3. Telegram Presence (парсинг сообщений)

### Проблема
`core/CORE/presence/telegram_presence.py::TelegramPresence.process_message()` (строка 71) УЖЕ реализует парсинг: строит regex из ключевых слов генома, ищет совпадения, регистрирует хиты в Observer и создаёт предложения. **Но** адаптер Telegram не вызывает `process_message` при входящих сообщениях.

### План реализации

**Шаг 1. Проверить Telegram-адаптер**
- Файл: `core/CORE/community/telegram.py` (или `runtime/cli/`)
- Найти обработчик `handle_message` / `on_message`
- Убедиться, что он вызывает `telegram_presence.process_message(text, chat_id, user_id)`

**Шаг 2. Подключить Presence в адаптер**
- В `runtime/core/bootstrap.py` или запуске Telegram-бота:
  ```python
  from core.presence_manager import init_telegram_presence
  tp = init_telegram_presence()
  # в обработчике сообщения:
  tp.process_message(message.text, chat_id, user_id)
  ```

**Шаг 3. Расширить парсинг (опционально)**
- Добавить извлечение sentiment (положительное/отрицательное)
- Добавить NER для нахождения новых сущностей (не из генома)
- Логировать в `ReaderMemory` для профиля читателя

**Шаг 4. Тесты**
- `runtime/tests/test_telegram_presence.py` — process_message находит ключевые слова из генома

**Оценка:** S (0.5-1 день, т.к. парсинг уже готов)

---

## 4. Краудфандинг-интеграция

### Проблема
Полностью отсутствует. Нужна интеграция с российскими платформами (Planeta.ru, Boomstarter) или международными (Kickstarter, Indiegogo).

### План реализации (исследование + MVP)

**Шаг 1. Исследование API**
- Planeta.ru: https://planeta.ru/api (если есть публичное)
- Boomstarter: нет официального API, нужен парсинг или партнёрский доступ
- Альтернатива: просто embedding виджета на сайт (iframe)

**Шаг 2. Модуль интеграции**
- Файл: `core/CORE/community/crowdfunding.py` (новый)
- Класс `CrowdfundingMonitor`:
  - `fetch_campaign_status(campaign_id) -> dict` (через API или парсинг)
  - `get_progress() -> float` (собрано / цель)
  - `get_backers_count() -> int`

**Шаг 3. API эндпоинты**
- Файл: `runtime/core/crowdfunding_routes.py` (новый)
  ```python
  @router.get("/crowdfunding/status", dependencies=[Depends(require_role("reader"))])
  async def cf_status():
      return await monitor.get_status()
  ```

**Шаг 4. UI отображение**
- Добавить карточку на `/_ui/about` или отдельную страницу `/_ui/crowdfunding`
- Прогресс-бар, количество бекеров, кнопка "Поддержать"

**Шаг 5. WebSocket-уведомления**
- При достижении майлстоунов — toast в дашборде

**Оценка:** M-L (зависит от доступности API; 1 неделя на MVP)

---

## Итоговый план спринтов

| Спринт | Фичи | Оценка |
|--------|------|---------|
| **Sprint 2a** | PDF-экстрактор + upload.html + тесты | 2 дня |
| **Sprint 2b** | Telegram Presence wiring (process_message уже готов) | 1 день |
| **Sprint 2c** | Email: авто-генерация из Pulse + отправка + периодика | 4 дня |
| **Sprint 2d** | Краудфандинг: исследование + MVP + UI | 1 неделя |

**Критический путь:**
1. PDF (независимо)
2. Telegram Presence (независимо, быстро)
3. Email (зависит от Pulse.build_context)
4. Crowdfunding (независимо, но требует внешних API)

---

## Риски

| Риск | Митигация |
|------|-----------|
| `pulse.build_context()` может не существовать | Проверить `pulse/pulse.py`; добавить метод на основе слоёв (KnowledgeLayer + MeaningLayer) |
| Нет публичного API краудфандинга | Использовать iframe-виджет или парсинг HTML |
| PDF-экстрактор тяжёлый | Кешировать, запускать асинхронно, не блокировать upload |
| SMTP-креды не настроены | Заглушка: логирование в `runtime/logs/email.log`, флаг `EMAIL_MODE=mock|smtp|sendgrid` |

---

## Следующие шаги
1. Подтвердить приоритет (PDF vs Email vs Telegram vs Crowdfunding)
2. Проверить наличие `pulse.build_context()`
3. Выбрать краудфандинг-платформу для интеграции
4. Перейти к реализации (ACT MODE)