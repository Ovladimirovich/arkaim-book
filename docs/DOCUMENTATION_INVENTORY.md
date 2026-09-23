# DOCUMENTATION INVENTORY — Post-F4 Rebaseline (R1)

**Дата создания:** 2026-09-18  
**Метод:** read-only аудит всех `.md` в `docs/` + сверка с git-историей и фактическим кодом  
**Цель:** однозначная карта каждого документа — что он делает, каков его статус, что с ним делать

---

## 1. SOURCE OF TRUTH (главные источники истины)

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `CURRENT_DEVELOPMENT_STATE.md` | CURRENT / NORMATIVE | Обновлён 2026-09-18 | ✅ **ДА** — главный operational SoT | **Оставить + обновить** (см. R1 §5) | Единственный документ, синтезирующий фактическое состояние; содержит stale info о M4.2.3/M4.2.4 — исправить |
| `README.md` (корень) | CURRENT / MARKETING | ~2026-08-08 | ❌ Нет — грубые метрики | **Обновить** или **архивировать** | Метрики устарели (29 стр→34, 195 роутов→219+). См. §14.7 |
| `AGENTS.md` (корень) | CURRENT / OPERATIONAL | ~2026-09 | ❌ Нет — неполная картина | **Обновить** | Не знает arkaim-media, MD-линию полностью, F4; пути ADR неверны |
| `CLAUDE.md` (корень) | CURRENT / REFERENCE | ~2026-07-20 | ❌ Нет — сильно устарел | **Архивировать** | Дублирует outdated инфу; 2 идентичных блока World Engine; нет MD-линии |

---

## 2. ADR (Architecture Decision Records)

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `ADR/ADR_0001_BOOK_IS_PRIMARY_SOURCE.md` | CURRENT / NORMATIVE | Принят | ✅ Да | **Оставить** | Базовый принцип проекта |
| `ADR/ADR_0002_BOOK_FIRST_LLM_SECOND.md` | CURRENT / NORMATIVE | Принят | ✅ Да | **Оставить** | Базовый принцип проекта |
| `ADR/ADR_0003_NO_AGENTS_BEFORE_INTELLIGENCE.md` | CURRENT / NORMATIVE | Принят | ✅ Да | **Оставить** | Базовый принцип проекта |
| `ADR/ADR_0004_SINGLE_BOOK_FIRST.md` | CURRENT / NORMATIVE | Принят | ✅ Да | **Оставить** | Базовый принцип проекта |
| `ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` | CURRENT / NORMATIVE | ✅ ACCEPTED (2026-09-14) | ✅ Да | **Оставить** | Граница проведена в коде, реализована |
| `ADR/ADR_MEDIA_PLAN_V0.md` | CURRENT / NORMATIVE | ✅ ACCEPTED | ✅ Да | **Оставить** | 10 owner-decisions, канон |
| `ADR/ADR_TEMPORAL_WORLD_MODEL.md` | CURRENT / NORMATIVE | ✅ ACCEPTED (2026-09-14) | ✅ Да | **Оставить** | Решения A-D реализованы в engine |
| `ADR_MERGE_PLAN.md` | HISTORICAL | Sprint-era | ❌ Нет | **Архивировать** | Исторический план слияния веток, не актуален |

---

