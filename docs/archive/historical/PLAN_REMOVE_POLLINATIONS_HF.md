# План: Удаление Pollinations.ai и HuggingFace, замена на ComfyUI

## Цель

Провести полную замену генераторов изображений Pollinations.ai и HuggingFace на единый провайдер **ComfyUI** во всём проекте «Наследие Аркаима». Удалить все упоминания и код, связанный с Pollinations.ai и HuggingFace как генераторами изображений. Убрать HuggingFace из цепочки LLM-провайдеров.

---

## ⚠️ КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ

**Интеграция с ComfyUI (локальный и Colab) уже полностью реализована и РАБОТАЕТ** в проекте и в интерфейсе. Включая:

- Провайдер изображений `comfyui.py` в `core/CORE/providers/image/`
- Конфигурацию `COMFYUI_URL` для локального (`http://127.0.0.1:8188`) и Colab (Cloudflare Tunnel) режимов
- API роуты в `runtime/core/routes/visual.py`
- Фронтенд страницы визуала (`/visual`, `/visual-view`, `/film-studio`)
- Скрипты генерации сцен

**ГЛАВНАЯ ЗАДАЧА — НЕ СЛОМАТЬ существующую ComfyUI интеграцию.**

Во время выполнения всех этапов:
- ❌ **НЕ удалять** `core/CORE/providers/image/comfyui.py` — это основной рабочий провайдер
- ❌ **НЕ менять** интерфейс/настройки ComfyUI в UI
- ❌ **НЕ трогать** `COMFYUI_URL` логику в `core/config.py` (уже есть)
- ❌ **НЕ менять** API роуты визуала (`runtime/core/routes/visual.py`)
- ✅ **ТОЛЬКО удалять** упоминания Pollinations.ai и HuggingFace
- ✅ **ТОЛЬКО заменять** код, который переключает с Pollinations/HF на другие провайдеры, на `comfyui`

Перед началом работы — сделать бэкап/коммит текущего состояния. После каждого этапа — проверять, что ComfyUI интеграция не сломалась.

---

## Этап 1. Проверка и инвентаризация всех упоминаний

### 1.1. Найти все упоминания "pollinations"
Искать по паттерну `(?i)pollinations` во всех файлах:
- Python (*.py)
- TypeScript (*.ts, *.tsx)
- JSON (*.json)
- Markdown (*.md)
- YAML (*.yaml, *.yml)
- TXT (*.txt)
- Dockerfile, docker-compose.yml
- .env / .env.template

### 1.2. Найти все упоминания "huggingface" / "hugging face" / "hf_"
Искать по паттерну `(?i)hugging|(?i)hf_` во всех файлах.

### 1.3. Найти все скрипты
- `scripts/generate_scenes_hf.py` — скрипт генерации сцен через HuggingFace
- `scripts/generate_scenes_pollinations.py` — скрипт генерации сцен через Pollinations.ai

### 1.4. Найти все провайдеры
- `runtime/core/providers/huggingface.py` — LLM провайдер HuggingFace
- `core/CORE/providers/image/huggingface.py` — (если существует) генератор изображений
- `core/CORE/providers/image/pollinations.py` — (если существует) генератор изображений
- `core/CORE/providers/image/comfyui.py` — основной провайдер (оставить)

---

## Этап 2. Конфигурация и переменные окружения

### 2.1. runtime/.env
Удалить:
```env
# ── HuggingFace ───────────────────────────────────────
HF_API_TOKEN=...
HF_MODEL=microsoft/Phi-3.5-mini-instruct
```

Изменить:
```env
PROVIDER_CHAIN=gigachat,openrouter,huggingface
```
на:
```env
PROVIDER_CHAIN=gigachat,openrouter
```

Пользователь работает с ComfyUI **локально** и **через Colab**. Конфигурация должна поддерживать оба режима.

**Обновить COMFYUI_URL** (поддерживать два варианта):
```env
# Локальный ComfyUI (основной)
COMFYUI_URL=http://127.0.0.1:8188

# Colab ComfyUI (Cloudflare Tunnel) — раскомментировать при работе через Colab
# COMFYUI_URL=https://apparently-sealed-thing-internet.trycloudflare.com
```

### 2.2. runtime/.env.template
Создать (или обновить) шаблон:
- Убрать HF_API_TOKEN, HF_MODEL
- Обновить PROVIDER_CHAIN на `gigachat,openrouter`
- Добавить два варианта COMFYUI_URL:
  - Локальный: `COMFYUI_URL=http://127.0.0.1:8188`
  - Colab (Cloudflare Tunnel): закомментированный пример
- Добавить комментарий-инструкцию, когда какой использовать

### 2.3. core/config.py
Удалить:
```python
HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
```

Изменить:
```python
PROVIDER_CHAIN = os.getenv("PROVIDER_CHAIN", "gigachat,openrouter,huggingface").split(",")
```
на:
```python
PROVIDER_CHAIN = os.getenv("PROVIDER_CHAIN", "gigachat,openrouter").split(",")
```

---

## Этап 3. Удаление/замена Python-модулей

### 3.1. runtime/core/providers/huggingface.py
- Удалить файл (если не используется).
- Если используется другими модулями — заменить на OpenRouter или GigaChat.
- Обновить runtime/core/providers/__init__.py — убрать импорт.

### 3.2. core/CORE/providers/image/
- Удалить `huggingface.py` и `pollinations.py` (если существуют).
- Сделать `comfyui.py` единственным активным провайдером.
- Обновить `__init__.py` — убрать импорты удалённых провайдеров.
- Привести enum/константы к единственному типу `"comfyui"`.

