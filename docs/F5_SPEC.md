<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL - НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Статусы, маршруты, компоненты и упоминания бывшего v2 ниже отражают состояние на момент создания документа. Актуальность проверяйте по docs/CURRENT_DEVELOPMENT_STATE.md, docs/DOCUMENTATION_INDEX.md, текущему коду и ADR.

﻿<!-- FRONTEND-CONSOLIDATION-BANNER -->
> [!IMPORTANT]
> **Архитектура фронтенда (решение владельца, зафиксировано).**
> - Единственный frontend проекта — `arkaim-web`: единственное направление дальнейшей разработки.
> - `arkaim-web-v2` — **удалён** из репозитория как рабочее направление.
> - Перечень потенциально восстанавливаемой из бывшего v2 функциональности: `docs/FRONTEND_RESTORE_BACKLOG.md`.
> - Дальнейшие сравнения `arkaim-web` против `arkaim-web-v2` не проводятся. Ниже могут встречаться исторические упоминания v2 (в датированных аудитах/спеках) — они относятся к удалённому направлению и НЕ означают сосуществования двух действующих фронтендов.

# F5 SPEC вЂ” Pre-implementation Audit v3

**Р”Р°С‚Р°:** 2026-09-18 В· **Р’РµСЂСЃРёСЏ:** v3 (РїРѕСЃР»Рµ arithmetic verification)
**РЎС‚Р°С‚СѓСЃ:** PRE-IMPLEMENTATION AUDIT (РЅРµ СЂРµР°Р»РёР·Р°С†РёСЏ)
**РњР°РЅРґР°С‚:** С‚РѕР»СЊРєРѕ С‡С‚РµРЅРёРµ, С‚РѕР»СЊРєРѕ СЃРїРµС†РёС„РёРєР°С†РёСЏ. РќРёРєР°РєРѕРіРѕ РєРѕРґР°.

---

## 1. РџСЂРѕСЃС‚С‹РјРё СЃР»РѕРІР°РјРё

F5 вЂ” СЌС‚Рѕ Р·Р°РІРµСЂС€РµРЅРёРµ frontend-РїСЂРѕРґСѓРєС‚Р°. Backend РїРѕР»РЅРѕСЃС‚СЊСЋ РіРѕС‚РѕРІ (РІСЃРµ 52 РєРѕРЅС‚СЂР°РєС‚Р° СЃСѓС‰РµСЃС‚РІСѓСЋС‚). РќР° РґРёСЃРєРµ Р»РµР¶Р°С‚ 5 РіРѕС‚РѕРІС‹С… СЃС‚СЂР°РЅРёС† (`/admin`, `/analytics`, `/profile`, `/status`, `/upload`), РєРѕС‚РѕСЂС‹Рµ Р¶РґСѓС‚ РєРѕРјРјРёС‚Р°. РќРµ С…РІР°С‚Р°РµС‚ 2 РЅРѕРІС‹С… СЃС‚СЂР°РЅРёС† (`/xray`, `/history`) Рё РёРЅС‚РµРіСЂР°С†РёРё WebSocket-С‚РѕСЃС‚РѕРІ.

**РќРёРєР°РєРёС… РёР·РјРµРЅРµРЅРёР№ backend РЅРµ С‚СЂРµР±СѓРµС‚СЃСЏ.**

---

## 2. РђСЂРёС„РјРµС‚РёРєР° вЂ” СЂР°Р·СЂРµС€С‘РЅРЅРѕРµ РїСЂРѕС‚РёРІРѕСЂРµС‡РёРµ

### 2.1 Р Р°Р·РЅС‹Рµ РјРЅРѕР¶РµСЃС‚РІР°

| РњРЅРѕР¶РµСЃС‚РІРѕ | РљРѕР»РёС‡РµСЃС‚РІРѕ | РћРїРёСЃР°РЅРёРµ |
|-----------|-----------|---------|
| Envelope keys | 90 | Р—Р°РїРёСЃРµР№ РІ `ENVELOPE_MAP` |
| OpenAPI paths | 290 | Р’СЃРµРіРѕ РїСѓС‚РµР№ РІ API |
| **F5 endpoints** | **52** | РџРѕРґРјРЅРѕР¶РµСЃС‚РІРѕ OpenAPI РґР»СЏ F5-РґРёР°РїР°Р·РѕРЅР° |
| ALREADY COVERED | 15 | F5 endpoints СѓР¶Рµ РІ envelope |
| REQUIRED ADDITIONS | 6 | F5 endpoints С‚СЂРµР±СѓСЋС‚ additions |
| OPTIONAL ADDITIONS | 10 | F5 endpoints РѕРїС†РёРѕРЅР°Р»СЊРЅС‹ |
| EXCLUDED | 21 | F5 endpoints РёСЃРєР»СЋС‡РµРЅС‹ РёР· F5 scope |

### 2.2 РџСЂРѕРІРµСЂРєР° СЃСѓРјРјС‹

```
ALREADY COVERED (15) + REQUIRED (6) + OPTIONAL (10) + EXCLUDED (21) = 52 вњ“
```

### 2.3 РџРѕС‡РµРјСѓ РІ v1 Р±С‹Р»Рѕ 50, Р° СЃРµР№С‡Р°СЃ 52?

Р’ v1 СЏ РїРѕСЃС‡РёС‚Р°Р» auth-admin РєР°Рє 12 endpoints, РЅРѕ С„Р°РєС‚РёС‡РµСЃРєРё РёС… **13** (РґРѕР±Р°РІР»РµРЅ `DELETE /auth/admin/sessions/{session_id}`). Р Р°Р·РЅРёС†Р° РІ 1 endpoint.

