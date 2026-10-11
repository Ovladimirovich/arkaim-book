# MD-4 M4.1 — Boundary + Repository Bootstrap — IMPLEMENTATION REPORT

**Дата:** 2026-09-13
**Статус:** IMPLEMENTED + TESTED (ждёт owner-GO)
**Мандат:** owner-GO «MD-4 вариант A», milestone M4.1: boundary + repository bootstrap; **код провайдеров НЕ переносится** до утверждения границы.
**Repo:** `c:\proect_arkaim\arkaim-media` (отдельный git-репозиторий; root-commit `8e465cc`)

---

## Простыми словами

**Цель:** создать новый отдельный проект `arkaim-media` и зафиксировать «договор» — как Аркаим будет с ним разговаривать. Сам код генерации ещё НЕ переносится.

**Сделано:**
1. Создан новый пустой репозиторий `arkaim-media` (рядом с Аркаимом).
2. Написан **договор** (Media Contract): Аркаим отправляет план + маленький конверт доставки (5 полей: тип, размер, выбор бэкенда, длительность, fps), получает назад готовые байты + постоянный номер результата (`media_id`). Всё.
3. Написаны 4 технические «формы» договора (JSON-схемы), которые физически не позволяют протащить запретное: качество (мёртв — ваше решение), ComfyUI-детали (workflow/модели/steps/seed), старое имя «provider».
4. Примеры заполнения договора собраны из **реальной** работы текущего кода Аркаима (не выдуманные).
5. Написано 15 автоматических проверок: договор валиден, запретные поля отбиваются. **15/15 зелёные.**
6. Первая фиксация в git нового репозитория.

**Результат:** PASS.

**Проблемы:** нет. Одна особенность: Аркаим и его схемы «плана» связаны обещанием байт-в-байт совпадения — это проверяется автоматически при каждом запуске тестов.

**Дальше (предложение, не автоматически):** ваш GO на этот договор → M4.2 (перенос провайдеров в новый репозиторий).

---

## 1. Что создано (полный состав, 13 файлов)

```
arkaim-media/  (git root-commit 8e465cc, master)
├── docs/MEDIA_CONTRACT.md                     ← договор (главный артефакт)
├── schemas/
│   ├── media_plan.schema.json                 ← байт-в-байт копия arkaim-схемы (SHA256 сверен)
│   ├── media_generate_request.schema.json     ← запрос POST /v1/generate
│   ├── media_result.schema.json               ← ответ успеха
│   └── media_error.schema.json                ← тело ошибок
├── examples/
│   ├── request_image.json                     ← реальная сериализация MediaPlan (dump из builder)
│   ├── result_image.json
│   └── error_timeout.json
├── tests/
│   ├── test_media_contract.py                 ← 15 контрактных тестов
│   └── _mini_draft7.py                         ← мини-валидатор draft-07 (как в MD-3.3)
├── README.md / pyproject.toml / .gitignore
```

## 2. Ключевые решения границы (по owner-решениям §16)

| Owner-решение | Как реализовано |
|---|---|
| Вариант A | Контракт = сериализация живого ExecutionDispatch-конверта; пайплайн/роуты не тронуты |
| Quality мёртв (16-2) | `quality` отсутствует в схеме запроса и физически отвергается (`additionalProperties: false`; тест `test_execution_quality_rejected`) |
| Film Studio в Arkaim (16-3) | В контракте отсутствует; ownership-таблица §6: Film Studio целиком Arkaim |
| Репо `arkaim-media` (16-4) | Создан: `c:\proect_arkaim\arkaim-media`, git init, identity Ovladimirovich |
| `media_id` наружу (16-5) | Поле ответа + pattern `^media_[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$` + тест формата |
| shot_assembler НЕ чинить (16-6) | Зафиксирован как D-2 migration debt (контракт §9); не чинился |
| **ExecutionDispatch ≠ постоянный API** (уточнение) | Контракт §0 явно: «ExecutionDispatch НЕ является межпроектным API; существует только внутри Media как внутренний мост; REMOVE IN MD-5». Целевая цепочка записана ровно как в мандате: Arkaim → стабильный Media Contract → Media Project → временный ExecutionDispatch bridge → Provider → Backend → Asset |

## 3. Граница: что знает каждая сторона

**Arkaim знает (и только это):** контракт; свой MediaPlan; execution-конверт из 5 полей (`media_kind, size, preferred_backend, duration_sec, fps`); `media_id`; формат ответа; 7 кодов ошибок; HTTP-адрес Media.

**Arkaim НЕ знает (запрещено схемами физически):** ComfyUI; workflow; node graph; checkpoint/model; sampler; steps; CFG; seed; provider-specific параметры; внутреннюю структуру Media. Проверено негативными тестами (10 полей-кандидатов отбиваются).

**Media Project НЕ знает (правило репо, README + контракт §0):** WorldModel/Genome/SceneEngine — не импортируются, не читаются, не дублируются.

**Media НЕ должен писать в хранилище Аркаима; Аркаим не читает файловую систему Media** (ownership §6: ассет — один владелец, Arkaim).