### 3.3. core/CORE/providers/video/
- Проверить на упоминания Pollinations/HuggingFace.
- Заменить на ComfyUI (при необходимости).

### 3.4. Архитектура фабрики провайдеров
- Найти фабрику/регистратор провайдеров изображений (например, в `core/CORE/visual/` или `core/CORE/providers/image/`).
- Убрать ветки для "pollinations" и "huggingface".
- Оставить ветку для "comfyui" с fallback на "mock"/"svg".

---

## Этап 4. Удаление/переработка скриптов

### 4.1. scripts/generate_scenes_hf.py
- **Вариант 1:** Удалить файл.
- **Вариант 2:** Переписать на ComfyUI API.
- Рекомендация: **удалить**, так как `generate_scenes.py` уже существует для базовой генерации, и будет создан новый единый скрипт через ComfyUI.

### 4.2. scripts/generate_scenes_pollinations.py
- **Вариант 1:** Удалить файл.
- **Вариант 2:** Переписать на ComfyUI API.
- Рекомендация: **удалить**.

### 4.3. Создать новый единый скрипт (опционально)
- Создать `scripts/generate_scenes_comfyui.py` — скрипт генерации сцен через ComfyUI, объединяющий функциональность удалённых скриптов.

### 4.4. Обновить scripts/__init__.py (если есть импорты)
- Убрать импорты удалённых скриптов.

---

## Этап 5. Документация

### 5.1. Обновить все .md файлы
Найти и заменить во всех документах:
- "Pollinations.ai" / "Pollinations" → "ComfyUI"
- "HuggingFace" в контексте генерации → "ComfyUI"
- "HuggingFace" в контексте LLM → удалить (оставить GigaChat, OpenRouter)

Файлы для проверки:
- `README.md`
- `docs/AI_ENGINEER_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/comfyui_guide.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_SUMMARY.md`
- `docs/PROJECT_STATE.md`
- `docs/WORLD_ENGINE.md`
- `docs/WORLD_EXPLORER.md`
- `docs/DEPLOY.md`
- `docs/KNOWLEDGE_BASE.md`
- `docs/KNOWLEDGE_EXPANSION.md`
- `docs/visualization_layer.md`
- `core/PROJECT_STATUS.md`
- `core/DEVELOPER_GUIDE.md`
- `core/README.md` (если есть)
- `AGENTS.md` (обновить список LLM-провайдеров)
- `arkaim-web/README.md`
- `arkaim-mobile/README.md`
- `CHANGELOG.md` (отметить change)

### 5.2. Обновить config.py комментарии
- Убрать упоминание HuggingFace из комментариев.

---

## Этап 6. Фронтенд

### 6.1. Найти упоминания в arkaim-web/src/
- Поиск `pollinations` и `huggingface` в .ts/.tsx файлах.
- Заменить настройки/типы/константы провайдеров на `comfyui`.

### 6.2. Найти упоминания в arkaim-mobile/src/
- Поиск `pollinations` и `huggingface`.
- Заменить на `comfyui`.

---

## Этап 7. Тесты

### 7.1. Найти тесты, использующие Pollinations/HuggingFace
- `runtime/tests/`
- `tests/`
- `arkaim-web/tests/`

### 7.2. Обновить тесты
- Заменить моки Pollinations/HuggingFace на моки ComfyUI.
- Обновить ожидания ответов (конфиг провайдеров).
- Убедиться, что все тесты проходят: `make test`

---

## Этап 8. Финальная проверка

### 8.1. Глобальный поиск
- Выполнить поиск `(?i)pollinations` — ожидается 0 результатов.
- Выполнить поиск `(?i)hugging` — ожидается 0 результатов (или только исторические записи в CHANGELOG, если решено сохранить).
- Выполнить поиск `(?i)hf_` — ожидается 0 результатов.

### 8.2. Запуск тестов и линтеров
- `make test` — все тесты проходят
- `make lint` — линтеры чистые

### 8.3. Верификация запуска
- Запустить backend: `cd runtime && uvicorn core.main:app --port 8642`
- Проверить, что:
  - FastAPI стартует без ошибок
  - Провайдер изображений = `comfyui`
  - Команда генерации изображения работает

### 8.4. Проверка обоих режимов ComfyUI
- **Локальный режим:** `COMFYUI_URL=http://127.0.0.1:8188` — запустить локальный ComfyUI и проверить генерацию.
- **Colab режим:** `COMFYUI_URL=https://...trycloudflare.com` — запустить ComfyUI в Colab, получить Cloudflare Tunnel URL, подставить в .env и проверить генерацию.
- Убедиться, что переключение между режимами происходит только через переменную `COMFYUI_URL` без изменения кода.

---

## Порядок исполнения

| Шаг | Задача | Приоритет |
|-----|--------|-----------|
| 1 | Найти все упоминания | Высокий |
| 2 | Обновить .env и .env.template | Высокий |
| 3 | Обновить core/config.py | Высокий |
| 4 | Удалить/переписать провайдеры | Высокий |
| 5 | Удалить скрипты | Средний |
| 6 | Обновить документацию | Средний |
| 7 | Обновить фронтенд | Средний |
| 8 | Обновить тесты | Средний |
| 9 | Финальная проверка | Высокий |

---

## Ожидаемый результат

После завершения плана:
1. Все упоминания Pollinations.ai удалены.
2. Все упоминания HuggingFace удалены (кроме возможных исторических записей в CHANGELOG).
3. Единственным генератором изображений является **ComfyUI**.
4. Цепочка LLM-провайдеров: **gigachat, openrouter** (без huggingface).
5. Все тесты проходят, линтеры чистые, приложение запускается.