**РС‚РѕРіРѕРІС‹Р№ С‚РѕС‡РЅС‹Р№ total: 52 F5 endpoints.**

---

## 3. РџРѕР»РЅР°СЏ РєР»Р°СЃСЃРёС„РёРєР°С†РёСЏ РІСЃРµС… 52 F5 endpoints

### 3.1 Auth/Admin вЂ” 13 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 1 | GET | `/auth/admin/api-keys` | вњ… | COVERED | admin page uses this |
| 2 | DELETE | `/auth/admin/api-keys/{key_id}` | вњ… | COVERED | admin page uses this |
| 3 | POST | `/auth/admin/invites` | вќЊ | OPTIONAL | optional admin invites tab |
| 4 | GET | `/auth/admin/invites` | вќЊ | OPTIONAL | optional admin invites tab |
| 5 | DELETE | `/auth/admin/invites/{invite_id}` | вќЊ | OPTIONAL | optional admin invites tab |
| 6 | GET | `/auth/admin/sessions` | вќЊ | OPTIONAL | optional admin sessions tab |
| 7 | DELETE | `/auth/admin/sessions/{session_id}` | вќЊ | EXCLUDED | no UI scenario in F5 |
| 8 | GET | `/auth/admin/stats` | вњ… | COVERED | admin page uses this |
| 9 | GET | `/auth/admin/users` | вњ… | COVERED | admin page uses this |
| 10 | GET | `/auth/admin/users/{user_id}` | вњ… | COVERED | admin page uses this |
| 11 | DELETE | `/auth/admin/users/{user_id}` | вњ… | COVERED | admin page uses this |
| 12 | POST | `/auth/admin/users/{user_id}/role` | вњ… | COVERED | admin page uses this |
| 13 | POST | `/auth/admin/users/{user_id}/toggle` | вњ… | COVERED | admin page uses this |

**РС‚РѕРіРѕ auth-admin:** 13 total | 8 COVERED | 4 OPTIONAL | 1 EXCLUDED

### 3.2 Health вЂ” 2 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 14 | GET | `/book/health` | вќЊ | EXCLUDED | duplicate of /health, no consumer |
| 15 | GET | `/health` | вњ… | COVERED | status page uses this |

**РС‚РѕРіРѕ health:** 2 total | 1 COVERED | 0 OPTIONAL | 1 EXCLUDED

### 3.3 Reader вЂ” 10 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 16 | GET | `/book/reader/context` | вќЊ | EXCLUDED | no UI scenario in F5 |
| 17 | GET | `/book/reader/history` | вњ… | COVERED | profile page uses this |
| 18 | GET | `/book/reader/history/full` | вќЊ | REQUIRED | history page needs full content |
| 19 | GET | `/book/reader/history/sessions` | вќЊ | REQUIRED | history page needs sessions list |
| 20 | GET | `/book/reader/history/stats` | вњ… | COVERED | analytics page uses this |
| 21 | GET | `/book/reader/profile` | вњ… | COVERED | profile page uses this |
| 22 | POST | `/book/reader/reading-event` | вњ… | COVERED | reading page uses this |
| 23 | GET | `/book/reader/reading-position` | вњ… | COVERED | reading page uses this |
| 24 | GET | `/book/reader/reading-progress` | вњ… | COVERED | profile/analytics use this |
| 25 | GET | `/book/reader/stats` | вќЊ | OPTIONAL | optional extended analytics |

**РС‚РѕРіРѕ reader:** 10 total | 6 COVERED | 2 REQUIRED | 1 OPTIONAL | 1 EXCLUDED

### 3.4 X-Ray вЂ” 27 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 26 | GET | `/xray/audit` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 27 | GET | `/xray/audit/{trace_id}` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 28 | GET | `/xray/diagnostics` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 29 | GET | `/xray/events` | вќЊ | REQUIRED | xray page needs events list |
| 30 | GET | `/xray/events/stream` | вќЊ | REQUIRED | xray page needs SSE live feed |
| 31 | GET | `/xray/manual/{scenario}` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 32 | GET | `/xray/mode` | вќЊ | OPTIONAL | optional xray mode display |
| 33 | GET | `/xray/replay/{trace_id}` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 34 | POST | `/xray/retention/run` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 35 | GET | `/xray/retention/storage-stats` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 36 | GET | `/xray/retention/trace-list` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 37 | POST | `/xray/sanitize/orphan-cleanup` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 38 | GET | `/xray/sanitize/quarantine-list` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 39 | POST | `/xray/sanitize/repair-duplicates` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 40 | GET | `/xray/sanitize/scan-duplicates` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 41 | GET | `/xray/stats` | вќЊ | REQUIRED | xray page needs stats |
| 42 | GET | `/xray/store/status` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 43 | GET | `/xray/traces` | вќЊ | OPTIONAL | optional xray traces list |
| 44 | GET | `/xray/traces/{trace_id}` | вќЊ | OPTIONAL | optional xray trace details |
| 45 | POST | `/xray/traces/{trace_id}/freeze` | вќЊ | EXCLUDED | admin operation, no F5 UI |
| 46 | POST | `/xray/traces/{trace_id}/tag` | вќЊ | EXCLUDED | admin operation, no F5 UI |
| 47 | POST | `/xray/traces/{trace_id}/terminate` | вќЊ | EXCLUDED | admin operation, no F5 UI |
| 48 | POST | `/xray/traces/{trace_id}/unfreeze` | вќЊ | EXCLUDED | admin operation, no F5 UI |
| 49 | GET | `/xray/traces/active` | вќЊ | OPTIONAL | optional xray active traces |
| 50 | GET | `/xray/traces/completed` | вќЊ | OPTIONAL | optional xray completed traces |
| 51 | GET | `/xray/traces/search` | вќЊ | EXCLUDED | admin tool, no F5 UI |
| 52 | GET | `/xray/version` | вќЊ | REQUIRED | xray page needs version info |

