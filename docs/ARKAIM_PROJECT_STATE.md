# ARKAIM PROJECT STATE — 2026-10-18

> [!WARNING]
> **Срез на 2026-10-18 (HEAD `b3bd0ac`).** Не текущая status map.
> Актуальные числа (2026-10-21): World Engine — **503 сущности / 80 связей**; crosswalk —
> **3 одобренных соответствия**; `core/KNOWLEDGE/claim_temporal_links.json` — **15 записей**;
> frontend unit — **241/241 в 31 файле**; backend — **2636 passed, 0 failed**.
> Текущая карта: `docs/CURRENT_DEVELOPMENT_STATE.md`, реестр решений: `docs/OWNER_DECISION_SHEET.md`.

**Генерация:** автономная (без GOVERNANCE). Источники: `docs/PROJECT_REBASELINE_2026-10-18.md` (фактический ребазина 2026-10-18), git HEAD `b3bd0ac`, live-прогоны backend `:8642` (2026-10-18), frontend `:3000`.

**Статус:** OK для принятия следующих технических решений; аудит-индекс документации и несколько механических дублей задокументированы, но не устранены (см. §4).

---

## 1. ФАКТИЧЕСКОЕ СОСТОЯНИЕ

| Показатель | Значение | Проверка |
|---|---|---|
| git | `b3bd0ac` (master), 25 ahead/0 behind `origin/master` | verify |
| Backend-тесты | 2426 passed / 16 failed / 26 skipped (~9.5 мин, 2026-10-18) | PASS/FAIL |
| Frontend-тесты | 223 passed / 8 failed (32 теста, 2026-10-18) | h3 тройной |
| Backend-сервер | `:8642` OPEN, 326 путей OpenAPI | live |
| Frontend | `:3000` OPEN | live |
| Типовой паттерн | backend `runtime`, frontend `arkaim-web` | docs/AI_ENGINEER_GUIDE |

**Backend (2426/16/26):**
- 2426 passed — все кроме 3 сетевых запросов (cross-media rerun).
- 16 failed — нужна triage-корректировка (файлы тестов ранее в `runtime/tests/`).
- 26 skipped — механизм пропусков не разбирался.

**Frontend (223/8):**
- 8 failures — нужна triage (файлы в `arkaim-web/src/app/`).

**Live (2026-10-18):**
- Backend: 326 REST endpoints; `/book/*` (ask, genome, layers, world), `/auth/*`, `/api/*`, `/xray/*`, `/_ui/*`.
- Knowledge Core: `/knowledge/*` (world/temporal/resolve, cards, conflicts, reasoning) — confirm pattern.
- Studio: 41 endpoint `/studio/*` (Phase 1B committed, Phase 2 — working tree).

## 2. АРХИТЕКТУРА ПО ФАКТИЧЕСКОМУ СОСТОЯНИЮ (2026-10-18)

```
Читатель → Web UI (Next.js 16, :3000) → Gateway/API Proxy → Backend (FastAPI 0.136, :8642)
                                                                    │
                                    ┌───────────────────────────────┴───────────────┐
                                    │  BookPulse (Live Core)                        │
                                    │  ├─ Knowledge Core (Mutable)                 │
                                    │  │  ├─ Knowledge Cards (M1–M8)               │
                                    │  │  ├─ Evidence (M2)                         │
                                    │  │  ├─ Conflict/Correction (M5–M7)           │
                                    │  │  └─ knowledge_engine + M14/M21–M25        │
                                    │  ├─ Temporal Engine (M3–M8)                  │
                                    │  ├─ Identity / Mission (Immutable)          │
                                    │  └─ WorldModel (163+ entities, 8 events)     │
                                    │  World Engine (singleton)                    │
                                    │  BookVoice (LLM-микрофон)                    │
                                    │  ReaderMemory + World Engine                 │
                                    └─────────────────────────────────────────────┘
```