## 3. КОРНЕВАЯ / ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `ARCHITECTURE.md` | HISTORICAL | ~2026-07-16 | ❌ Нет | **Архивировать** | Sprint-era архитектура; нет MD-линии; ADC-paths устарели |
| `PROJECT_STATE.md` | HISTORICAL | ~2026-08-08 | ❌ Нет | **Архивировать** | Нет MD-линии; 29 страниц (факт: 34); дублируется CURRENT_DEVELOPMENT_STATE |
| `PROJECT_STATUS.md` | HISTORICAL | ~2026-08-08 | ❌ Нет | **Архивировать** | Нет MD-линии; 29 стр (факт 34); дублируется CURRENT_DEVELOPMENT_STATE |
| `PROJECT_SUMMARY.md` | HISTORICAL | ~2026-08-08 | ❌ Нет | **Архивировать** | Полный дубликат PROJECT_STATUS; redundant |
| `INTERFACE_CAPABILITIES.md` | HISTORICAL | ~2026-08-08 | ❌ Нет | **Архивировать** | 29 страниц (факт 34); устаревшие метрики |
| `INTERFACE_TODO.md` | HISTORICAL | 2026-07-20 | ❌ Нет | **Архивировать** | Sprint-era TODO; не актуален |
| `DEPLOY.md` | CURRENT / SUPPORTING | ~2026 | ✅ Частично | **Оставить** | Инструкции деплоя актуальны |
| `KNOWLEDGE_BASE.md` | CURRENT / SUPPORTING | ~2026 | ❌ Нет | **Оставить** | Полезный справочник по знаниям |
| `BOOK_INTELLEGENCE_PIPELINE_REPORT.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Исторический отчёт; детали перекрыты CURRENT_DEVELOPMENT_STATE |
| `DATA_DISCIPLINE_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-15 | ❌ Нет | **Архивировать** | Завершённый этап; детали не нужны для текущей работы |
| `PROVENANCE_COMPLETION_REPORT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Завершённый этап |
| `TRUTH_CORE_FORENSIC_AUDIT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Завершённый аудит |
| `MILESTONE_B_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Исторический этап B |
| `FORENSIC_AUDIT_GATEWAY_2026-09-16.md` | COMPLETED / HISTORICAL | 2026-09-16 | ❌ Нет | **Архивировать** | Завершённый аудит gateway |
| `FORENSIC_AUDIT_BACKEND_CHANGES_2026-09-18.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать** | Завершённый аудит бэкенд-изменений |
| `RECONCILIATION_REPORT_2026-09-18.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать** | Завершённый reconciliation |
| `STUDIO_SPEC.md` | HISTORICAL | ~2026 | ❌ Нет | **Архивировать** | Спецификация Studio; не актуальна |
| `READING_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Завершённый этап чтения |
| `READING_FORENSIC_VERIFICATION_REPORT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Завершённый аудит чтения |
| `READING_UX_REDESIGN_PLAN.md` | HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | План UX — не реализован |
| `UPLOAD_IMPLEMENTATION_PLAN.md` | HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | План загрузки — не реализован как отдельный этап |
| `ANALYTICS_IMPLEMENTATION_PLAN.md` | HISTORICAL / DEFERRED | 2026-09-17 | ❌ Нет | **Архивировать** | План аналитики; аналитика → separate milestone (D-F4-4) |
| `G0_IMPLEMENTATION_PLAN.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | G0 завершён |

---

## 4. FRONTEND АРХИТЕКТУРА И ОТЧЁТЫ

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `FRONTEND_ARCHITECTURE.md` | CURRENT / NORMATIVE | 2026-09-08 | ✅ Да — архитектурный контракт | **Оставить** | Формальный F1-F6 scope; определяет boundary; акт. хотя dates устарели |
| `FRONTEND_FORENSIC_AUDIT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Forensic-аудит legacy frontend; завершён |
| `FRONTEND_INVENTORY_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-17 | ❌ Нет | **Архивировать** | Inventory frontend; завершён |
| `F1_SPEC.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | SPEC F1 — реализован и принят |
| `F1_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | Pre-audit F1 — завершён |
| `F1_IMPLEMENTATION_PLAN.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | План F1 — выполнен |
| `F1_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Отчёт F1 — CLOSED |
| `F1_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Post-audit F1 — PASS |
| `F2_SPEC.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | SPEC F2 — реализован и принят |
| `F2_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Pre-audit F2 — завершён |
| `F2_IMPLEMENTATION_PLAN.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | План F2 — выполнен |
| `F2_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Отчёт F2 — ACCEPTED & CLOSED |
| `F2_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Post-audit F2 — PASS WITH FINDINGS |
| `F3_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-10 | ❌ Нет | **Архивировать** | Pre-audit F3 — завершён |
| `F3_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-10 | ❌ Нет | **Архивировать** | Отчёт F3 — ACCEPTED & CLOSED |
| `F3_FORENSIC_POST_AUDIT_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-10 | ❌ Нет | **Архивировать** | Post-audit F3 — PASS WITH FINDINGS |
| `F3_POST_AUDIT_FOLLOWUP_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-10 | ❌ Нет | **Архивировать** | Follow-up F3 — PA-1/PA-2 закрыты |
| `F4_SPEC.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать** | SPEC F4 — реализован и принят. **Статус в шапке верен: ACCEPTED & CLOSED** |
| `F4_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать** | Pre-audit F4 — завершён |
| `F4_SCOPE_DECISION_PACK.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать + исправить статус** | DECISIONS ACCEPTED; GO для реализации ПОЛУЧЕН (F4 IMPLEMENTED)._header stale: "GO for implementation pending" → "GO RECEIVED" |
| `F4_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-18 | ❌ Нет | **Архивировать** | Отчёт F4 — ACCEPTED & CLOSED |