**РС‚РѕРіРѕ xray:** 27 total | 0 COVERED | 4 REQUIRED | 5 OPTIONAL | 18 EXCLUDED

### 3.5 РС‚РѕРіРѕРІР°СЏ СЃРІРѕРґРєР° РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј

| РљР°С‚РµРіРѕСЂРёСЏ | Total | COVERED | REQUIRED | OPTIONAL | EXCLUDED |
|-----------|-------|---------|----------|----------|----------|
| auth-admin | 13 | 8 | 0 | 4 | 1 |
| health | 2 | 1 | 0 | 0 | 1 |
| reader | 10 | 6 | 2 | 1 | 1 |
| xray | 27 | 0 | 4 | 5 | 18 |
| **РРўРћР“Рћ** | **52** | **15** | **6** | **10** | **21** |

**РђСЂРёС„РјРµС‚РёС‡РµСЃРєР°СЏ РїСЂРѕРІРµСЂРєР°:** 15 + 6 + 10 + 21 = **52** вњ“

---

## 4. РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ envelope additions (6 С€С‚.)

РљР°Р¶РґС‹Р№ endpoint РїСЂРѕРІРµСЂРµРЅ РЅР° РЅР°Р»РёС‡РёРµ РІ OpenAPI Рё РЅР°Р»РёС‡РёРµ frontend consumer.

| # | Endpoint | Method | Type | Frontend consumer | F5 С„Р°Р№Р» | Response shape |
|---|----------|--------|------|-------------------|---------|---------------|
| 1 | `/xray/events/stream` | GET | SSE direct | `/xray` page (SSE-Р»РµРЅС‚Р°) | `contracts/xray.ts` | SSE stream: `event: <name>\ndata: <json>` |
| 2 | `/xray/stats` | GET | direct | `/xray` page (СЃС‚Р°С‚РёСЃС‚РёРєР°) | `contracts/xray.ts` | `{active_traces, completed_traces}` |
| 3 | `/xray/events` | GET | direct | `/xray` page (РїРѕСЃР»РµРґРЅРёРµ СЃРѕР±С‹С‚РёСЏ) | `contracts/xray.ts` | РјР°СЃСЃРёРІ СЃРѕР±С‹С‚РёР№ |
| 4 | `/xray/version` | GET | direct | `/xray` page (РІРµСЂСЃРёСЏ) | `contracts/xray.ts` | `{version, build}` |
| 5 | `/book/reader/history/sessions` | GET | enveloped | `/history` page (СЃРїРёСЃРѕРє СЃРµСЃСЃРёР№) | `contracts/reader.ts` | `{ok, data: Session[], total}` |
| 6 | `/book/reader/history/full` | GET | enveloped | `/history` page (РїРѕР»РЅР°СЏ РёСЃС‚РѕСЂРёСЏ) | `contracts/reader.ts` | `{ok, data: FullItem[], total}` |

**РџСЂРѕРІРµСЂРєР° OpenAPI:** РІСЃРµ 6 endpoints СЃСѓС‰РµСЃС‚РІСѓСЋС‚ вњ“

---

## 5. РџСЂРѕРІРµСЂРєР° РїСЏС‚Рё existing pages

### 5.1 `/admin` (426 СЃС‚СЂРѕРє)

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ |
|--------|-------|
| РљРѕРіРґР° СЃРѕР·РґР°РЅ | 2026-09-17 17:46 |
| РџРµСЂРІРѕРЅР°С‡Р°Р»СЊРЅС‹Р№ milestone | F5 (Product completion вЂ” admin) |
| РџРѕС‡РµРјСѓ РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє F5 | РЎС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РёСЃРїРѕР»СЊР·СѓРµС‚ С‚РѕР»СЊРєРѕ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ РєРѕРЅС‚СЂР°РєС‚С‹, С‚СЂРµР±СѓРµС‚ РєРѕРјРјРёС‚Р° |
| Tests | вњ… `admin.test.ts` (266 СЃС‚СЂРѕРє, 17.09) |
| Backend contracts | `GET /auth/admin/*`, `POST /auth/admin/*`, `DELETE /auth/admin/*` вЂ” 8 РїСѓС‚РµР№, РІСЃРµ РІ envelope |
| РР·РјРµРЅРµРЅРёР№ F5 | **0** вЂ” СЃС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РєРѕРјРјРёС‚ |
| Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ Р»Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ? | вњ… Р”Р° |