## 4. Request/Result/Error semantics (кратко; полное — в контракте)

- **Запрос:** `POST /v1/generate` `{plan: <MediaPlan v0.1.0>, execution: {media_kind, size, preferred_backend, duration_sec?, fps?}}`. Синхронный. `media_kind` дублем в конверте (рассинхрон с планом → 400).
- **Ответ:** `{media_id, kind, bytes_b64, content_format, backend, workflow_used?}` — байты отдаёт, ассетом не владеет.
- **Ошибки:** 400 INVALID_REQUEST / 422 UNSUPPORTED_MEDIA_KIND·UNSUPPORTED_SIZE·BACKEND_NOT_AVAILABLE / 429 OVERLOADED / 500 GENERATION_FAILED / 504 GENERATION_TIMEOUT; тело `{error:{code, message, retryable}}`; без стектрейсов наружу.
- **Таймауты Media (внутренние):** image ≤300 с (как текущий ComfyUIProvider._poll), video ≤600 с.

## 5. Тесты (15/15 зелёные; прогон в repo: `pytest tests -q`)

Позитивные (4): request/result/error примеры валидны; plan-часть примера валидна против аркаим-схемы.
Негативные (10): quality; steps/cfg/sampler/seed/model/checkpoint/workflow/node_graph/comfyui/loras/denoise (пакет); provider (нужно preferred_backend); negative (только в плане); BANNED-поля плана; media_kind обязателен; ComfyUI-leak в ответе (sampler/steps/seed/model/node_graph/prompt-эхо); media_id обязателен + формат; посторонний error-код.
Инвариант (1): **байт-идентичность** `media_plan.schema.json` ↔ `arkaim/SCHEMAS/MEDIA_PLAN.schema.json` (тест сравнивает файлы при каждом прогоне; раскладка сёстриних репо; SKIP, если аркаим не рядом).

## 6. Self-review (что мог пойти не так — и проверено)

| Риск | Проверка | Итог |
|---|---|---|
| Контракт «выдуман», а не снят с живого кода | Пример собран dump'ом реального `MediaPlanBuilder().build_image_plan(...).to_dict()`; execution-поля = ровно `ExecutionDispatch.from_plan` (dispatch.py:42–64) | Не выдуман |
| Схема плана разошлась с аркаимом | SHA256 обоих файлов: `B52B7E7A…50F635` — равны; постоянный тест | Байт-идентична |
| ExecutionDispatch узаконен как вечный API | Контракт §0 + D-1 debt: «только внутренний мост, REMOVE IN MD-5» | Отвергнуто явно |
| Arkaim-код изменён | git status Аркаима: только Этап-1 тест-фикс + 2 док-артефакта аудита (см. §8) | Не изменён |
| Незакоммиченная работа | arkaim-media: root-commit 8e465cc (13 файлов) | Зафиксировано |
| Секреты/env в новый репо | .gitignore (`*.env`, keys, pems); git show: 0 совпадений | Чисто |
| Репо видит домен книги | В коде репо нет ни одного import из arkaim-модулей | Чисто |

## 7. Мандат-чеклист M4.1

- [x] создать `arkaim-media` — создан (отдельный git-репо, 13 файлов, root-commit);
- [x] определить минимальный стабильный внешний контракт — MEDIA_CONTRACT.md v1.0 DRAFT + 4 схемы + 15 тестов;
- [x] определить ownership Asset/storage — контракт §6 (Arkaim — единственный владелец ассетов; Media — stateless; film-studio — Arkaim; workflows/checkpoint — Media);
- [x] определить request/result/error semantics — §3/§4/§5 (7 машинных кодов, retryable-семантика);
- [x] **не переносить код до утверждения границы** — провайдеры не перенесены; в репо нет ни одного .py-провайдера.

## 8. Валидация по мандату

- **MD-3 не изменён:** аркаим `git status` = `M runtime/tests/test_m8_1_present_anchor.py` (Этап 1, ACCEPTED) + 2 untracked док-артефакта (отчёты Этапов 1–2, ожидавшие коммита по вашему решению). Ни MediaPlan, ни маршруты, ни SceneContext, ни WorldModel/temporal, ни frontend — не тронуты.
- **Контрольные прогоны Аркаима (не зависимость, а защита от случайных правок):** в этом milestone не запускались — код Аркаима не изменялся; последний контроль 134/134 (MD-3) и 207/207 (temporal) зафиксирован в Этапе 1 и остаётся актуальным.
- **Новый репо:** 15/15 контрактных тестов зелёные (pytest от аркаим-venv; зависимостей в pyproject на M4.1 нет — пустые dependencies, httpx/FastAPI придут с кодом в M4.2).

## 9. Что дальше (требует owner-GO)

**GO на контракт v1.0** (утверждение границы) → **M4.2 — перенос providers**: ComfyUI/video/mock provider stack; никаких новых возможностей; никакого оживления Quality; пять существующих маршрутов Аркаима не меняются (подмена цепи — только за DI-фабрику adc_deps, с миграционным мостом).

**STOP: M4.1 завершён. Код провайдеров не перенесён. Жду owner-GO.**