---

## 5. MD-LINEAR (Media/Integration)

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `MD3_STAGE_CLOSURE.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать + пометить superseded** | ⚠️ Частично устарел (ссылка «ждёт GO на MD-4»), но MD-4/MD-5 уже DONE. Сохранить как историческую фиксацию MD-3 |
| `MD3_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-11 | ❌ Нет | **Архивировать** | Pre-audit MD-3 — завершён |
| `MD3_1_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать** | MD-3.1 — CLOSED |
| `MD3_2_ROUTE_{A,B,C,D,E}_{BASELINE,IMPLEMENTATION_REPORT}.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать** (10 файлов) | MD-3.2 routes — CLOSED |
| `MD3_3_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать** | MD-3.3 pre-audit — завершён |
| `MD3_3_DEPRECATION_REGISTRY.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать** | MD-3.3 deprecation registry — CLOSED |
| `MD3_3_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-12 | ❌ Нет | **Архивировать** | MD-3.3 — CLOSED |
| `MD2_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-11 | ❌ Нет | **Архивировать** | Pre-audit MD-2 — завершён |
| `MD2_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-11 | ❌ Нет | **Архивировать** | MD-2 — CLOSED |
| `MD2_POST_IMPLEMENTATION_FORENSIC_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-11 | ❌ Нет | **Архивировать** | Post-audit MD-2 — CLOSED |
| `MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | Pre-audit MD-4 — завершён |
| `MD4_M41_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | M4.1 bootstrap — CLOSED |
| `MD4_M42_1_PROVIDER_INVENTORY.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | M4.2.1 inventory — CLOSED |
| `MD4_M42_2_COMFYUI_MIGRATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | ⚠️ Superseeded M4.2.3/M4.2.4; header уже говорит «суперседирован». Историческая ценность: proof-of-concept миграции |
| `MD4_M43_BRIDGE_ARKAIM_SIDE.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | M4.3 bridge — CLOSED |
| `MD4_M44_LIVE_RUN_ARKAIM_SIDE.md` | COMPLETED / HISTORICAL | 2026-09-13 | ❌ Нет | **Архивировать** | M4.4 live run — CLOSED |
| `MD5_MIGRATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-14 | ❌ Нет | **Архивировать** | MD-5 — ACCEPTED. **НО: содержит ссылку «следующий — MD-6»** — это актуально! Оставить в archive как исторический, но CURRENT_DEVELOPMENT_STATE должен покрывать MD-6 |
| `MEDIA_DIRECTION_FOUNDATION.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Foundation MD-линии; ссылки на «Sprint» устарели; документ важен как origin |
| `FORENSIC_AUDIT_POST_MD5.md` | COMPLETED / HISTORICAL | 2026-09-14 | ❌ Нет | **Архивировать** | Post-MD-5 аудит — завершён |

---

## 6. TEMPORAL / M-СЕРИЯ

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `M0_ARCHITECTURE_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-04 | ❌ Нет | **Архивировать** | Pre-M0 аудит — завершён |
| `M1_CANON_PROVENANCE.md` | COMPLETED / HISTORICAL | 2026-09-04 | ❌ Нет | **Архивировать** | M1 — CLOSED |
| `M2_TEMPORAL_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-04 | ❌ Нет | **Архивировать** | M2 аудит — завершён |
| `M2_TEMPORAL_MODEL.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M2 — CLOSED |
| `M3_TEMPORAL_RECONSTRUCTION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-04 | ❌ Нет | **Архивировать** | M3 аудит — завершён |
| `M3_TEMPORAL_RECONSTRUCTION_MODEL.md` | COMPLETED / HISTORICAL | 2026-09-04 | ❌ Нет | **Архивировать** | M3 — CLOSED |
| `M4_INTEGRATION_MODEL.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M4 — CLOSED |
| `M4_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M4 pre-audit — завершён |
| `M5_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M5 pre-audit — завершён |
| `M5_TEMPORAL_INTEGRATION_MODEL.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M5 — CLOSED |
| `M7_2_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M7.2 pre-audit — завершён |
| `M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md` | COMPLETED / HISTORICAL | 2026-09-05 | ❌ Нет | **Архивировать** | M8 — CLOSED |
| `M8_1_ARCHITECTURE_DECISION.md` | COMPLETED / HISTORICAL | 2026-09-06 | ❌ Нет | **Архивировать** | M8.1 решение — CLOSED (интегрировано в ADR_TEMPORAL) |
| `M8_1_ARCHITECTURE_DECISION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-06 | ❌ Нет | **Архивировать** | Audit M8.1 — завершён |
| `M8_1_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-06 | ❌ Нет | **Архивировать** | M8.1 impl — CLOSED |
| `M8_1_IMPLEMENTATION_SUMMARY.md` | DUPLICATE | 2026-09-06 | ❌ Нет | **Архивировать** | Дубликат M8_1_IMPLEMENTATION_REPORT |
| `M8_1_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-06 | ❌ Нет | **Архивировать** | Post-audit M8.1 — завершён |
| `M8_1_TEST_ISOLATION_FIX_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | Fix теста M8.1 — CLOSED |
| `M9_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | M9 pre-audit — завершён |
| `M9_SPEC.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | M9 — ACCEPTED & CLOSED |
| `M9_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-08 | ❌ Нет | **Архивировать** | Post-audit M9 — CLOSED |
| `M10_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10 pre-audit — завершён |
| `M10_IMPLEMENTATION_PLAN.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10 план — выполнен |
| `M10_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10 — CLOSED |
| `M10_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Post-audit M10 — CLOSED |
| `M10_2_PRE_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10.2 pre-audit — завершён |
| `M10_2_IMPLEMENTATION_PLAN.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10.2 план — выполнен |
| `M10_2_IMPLEMENTATION_REPORT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | M10.2 — CLOSED |
| `M10_2_POST_IMPLEMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-09 | ❌ Нет | **Архивировать** | Post-audit M10.2 — ACCEPTED & CLOSED |
| `TEMPORAL_CHAIN_AUDIT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Temporal chain audit — завершён |
| `TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Temporal arch audit — завершён |
| `TEMPORAL_API_ALIGNMENT_{PLAN,REPORT,FORENSIC_AUDIT}.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** (3 файла) | Temporal alignment — завершён |
| `TEMPORAL_LEGACY_FORENSIC_AUDIT.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Legacy temporal audit — завершён |
| `TEMPORAL_LEGACY_REFINEMENT_{DESIGN_CHECK,IMPLEMENTATION_REPORT}.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** (2 файла) | Legacy refinement — завершён |