### 5.2 `/analytics` (300 СЃС‚СЂРѕРє)

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ |
|--------|-------|
| РљРѕРіРґР° СЃРѕР·РґР°РЅ | 2026-09-17 16:21 |
| РџРµСЂРІРѕРЅР°С‡Р°Р»СЊРЅС‹Р№ milestone | F5 (Product completion вЂ” analytics) |
| РџРѕС‡РµРјСѓ РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє F5 | РЎС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РёСЃРїРѕР»СЊР·СѓРµС‚ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ РєРѕРЅС‚СЂР°РєС‚С‹ |
| Tests | вњ… `analytics.test.ts` (149 СЃС‚СЂРѕРє, 17.09) |
| Backend contracts | `/book/reader/history/stats`, `/book/graph/stats`, `/book/cache/stats`, `/book/os/documents`, `/book/reader/reading-progress` вЂ” РІСЃРµ РІ envelope |
| РР·РјРµРЅРµРЅРёР№ F5 | **0** вЂ” СЃС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РєРѕРјРјРёС‚ |
| Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ Р»Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ? | вњ… Р”Р° |

### 5.3 `/profile` (177 СЃС‚СЂРѕРє)

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ |
|--------|-------|
| РљРѕРіРґР° СЃРѕР·РґР°РЅ | 2026-09-16 20:39 |
| РџРµСЂРІРѕРЅР°С‡Р°Р»СЊРЅС‹Р№ milestone | F2 (Reader Profile) |
| РџРѕС‡РµРјСѓ РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє F5 | РќРµ РєРѕРјРјРёС‡РµРЅ, СЏРІР»СЏРµС‚СЃСЏ С‡Р°СЃС‚СЊСЋ product completion |
| Tests | вќЊ РќРµС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ test-С„Р°Р№Р»Р° (С‚РµСЃС‚С‹ С‡РµСЂРµР· `contracts.test.ts`) |
| Backend contracts | `/book/reader/profile`, `/book/reader/history`, `/book/reader/reading-progress` вЂ” РІСЃРµ РІ envelope |
| РР·РјРµРЅРµРЅРёР№ F5 | **0** вЂ” СЃС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РєРѕРјРјРёС‚ |
| Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ Р»Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ? | вњ… Р”Р° |

### 5.4 `/status` (70 СЃС‚СЂРѕРє)

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ |
|--------|-------|
| РљРѕРіРґР° СЃРѕР·РґР°РЅ | 2026-09-16 20:39 |
| РџРµСЂРІРѕРЅР°С‡Р°Р»СЊРЅС‹Р№ milestone | F1 (Foundation dashboard) |
| РџРѕС‡РµРјСѓ РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє F5 | РќРµ РєРѕРјРјРёС‡РµРЅ, С‚СЂРµР±СѓРµС‚ РєРѕРјРјРёС‚Р° |
| Tests | вќЊ РќРµС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ test-С„Р°Р№Р»Р° |
| Backend contracts | `GET /health` вЂ” РІ envelope |
| РР·РјРµРЅРµРЅРёР№ F5 | **0** вЂ” СЃС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РєРѕРјРјРёС‚ |
| Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ Р»Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ? | вњ… Р”Р° |

### 5.5 `/upload` (236 СЃС‚СЂРѕРє)

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ |
|--------|-------|
| РљРѕРіРґР° СЃРѕР·РґР°РЅ | 2026-09-17 13:55 |
| РџРµСЂРІРѕРЅР°С‡Р°Р»СЊРЅС‹Р№ milestone | F5 (BookOS integration) |
| РџРѕС‡РµРјСѓ РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє F5 | РЎС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РёСЃРїРѕР»СЊР·СѓРµС‚ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ РєРѕРЅС‚СЂР°РєС‚С‹ |
| Tests | вњ… `upload.test.ts` (149 СЃС‚СЂРѕРє, 17.09) |
| Backend contracts | `GET /book/os/documents`, `POST /book/os/pipeline/ingest` вЂ” РІСЃРµ РІ envelope |
| РР·РјРµРЅРµРЅРёР№ F5 | **0** вЂ” СЃС‚СЂР°РЅРёС†Р° РіРѕС‚РѕРІР°, РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РєРѕРјРјРёС‚ |
| Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ Р»Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ? | вњ… Р”Р° |

---

## 6. РќРѕРІС‹Рµ СЃС‚СЂР°РЅРёС†С‹: РјРёРЅРёРјР°Р»СЊРЅС‹Р№ scope

### 6.1 `/xray` вЂ” SSE Observability

**Data sources (РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ):**
- `GET /xray/version` вЂ” РІРµСЂСЃРёСЏ (1 Р·Р°РїСЂРѕСЃ, СЃС‚Р°С‚РёС‡РЅРѕ)
- `GET /xray/stats` вЂ” active/completed traces count (СЃС‚Р°С‚РёС‡РЅРѕ)
- `GET /xray/events/stream` вЂ” SSE live Р»РµРЅС‚Р° (РѕС‚РєСЂС‹С‚РѕРµ СЃРѕРµРґРёРЅРµРЅРёРµ)

**РћРїС†РёРѕРЅР°Р»СЊРЅРѕ (РјРѕР¶РµС‚ Р±С‹С‚СЊ РґРѕР±Р°РІР»РµРЅРѕ РїРѕР·Р¶Рµ):**
- `GET /xray/events` вЂ” СЃРїРёСЃРѕРє РїРѕСЃР»РµРґРЅРёС… СЃРѕР±С‹С‚РёР№
- `GET /xray/mode` вЂ” С‚РµРєСѓС‰РёР№ СЂРµР¶РёРј
- `GET /xray/traces`, `/traces/active`, `/traces/completed` вЂ” СЃРїРёСЃРєРё С‚СЂРµР№СЃРѕРІ