**Словарь (дословно по `chapter.md`):**
| Графем | Лексема | Реализация | C map |
|---|---|---|---|
| BOOK_DOCUMENT.json | книга | `core/KNOWLEDGE/BOOK_DOCUMENT.json` | C3 |
| enriched_chunks.json | enrichment | `runtime_data/enriched_chunks.json`? + Chroma | C3 |
| SYNOPSIS_DOCUMENT.json | сценарий | 119 сцен / 642 абзаца | C3 |
| id_map | канонический id | B3-A reconciliation | C3 |
| GENOME | геном | `core/GENOME/` | C3 |
| Research | исследование | `mkdir 100/creative_*`? + `mkdir 100/creative_*` | C3 |
| SoT | источники истины | SOURCE_OF_TRUTH, CANON | C3 |
| Canonical | канон | BOOK/AUTHOR/ARTICLES/INTERVIEWS/SYNOPSIS | C3 |
| Endurance | выносливость | M16 / СКИ?? | C3 |
| Stories | блоки сценария | `core/CORE/stories/` + studio | C3 |
| Scenes | сцены | `core/CORE/scenes/` (v2) | C3 |
## 3. ЧТО ОСТАЛОСЬ НЕ ПРОВЕРЕНО (OPEN ITEMS)

1. **Test-drift:** backend 16 failures + frontend 8 failures — нужен triage (конкретные файлы → fix).
2. **Live-test округление:** 2426/26 vs 2442/16 — разница 16 → нужен перезапуск того же baseline счётчика; пока статус OPEN.
3. **Docs-index:** `DOCUMENTATION_INDEX.md` ссылается на несуществующий `CURRENT_DEVELOPMENT_STATE.md` (регистр). `CURRENT_DEVELOPMENT_STATE.md` — оригинал 2026-10-11. Обновление индекса — рекомендация, не блокирующая ядро.
4. **Duplicates:** `runtime/core/CORE/WORLD_MODEL` + `core/CORE/WORLD_MODEL`; `runtime/core/KNOWLEDGE` + `core/KNOWLEDGE`; docs-дубли — tech debt, не влияют на пайплайн.
5. **studio.py:** `runtime/core/routes/studio.py` — пустой маршрутизатор (без `/studio`); 41 endpoint в `main.py` (Studio v2). Статус: Phase 1B committed, Phase 2 в working tree.
6. **Media:** `arkaim-media` — отдельный repo (MEDIA_CONTRACT v1.0, ACCEPTED); ComfyUI/Agnes live, ComfyICU LTX 2.5 I2V uncommitted; audio юридически заблокирован (D2). `MEDIA_PRODUCTION_MASTERPLAN` (2026-10-14) — PROPOSED, ждёт OWNER-GO.
7. **Knowledge Core:** `/knowledge/*` live 2026-10-18; canonical WorldModel stale (2026-07-16); relation graph пуст; crosswalk 2 маппинга. Перерасчёт данных — техническая задача, не блокирует ядро.
8. **archive/**: папка HISTORICAL; требуется архивировать/очистить.

## 4. ОГРАНИЧЕНИЯ (STOP GATE)

| Тип решения | Показано владельцу | Статус |
|---|---|---|
| Изменение canonical contract (provenance semantics) | `ADR_ARKAIM_MEDIA_BOUNDARY` | GATE |
| Изменение границы WorldModel/Temporal | WorldModel 163+ entities | GATE |
| Изменение публичного API contract | `/book/*`, `/knowledge/*`, `/studio/*` | GATE |
| Изменение persistence policy | SQLite + Chroma + runtime/runtime_data | GATE |
| Параллельные механизмы запуска | Makefile only | GATE (not) |
| `docs/CURRENT_DEVELOPMENT_STATE.md` → deprecated | SUPERSEDED | GATE (not) |

## 5. РЕКОМЕНДАЦИИ (COUNSEL / NEXT)

**Сделать в течение недели (без OWNER-GO):**
1. Triage backend 16 failures + frontend 8 failures (конкретные файлы → fix).
2. Перепроверить live-тест: привести к одному baseline (2426/26 vs 2442/16 → 2442/16/26 — rerun).
3. Закоммитить Phase 2 Studio во временную ветку (фиксирует baseline) + убрать трэкер.
4. Завершить `/studio` маршрутизацию: `runtime/core/routes/studio.py` → либо маршрутизатор (если базовый контракт нужен), либо явный плагин/декоратор (если Studio v2 покрыт в main.py).

**После OWNER-GO:**
5. Актуализировать `docs/DOCUMENTATION_INDEX.md` (ссылки, версии).
6. Очистить `archive/` (HISTORICAL) + `docs/CURRENT_DEVELOPMENT_STATE.md` (SUPERSEDED).
7. Удалить дубли `runtime/core/CORE/WORLD_MODEL` и `runtime/core/KNOWLEDGE` (по git).
8. Перерасчёт WorldModel и crosswalk на 2026-10-18 (Temporal Engine + M3/M4 resolvers).
9. `MEDIA_PRODUCTION_MASTERPLAN` (2026-10-14) — принять или отклонить владельцем.