---

## 7. ВНУТРЕННИЕ / SPRINT-ERA / ИСТОРИЧЕСКИЕ

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `internal/SYSTEM_AUDIT.md` | HISTORICAL | 2026-07-09 | ❌ Нет | **Архивировать** | Sprint-era аудит; исправлено всё |
| `internal/ANALYSIS_REPORT.md` | HISTORICAL | 2026-07-23 | ❌ Нет | **Архивировать** | Blackbox analysis; historical |
| `internal/SESSION_SUMMARY.md` | HISTORICAL | 2026-07-20 | ❌ Нет | **Архивировать** | World Engine session summary; исторический |
| `internal/PLAN_NEXT.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | ⚠️ Уже помечен «АРХИВ» в документе. M11 не актуален |
| `internal/nimble-nebula-notes.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Заметки сессии; исторические |
| `compose/reports/BACKEND_AUDIT_2026-07-10.md` | HISTORICAL | 2026-07-10 | ❌ Нет | **Архивировать** | Backend audit — завершён |
| `sprint_0_summary.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Sprint 0 summary; исторический |
| `plan_sprint2.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Sprint 2 plan; исторический |
| `plan_sprint2d_crowdfunding.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Crowdfunding plan; исторический |
| `restructuring_plan.md` | HISTORICAL | 2026-07-10 | ❌ Нет | **Архивировать** | Перестройка; исторический |
| `project_overview.md` | HISTORICAL | 2026-07-10 | ❌ Нет | **Архивировать** | Обзор проекта; исторический |
| `TEST_REPORT.md` | HISTORICAL | 2026-07-20 | ❌ Нет | **Архивировать** | Устаревшие метрики тестов |
| `provenance_forensic_map.md` | HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Map provenance — завершён |
| `forensic_investigation_studio.md` | HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** | Studio investigation — завершён |

---

## 8. ПОДСИСТЕМЫ / РУКОВОДСТВА

| Документ | Категория | Статус | Source of Truth? | Действие | Причина |
|----------|-----------|--------|------------------|----------|---------|
| `AI_ENGINEER_GUIDE.md` | CURRENT / SUPPORTING | ~2026-08-08 | ❌ Нет | **Оставить** | Полезный гайд для инженеров; частично устарел но ценен |
| `ComfyUI.md` | HISTORICAL | 2026-07-19 | ❌ Нет | **Архивировать** | Colab-setup guide; устарел (Local ComfyUI теперь) |
| `comfyui_guide.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Устаревшие ссылки на HF/Pollinations |
| `visual_genome_guide.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Sprint-era guide; не актуален |
| `visualization_layer.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Sprint-era; не актуален |
| `WORLD_ENGINE.md` | HISTORICAL | 2026-07-20 | ❌ Нет | **Архивировать** | Устаревший; данные в CURRENT_DEVELOPMENT_STATE |
| `WORLD_EXPLORER.md` | HISTORICAL | 2026-07-19 | ❌ Нет | **Архивировать** | Устаревший |
| `KNOWLEDGE_EXPANSION.md` | HISTORICAL | ~2026-07 | ❌ Нет | **Архивировать** | Historical |
| `KNOWLEDGE_CARDS_{CROSS_SOURCE,FORENSIC}_*.md` | COMPLETED / HISTORICAL | ~2026-09 | ❌ Нет | **Архивировать** (2 файла) | Завершённые этапы |
| `DOCUMENTATION_AUDIT.md` | COMPLETED / HISTORICAL | 2026-09-14 | ❌ Нет | **Архивировать** | Этот аудит — meta-документ; результаты инкорпорированы в R1. **НО** — сам документ ценен как история процесса. Архивировать с пометкой |
| `NEXT_PHASE_ARCHITECTURAL_AUDIT.md` | HISTORICAL | ~2026-09-08 | ❌ Нет | **Архивировать** | ⚠️ Уже помечен «АРХИВ» в документе. M11 не актуален |