**SSE lifecycle:**
```
mount   в†’ consumeSseResponse(fetch('/xray/events/stream'), { onEvent, onError })
        в†’ render event РІ СЃРїРёСЃРѕРє (bounded buffer: РїРѕСЃР»РµРґРЅРёРµ 100 СЃРѕР±С‹С‚РёР№)
        в†’ auto-reconnect РїСЂРё disconnect (reuse ws-client backoff pattern)
unmount в†’ AbortController.abort() + cleanup buffer
```

**React hook (РЅРѕРІС‹Р№):**
```ts
// shared/realtime/xray-sse.ts
export function useXraySse(onEvent: (e: XrayEvent) => void) {
  // consumeSseResponse в†’ wrapper РЅР°Рґ fetch + SSE parser
  // signal С‡РµСЂРµР· useEffect cleanup
  // bounded buffer: РїРѕСЃР»РµРґРЅРёРµ N СЃРѕР±С‹С‚РёР№
}
```

**XRayEvent С‚РёРї (РёР· OpenAPI description):**
```ts
export type XrayEvent =
  | { event: 'trace_completed'; data: { trace_id: string; name: string; duration_ms: number } }
  | { event: 'trace_frozen'; data: { trace_id: string } }
  | { event: 'trace_terminated'; data: { trace_id: string } }
  | { event: 'orphan_change'; data: { count: number } }
  | { event: 'stats_changed'; data: { active: number; completed: number } }
  | { event: 'heartbeat' };
```

**Р¤Р°Р№Р»С‹:**
- NEW: `src/app/(main)/xray/page.tsx` (~150 СЃС‚СЂРѕРє)
- NEW: `src/shared/api/contracts/xray.ts` (~50 СЃС‚СЂРѕРє)
- NEW: `src/shared/realtime/xray-sse.ts` (~60 СЃС‚СЂРѕРє)
- NEW: `tests/unit/xray.test.ts` (~80 СЃС‚СЂРѕРє)

### 6.2 `/history` вЂ” Reader Sessions

**Data sources (РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ):**
- `GET /book/reader/history/sessions` вЂ” СЃРїРёСЃРѕРє СЃРµСЃСЃРёР№ (enveloped, **Р±РµР· query params**)
- `GET /book/reader/history/full?limit=N&session_id=X` вЂ” РїРѕР»РЅС‹Р№ РєРѕРЅС‚РµРЅС‚ (enveloped, **limit + session_id**)

**Backend constraints (С„Р°РєС‚ РёР· OpenAPI):**

| РџР°СЂР°РјРµС‚СЂ | `history/sessions` | `history/full` |
|----------|-------------------|----------------|
| `limit` | вќЊ РЅРµС‚ | вњ… РµСЃС‚СЊ (default 100) |
| `offset` | вќЊ РЅРµС‚ | вќЊ РЅРµС‚ |
| `session_id` | вќЊ РЅРµС‚ | вњ… РµСЃС‚СЊ (optional) |
| `date_range` | вќЊ РЅРµС‚ | вќЊ РЅРµС‚ |
| `search` | вќЊ РЅРµС‚ | вќЊ РЅРµС‚ |

**Р РµР°Р»РёР·Р°С†РёСЏ С„РёР»СЊС‚СЂРѕРІ РЅР° frontend:**

| Р¤РёР»СЊС‚СЂ | Р РµР°Р»РёР·Р°С†РёСЏ | РћР±РѕСЃРЅРѕРІР°РЅРёРµ |
|--------|-----------|-------------|
| limit | вњ… backend support | `history/full?limit=N` |
| session_id | вњ… backend support | `history/full?session_id=X` |
| offset | вќЊ client-side pagination | backend РЅРµ РїРѕРґРґРµСЂР¶РёРІР°РµС‚, РёСЃРїРѕР»СЊР·СѓРµРј limit-based pagination |
| date range | вќЊ client-side filter | backend РЅРµ РїРѕРґРґРµСЂР¶РёРІР°РµС‚, С„РёР»СЊС‚СЂСѓРµРј СѓР¶Рµ РїРѕР»СѓС‡РµРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ |
| search by content | вќЊ client-side filter | backend РЅРµ РїРѕРґРґРµСЂР¶РёРІР°РµС‚, С„РёР»СЊС‚СЂСѓРµРј СѓР¶Рµ РїРѕР»СѓС‡РµРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ |

**UI layout:**
- Filter bar: session dropdown (РёР· `history/sessions`), limit selector
- Session list: expandable РєР°СЂС‚РѕС‡РєРё СЃ question content
- Client-side search Рё date filter РЅР°Рґ СѓР¶Рµ Р·Р°РіСЂСѓР¶РµРЅРЅС‹РјРё РґР°РЅРЅС‹РјРё

**Р¤Р°Р№Р»С‹:**
- NEW: `src/app/(main)/history/page.tsx` (~200 СЃС‚СЂРѕРє)
- CHANGE: `src/shared/api/contracts/reader.ts` вЂ” РґРѕР±Р°РІРёС‚СЊ `getHistorySessions()`, `getHistoryFull()`
- NEW: `tests/unit/history.test.ts` (~80 СЃС‚СЂРѕРє)

---

## 7. WS Toast вЂ” РёРЅС‚РµРіСЂР°С†РёСЏ

### 7.1 РЎСѓС‰РµСЃС‚РІСѓСЋС‰РµРµ СЃРѕСЃС‚РѕСЏРЅРёРµ