---

## 9. СВОДКА КАТЕГОРИЙ

| Категория | Кол-во | Описание |
|-----------|--------|----------|
| **CURRENT / NORMATIVE** | 5 | CURRENT_DEVELOPMENT_STATE, ADR×7, FRONTEND_ARCHITECTURE, AGENTS.md (частично) |
| **CURRENT / SUPPORTING** | 4 | DEPLOY.md, KNOWLEDGE_BASE.md, AI_ENGINEER_GUIDE.md, README.md (обновить) |
| **COMPLETED / HISTORICAL** | ~70 | Все MD/F/M-отчёты, pre/post-audits, implementation reports |
| **HISTORICAL / SUPERSEDED** | ~30 | Sprint-era, устаревшие статусы, дубликаты |
| **DUPLICATE** | 3 | PROJECT_STATUS / PROJECT_STATE / PROJECT_SUMMARY; M8_1_IMPLEMENTATION_SUMMARY; ComfyUI.md + comfyui_guide.md |
| **UNKNOWN** | 0 | Все документы идентифицированы |

---

## 10. Ключевые несоответствия, выявленные в ходе R1

| # | Несоответствие | Где | Что исправить |
|---|---------------|-----|---------------|
| R1-1 | M4.2.3/M4.2.4 в CURRENT_DEVELOPMENT_STATE: «НЕ НАЧАТ» | §6.5, строки 199–202 | Факт: `0256140` (M4.2.3), `4ccfd8e` (M4.2.4) — COMMITTED в arkaim-media. **Исправить на ACCEPTED & CLOSED** |
| R1-2 | MEDIA_CONTRACT v1.0 в CURRENT_DEVELOPMENT_STATE: «DRAFT — ждёт GO» | §9.1 | Факт: коммит `f0327cd` в arkaim-media — **ACCEPTED**. **Исправить статус** |
| R1-3 | F4_SCOPE_DECISION_PACK.md header: «GO for implementation pending» | строка 4 | Факт: GO получен, реализация выполнена, F4 ACCEPTED & CLOSED. **Исправить на «GO RECEIVED 2026-09-18»** |
| R1-4 | CURRENT_DEVELOPMENT_STATE.md строка 47: «Текущий этап — MD-5 ACCEPTED» | §2 Executive Summary | Факт: MD-5 ACCEPTED, **MD-6 CLOSED** (4be2a40). **Исправить** |
| R1-5 | CURRENT_DEVELOPMENT_STATE.md строка 28: «Следующий — M4.2.3 или F-линейка» | §2 | Факт: M4.2.3/M4.2.4/M4.3/M4.4 все DONE. **Следующий кандидат — M4.2.3… стоп, они все done. Следующий: M4.5 / MD-6 / F5** |
| R1-6 | ADR_TEMPORAL_WORLD_MODEL и ADR_ARKAIM_MEDIA_BOUNDARY в CURRENT_DEVELOPMENT_STATE §7: статусы верны (✅ ACCEPTED), но в шапках самих ADR когда-то были PROPOSED | — | Уже исправлено в самих ADR-файлах (видимо, после первого аудита). Проверить. |
| R1-7 | `docs/README.md` не существует (или устарел) | docs/ | Нет навигационного индексного документа для docs/ |
| R1-8 | `core/ADR/` пуст (по §4 CURRENT_DEVELOPMENT_STATE), но `docs/ADR/` содержит 7 ADR | §4 | Соответствует — core/ADR пуст, docs/ADR полон. AGENTS.md ошибочно говорит «ADR/ (корень) ПУСТАЯ» — это верный факт, но может запутать. |