`WsProvider.tsx` (44 СЃС‚СЂРѕРєРё):
- РџРѕРґРєР»СЋС‡Р°РµС‚ WS РїСЂРё mount root layout
- Р­РєСЃРїРѕСЂС‚РёСЂСѓРµС‚ `useWsStatus()` вЂ” С‚РѕР»СЊРєРѕ boolean connected
- Р­РєСЃРїРѕСЂС‚РёСЂСѓРµС‚ `useWsEvent(event, handler)` вЂ” generic РїРѕРґРїРёСЃРєР°
- WS СЃРѕР±С‹С‚РёСЏ: `pulse_beat`, `new_suggestion`, `service_status`, `new_question`, `your_question_answered`, `chat_response`, `crowdfunding_milestone`

### 7.2 Toast policy

**Toast-triggering events (F5 scope):**
| РЎРѕР±С‹С‚РёРµ | Toast message |
|---------|--------------|
| `new_question` | В«РќРѕРІС‹Р№ РІРѕРїСЂРѕСЃ Рє РєРЅРёРіРµВ» |
| `your_question_answered` | В«РћС‚РІРµС‚ РЅР° РІР°С€ РІРѕРїСЂРѕСЃ РіРѕС‚РѕРІВ» |
| `new_suggestion` | В«РќРѕРІРѕРµ РїСЂРµРґР»РѕР¶РµРЅРёРµ РІ СЃРѕРѕР±С‰РµСЃС‚РІРµВ» |
| `crowdfunding_milestone` | В«РќРѕРІС‹Р№ milestone РєСЂР°СѓРґС„Р°РЅРґРёРЅРіР°В» |
| `service_status` | В«РЎС‚Р°С‚СѓСЃ СЃРµСЂРІРёСЃР° РёР·РјРµРЅС‘РЅВ» |

**РќР• toast (С‚РѕР»СЊРєРѕ log/debug):**
- `pulse_beat` вЂ” heartbeat, СЃР»РёС€РєРѕРј С‡Р°СЃС‚Рѕ
- `chat_response` вЂ” РїРѕС‚РѕРє РІ СЂРµР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё, РЅРµ С‚РѕСЃС‚

### 7.3 РРЅС‚РµРіСЂР°С†РёСЏ

**Р•РґРёРЅР°СЏ С‚РѕС‡РєР°:** СЃРѕР·РґР°С‚СЊ `WsToast.tsx` РІ `shared/realtime/`, РїРѕРґРєР»СЋС‡Р°С‚СЊ РІ root layout (СЂСЏРґРѕРј СЃ WsProvider).

```tsx
// shared/realtime/WsToast.tsx
export function WsToast() {
  const { message } = App.useApp();
  
  useWsEvent('new_question', () => message.info('РќРѕРІС‹Р№ РІРѕРїСЂРѕСЃ Рє РєРЅРёРіРµ'));
  useWsEvent('your_question_answered', () => message.success('РћС‚РІРµС‚ РЅР° РІР°С€ РІРѕРїСЂРѕСЃ РіРѕС‚РѕРІ'));
  useWsEvent('new_suggestion', () => message.info('РќРѕРІРѕРµ РїСЂРµРґР»РѕР¶РµРЅРёРµ РІ СЃРѕРѕР±С‰РµСЃС‚РІРµ'));
  useWsEvent('crowdfunding_milestone', () => message.success('РќРѕРІС‹Р№ milestone'));
  useWsEvent('service_status', () => message.warning('РЎС‚Р°С‚СѓСЃ СЃРµСЂРІРёСЃР° РѕР±РЅРѕРІР»С‘РЅ'));
  
  return null;
}
```

**РџРѕРґРєР»СЋС‡РµРЅРёРµ РІ `providers.tsx`:**
```tsx
<WsProvider>
  <WsToast /> {/* toast Р»РѕРіРёРєР° */}
  {children}
</WsProvider>
```

### 7.4 Reconnect behavior

- `WsClient` СѓР¶Рµ РёРјРµРµС‚ auto-reconnect (exponential backoff, max 10 attempts)
- `useWsEvent` С…СѓРє РїРµСЂРµР·Р°РїСѓСЃРєР°РµС‚ РїРѕРґРїРёСЃРєСѓ РїСЂРё РєР°Р¶РґРѕРј СЂРµСЂРµРЅРґРµСЂРµ СЃ РЅРѕРІС‹РјРё handler
- **РџСЂРѕР±Р»РµРјР°:** РїСЂРё reconnect РІСЃРµ `useWsEvent` handlers РїРµСЂРµР·aregistrent вЂ” РЅРѕ СЌС‚Рѕ РєРѕСЂСЂРµРєС‚РЅРѕ (СЌС„С„РµРєС‚ React run again)
- **Р РµС€РµРЅРёРµ:** РґРѕР±Р°РІРёС‚СЊ `key` РЅР° `WsToast` РёР»Рё РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ СЃС‚Р°Р±РёР»СЊРЅС‹Р№ reference РґР»СЏ handlers

### 7.5 Cleanup

РџСЂРё unmount `WsToast`:
- `useWsEvent` effect cleanup РІС‹Р·С‹РІР°РµС‚ `off()` вЂ” РїРѕРґРїРёСЃРєР° СѓРґР°Р»РµРЅР°
- РџСЂРё remount (РЅР°РІРёРіР°С†РёСЏ РЅР° РґСЂСѓРіСѓСЋ СЃС‚СЂР°РЅРёС†Сѓ Рё РЅР°Р·Р°Рґ) вЂ” РїРѕРґРїРёСЃРєРё РІРѕСЃСЃС‚Р°РЅР°РІР»РёРІР°СЋС‚СЃСЏ
- **РќРµС‚ СѓС‚РµС‡РµРє:** РєР°Р¶РґС‹Р№ `useEffect` РёРјРµРµС‚ cleanup