---

## 11. Действия R1 — план

### 11.1 Архивировать (~95 файлов)
Переместить в `docs/archive/` с подкатегориями:
- `docs/archive/md-line/` — все MD*-отчёты
- `docs/archive/temporal/` — все M*-отчёты
- `docs/archive/frontend/` — все F*-отчёты
- `docs/archive/historical/` — sprint-era, устаревшие статусы, internal/
- `docs/archive/subsystems/` — WORLD_ENGINE, WORLD_EXPLORER, ComfyUI guides
- `docs/archive/completed/` — завершённые аудты и отчеты (DATA_DISCIPLINE, PROVENANCE, FORENSIC_*)

### 11.2 Оставить в docs/ (актуальные)
- `CURRENT_DEVELOPMENT_STATE.md` (обновить)
- `FRONTEND_ARCHITECTURE.md` (оставить — architectural contract)
- `ADR/*.md` (7 файлов)
- `DEPLOY.md`
- `AI_ENGINEER_GUIDE.md`
- `KNOWLEDGE_BASE.md`
- `README.md` (обновить метрики)

### 11.3 Исправить
- `CURRENT_DEVELOPMENT_STATE.md` — M4.2.3/M4.2.4 статус, MEDIA_CONTRACT статус, текущая фаза
- `F4_SCOPE_DECISION_PACK.md` — header status
- `README.md` — метрики

### 11.4 Создать
- `docs/archive/README.md` — навигация по архиву
- `docs/POST_F4_REBASELINE.md` — итоговый отчёт R1