---

## 8. F5 вЂ” РїРѕР»РЅС‹Р№ СЃРїРёСЃРѕРє С„Р°Р№Р»РѕРІ

### 8.1 РќРѕРІС‹Рµ С„Р°Р№Р»С‹

| Р¤Р°Р№Р» | РћРїРёСЃР°РЅРёРµ | РЎС‚СЂРѕРє (РѕС†РµРЅРєР°) |
|------|----------|---------------|
| `src/app/(main)/xray/page.tsx` | SSE-Р»РµРЅС‚Р° С‚СЂР°СЃРёСЂРѕРІРѕРє | ~150 |
| `src/app/(main)/history/page.tsx` | РСЃС‚РѕСЂРёСЏ СЃРµСЃСЃРёР№ С‡РёС‚Р°С‚РµР»СЏ | ~200 |
| `src/shared/api/contracts/xray.ts` | XRay РєРѕРЅС‚СЂР°РєС‚С‹ | ~50 |
| `src/shared/realtime/xray-sse.ts` | SSE hook РґР»СЏ xray | ~60 |
| `src/shared/realtime/WsToast.tsx` | WS toast РёРЅС‚РµРіСЂР°С†РёСЏ | ~40 |
| `tests/unit/xray.test.ts` | XRay РєРѕРЅС‚СЂР°РєС‚ С‚РµСЃС‚С‹ | ~80 |
| `tests/unit/history.test.ts` | History РєРѕРЅС‚СЂР°РєС‚ С‚РµСЃС‚С‹ | ~80 |

### 8.2 РР·РјРµРЅСЏРµРјС‹Рµ С„Р°Р№Р»С‹

| Р¤Р°Р№Р» | РР·РјРµРЅРµРЅРёРµ | РџСЂРёС‡РёРЅР° |
|------|-----------|---------|
| `src/shared/api/envelope.ts` | +6 Р·Р°РїРёСЃРµР№ | xray + history endpoints |
| `src/shared/api/contracts/reader.ts` | +2 С„СѓРЅРєС†РёР№ | getHistorySessions, getHistoryFull |
| `src/shared/rbac/navigation.ts` | +2 items | xray (admin+), history (reader+) |
| `src/app/providers.tsx` | +WsToast | toast РёРЅС‚РµРіСЂР°С†РёСЏ |

### 8.3 РљРѕРјРјРёС‚ РіРѕС‚РѕРІС‹С… СЃС‚СЂР°РЅРёС† (5 С€С‚.)

| Р¤Р°Р№Р» | РЎС‚Р°С‚СѓСЃ | РЎС‚СЂРѕРєРё |
|------|--------|--------|
| `src/app/(main)/admin/page.tsx` | вњ… РіРѕС‚РѕРІ | 426 |
| `src/app/(main)/analytics/page.tsx` | вњ… РіРѕС‚РѕРІ | 300 |
| `src/app/(main)/profile/page.tsx` | вњ… РіРѕС‚РѕРІ | 177 |
| `src/app/(main)/status/page.tsx` | вњ… РіРѕС‚РѕРІ | 70 |
| `src/app/(main)/upload/page.tsx` | вњ… РіРѕС‚РѕРІ | 236 |

**Р’СЃРµ 5 СЃС‚СЂР°РЅРёС† РёСЃРїРѕР»СЊР·СѓСЋС‚ С‚РѕР»СЊРєРѕ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ backend-РєРѕРЅС‚СЂР°РєС‚С‹. Zero РёР·РјРµРЅРµРЅРёР№ backend.**

---

## 9. Test plan

### 9.1 РќРѕРІС‹Рµ С‚РµСЃС‚С‹

| Р¤Р°Р№Р» | Р§С‚Рѕ С‚РµСЃС‚РёСЂСѓРµС‚ | РћР¶РёРґР°РµРјС‹Р№ СЂРµР·СѓР»СЊС‚Р°С‚ |
|------|--------------|---------------------|
| `xray.test.ts` | envelope map (4 Р·Р°РїРёСЃРё), xray contract types | 4+ tests PASS |
| `history.test.ts` | envelope map (2 Р·Р°РїРёСЃРё), getHistorySessions, getHistoryFull | 4+ tests PASS |
| `ws-toast.test.ts` | toast events: new_question, your_question_answered, new_suggestion | 3+ tests PASS |

### 9.2 РР·РјРµРЅСЏРµРјС‹Рµ С‚РµСЃС‚С‹

| Р¤Р°Р№Р» | РР·РјРµРЅРµРЅРёРµ |
|------|-----------|
| `contracts.test.ts` | Р”РѕР±Р°РІРёС‚СЊ РїСЂРѕРІРµСЂРєСѓ 6 РЅРѕРІС‹С… envelope Р·Р°РїРёСЃРµР№ |
| `rbac.test.ts` | Р”РѕР±Р°РІРёС‚СЊ РїСЂРѕРІРµСЂРєСѓ РЅР°РІРёРіР°С†РёРѕРЅРЅС‹С… РїСѓРЅРєС‚РѕРІ xray/history |

### 9.3 РћР¶РёРґР°РµРјС‹Р№ РёС‚РѕРі

```
arkaim-web-v2 tests: 132 (С‚РµРєСѓС‰РёРµ) + 15 (РЅРѕРІС‹Рµ) = 147/147 PASS
next build: 24 СЃС‚СЂР°РЅРёС†С‹ (17 untracked + 5 F4 committed) в†’ РІСЃРµ СЃС‚Р°С‚РёС‡РЅРѕ РіРµРЅРµСЂРёСЂСѓСЋС‚СЃСЏ
```

---

## 10. Verification Checklist (post-F5)

- [ ] `/xray` СЃС‚СЂР°РЅРёС†Р° СЃСѓС‰РµСЃС‚РІСѓРµС‚, РїРѕРєР°Р·С‹РІР°РµС‚ SSE-Р»РµРЅС‚Сѓ + СЃС‚Р°С‚РёСЃС‚РёРєСѓ
- [ ] `/history` СЃС‚СЂР°РЅРёС†Р° СЃСѓС‰РµСЃС‚РІСѓРµС‚, РїРѕРєР°Р·С‹РІР°РµС‚ СЃРµСЃСЃРёРё СЃ С„РёР»СЊС‚СЂР°РјРё
- [ ] WS-С‚РѕСЃС‚С‹ РїРѕСЏРІР»СЏСЋС‚СЃСЏ РїСЂРё `new_question`, `your_question_answered`, `new_suggestion`
- [ ] 5 РіРѕС‚РѕРІС‹С… СЃС‚СЂР°РЅРёС† Р·Р°РєРѕРјРјРёС‡РµРЅС‹
- [ ] envelope.ts СЃРѕРґРµСЂР¶РёС‚ 6 РЅРѕРІС‹С… Р·Р°РїРёСЃРµР№ (xrayГ—4 + historyГ—2)
- [ ] 147/147 С‚РµСЃС‚РѕРІ green
- [ ] `next build` РїСЂРѕС…РѕРґРёС‚ (24 СЃС‚СЂР°РЅРёС†С‹)
- [ ] Backend РЅРµ РёР·РјРµРЅС‘РЅ (0 С„Р°Р№Р»РѕРІ РІ runtime/)
- [ ] Р Р°Р±РѕС‡РµРµ РґРµСЂРµРІРѕ: С‚РѕР»СЊРєРѕ F5-С„Р°Р№Р»С‹ + docs/

---

## 11. Р Р°Р·РґРµР»РµРЅРёРµ F5 Рё Technical Debt

| Р­Р»РµРјРµРЅС‚ | F5? | РћР±РѕСЃРЅРѕРІР°РЅРёРµ |
|---------|-----|-------------|
| M8.1 test-fix | вќЊ РќР• F5 | РћС‚РґРµР»СЊРЅС‹Р№ technical-debt item |
| Legacy `arkaim-web/` СѓРґР°Р»РµРЅРёРµ | вќЊ РќР• F5 | F6 scope |
| F6 (help, a11y, mobile, E2E) | вќЊ РќР• F5 | РЎР»РµРґСѓСЋС‰Р°СЏ С„Р°Р·Р° |
| Backend changes | вќЊ РќР• F5 | Р РµРіР»Р°РјРµРЅС‚ F-Р»РёРЅРµР№РєРё: 0 РёР·РјРµРЅРµРЅРёР№ |
| `reader/stats` envelope | вљ пёЏ РћРїС†РёРѕРЅР°Р»СЊРЅРѕ | РњРѕР¶РµС‚ Р±С‹С‚СЊ РґРѕР±Р°РІР»РµРЅ РїСЂРё СЂРµР°Р»РёР·Р°С†РёРё |
| `admin/sessions` + `admin/invites` | вљ пёЏ РћРїС†РёРѕРЅР°Р»СЊРЅРѕ | РњРѕРіСѓС‚ Р±С‹С‚СЊ РґРѕРї. С‚Р°Р±Р°РјРё РІ `/admin` |

---

## 12. РС‚РѕРіРѕРІР°СЏ СЃРІРѕРґРєР°

| РњРµС‚СЂРёРєР° | Р—РЅР°С‡РµРЅРёРµ |
|---------|---------|
| **TOTAL F5 endpoints** | **52** |
| ALREADY COVERED (РІ envelope) | 15 |
| REQUIRED ADDITIONS | 6 |
| OPTIONAL ADDITIONS | 10 |
| EXCLUDED | 21 |
| **РџСЂРѕРІРµСЂРєР°:** 15 + 6 + 10 + 21 | **= 52** вњ“ |
| РќРѕРІС‹С… СЃС‚СЂР°РЅРёС† | 2 (`/xray`, `/history`) |
| РљРѕРјРјРёС‚ РіРѕС‚РѕРІС‹С… СЃС‚СЂР°РЅРёС† | 5 (`/admin`, `/analytics`, `/profile`, `/status`, `/upload`) |
| РќРѕРІС‹Р№ РєРѕРґ (СЃС‚СЂРѕРєРё, РѕС†РµРЅРєР°) | ~580 |
| РќРѕРІС‹Рµ С‚РµСЃС‚С‹ (СЃС‚СЂРѕРєРё, РѕС†РµРЅРєР°) | ~160 |
| **Backend changes** | **0** |
| **M8.1 included** | **РќРµС‚** |
| **F6 included** | **РќРµС‚** |
| **Legacy removal included** | **РќРµС‚** |

---

## STOP

Р­С‚Рѕ complete pre-implementation audit v3. **РќРёРєР°РєРѕРіРѕ РєРѕРґР° РЅРµ РЅР°РїРёСЃР°РЅРѕ.**
РЎР»РµРґСѓСЋС‰РёР№ step вЂ” owner-GO РЅР° **F5 implementation**.
