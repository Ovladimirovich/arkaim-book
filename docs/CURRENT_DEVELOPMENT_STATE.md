<!-- FRONTEND-CONSOLIDATION-BANNER -->
> [!IMPORTANT]
> **Архитектура фронтенда (решение владельца, зафиксировано).**
> - Единственный frontend проекта — `arkaim-web`: единственное направление дальнейшей разработки.
> - `arkaim-web-v2` — **удалён** из репозитория как рабочее направление.
> - Перечень потенциально восстанавливаемой из бывшего v2 функциональности: `docs/FRONTEND_RESTORE_BACKLOG.md`.
> - Дальнейшие сравнения `arkaim-web` против `arkaim-web-v2` не проводятся. Ниже могут встречаться исторические упоминания v2 (в датированных аудитах/спеках) — они относятся к удалённому направлению и НЕ означают сосуществования двух действующих фронтендов.

# CURRENT DEVELOPMENT STATE вЂ” С„Р°РєС‚РёС‡РµСЃРєР°СЏ РєР°СЂС‚Р° РїСЂРѕРµРєС‚Р° В«РќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°В»

**Р”Р°С‚Р° РїРµСЂРІРёС‡РЅРѕРіРѕ Р°СѓРґРёС‚Р°:** 2026-09-14 В· **РџРѕСЃР»РµРґРЅРµРµ РѕР±РЅРѕРІР»РµРЅРёРµ:** 2026-09-24 (GO-1: Р°РєС‚СѓР°Р»РёР·Р°С†РёСЏ РЅР° HEAD `8aef0f9`)
**РўРёРї РґРѕРєСѓРјРµРЅС‚Р°:** С„Р°РєС‚РёС‡РµСЃРєР°СЏ РєР°СЂС‚Р° РїСЂРѕРµРєС‚Р° В«РќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°В» вЂ” source-of-truth РґР»СЏ СЃРѕСЃС‚РѕСЏРЅРёСЏ СЂР°Р·СЂР°Р±РѕС‚РєРё
**РњРµС‚РѕРґ:** С‡С‚РµРЅРёРµ СЂРµР°Р»СЊРЅС‹С… С„Р°Р№Р»РѕРІ/РєРѕРґР°/git-РёСЃС‚РѕСЂРёРё; С„Р°РєС‚РёС‡РµСЃРєРёРµ Р·Р°РїСѓСЃРєРё С‚РµСЃС‚-СЃСЊСЋС‚РѕРІ; С…РµС€-СЃРІРµСЂРєРё; live-РїСЂРѕРІРµСЂРєР° ComfyUI-СЃРµСЂРІРµСЂР°. РќР°Р»РёС‡РёРµ С„Р°Р№Р»Р° РќР• СЃС‡РёС‚Р°Р»РѕСЃСЊ РґРѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІРѕРј СЂР°Р±РѕС‚С‹; РєР°Р¶РґС‹Р№ СЃСѓС‰РµСЃС‚РІРµРЅРЅС‹Р№ С„Р°РєС‚ СЃРЅР°Р±Р¶С‘РЅ РёСЃС‚РѕС‡РЅРёРєРѕРј.

---

## РџСЂРѕСЃС‚С‹РјРё СЃР»РѕРІР°РјРё (РґР»СЏ РІР»Р°РґРµР»СЊС†Р°)

1. **Р§С‚Рѕ Р±С‹Р»Рѕ С†РµР»СЊСЋ?** вЂ” РћСЃС‚Р°РЅРѕРІРёС‚СЊ СЂРµР°Р»РёР·Р°С†РёСЋ Рё РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ РїРѕР»РЅСѓСЋ С„Р°РєС‚РёС‡РµСЃРєСѓСЋ РєР°СЂС‚Сѓ РІСЃРµРіРѕ, С‡С‚Рѕ СѓР¶Рµ СЃРґРµР»Р°РЅРѕ, С‡С‚РѕР±С‹ Р»СЋР±РѕР№ РЅРѕРІС‹Р№ РёРЅР¶РµРЅРµСЂ/РР РїРѕРЅСЏР» РїСЂРѕРµРєС‚ Р±РµР· РёСЃС‚РѕСЂРёРё РїРµСЂРµРїРёСЃРєРё.

2. **Р§С‚Рѕ СЂРµР°Р»СЊРЅРѕ СЃРґРµР»Р°РЅРѕ?** вЂ” РџСЂРѕРІРµСЂРµРЅС‹ РґРІР° СЂРµРїРѕР·РёС‚РѕСЂРёСЏ (arkaim Рё arkaim-media), РІРµСЃСЊ git-Р¶СѓСЂРЅР°Р», РІСЃРµ ADR, ~45 milestone-РѕС‚С‡С‘С‚РѕРІ, РєР»СЋС‡РµРІС‹Рµ РјРѕРґСѓР»Рё РєРѕРґР°; С„Р°РєС‚РёС‡РµСЃРєРё Р·Р°РїСѓС‰РµРЅС‹ С‚РµСЃС‚-СЃСЊСЋС‚С‹ (РІСЃРµ РѕСЃРЅРѕРІРЅС‹Рµ Р·РµР»С‘РЅС‹Рµ: 106 backend test-С„Р°Р№Р»РѕРІ, 37 frontend test-С„Р°Р№Р»РѕРІ, 42/42 media). **Р’СЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7) Р·Р°РєСЂС‹С‚С‹.** Р’СЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6) Р·Р°РєСЂС‹С‚С‹. **G0 (OpenAI-compatible API) СЂРµР°Р»РёР·РѕРІР°РЅ Рё СЃР»РёС‚ РІ master.** **C2 (provenance РЅР° СЂС‘Р±СЂР°С…) РёСЃРїСЂР°РІР»РµРЅ.** **F-12 (film-studio Р‘Р”) FUNCTIONALLY ACCEPTED / CLOSED.** РЎР±РѕСЂРєРё: 14 С‚РµС…РЅРёС‡РµСЃРєРёС… РґРѕР»РіРѕРІ Р·Р°С„РёРєСЃРёСЂРѕРІР°РЅРѕ, 15 РЅРµСЃРѕРѕС‚РІРµС‚СЃС‚РІРёР№ РґРѕРєСѓРјРµРЅС‚Р°С†РёРё/РєРѕРґР° вЂ” РёСЃРїСЂР°РІР»РµРЅС‹ РіРґРµ РІРѕР·РјРѕР¶РЅРѕ.

3. **Р§С‚Рѕ РїРѕР»СѓС‡РёР»РѕСЃСЊ?** вЂ” PASS: СЌС‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ вЂ” С„Р°РєС‚РёС‡РµСЃРєР°СЏ РєР°СЂС‚Р°. РЎР°РјРѕРµ РІР°Р¶РЅРѕРµ: **С‚РµРєСѓС‰Р°СЏ С‚РѕС‡РєР° = F6 CLOSED / G0 CLOSED / C2 CLOSED / F-12 CLOSED / MD-7 CLOSED**. Р’СЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7), РІСЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6), G0, C2, F-12 СЂРµР°Р»РёР·РѕРІР°РЅС‹ Рё РїСЂРёРЅСЏС‚С‹. F6: /help СЃС‚СЂР°РЅРёС†Р°, 14 E2E С‚РµСЃС‚РѕРІ, a11y, eslint cleanup. G0: /v1/models, /v1/chat/completions, /providers/health, per-provider rate limiting, 12 С‚РµСЃС‚РѕРІ. **STOP РїРѕСЃР»Рµ F6/G0, Р¶РґС‘С‚ owner-GO РЅР° СЃР»РµРґСѓСЋС‰РёР№ СЌС‚Р°Рї**.

4. **Р•СЃС‚СЊ Р»Рё РїСЂРѕР±Р»РµРјС‹?** вЂ” Р”Р°, РїРµСЂРµС‡РёСЃР»РµРЅС‹ РІ В§13вЂ“14. Р“Р»Р°РІРЅР°СЏ: С‡Р°СЃС‚СЊ РґРѕРєСѓРјРµРЅС‚РѕРІ РІ РєРѕСЂРЅРµ repo (README/AGENTS/PROJECT_STATE) РѕРїРёСЃС‹РІР°РµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ РЅР° Р°РІРіСѓСЃС‚ 2026 Рё РЅРµ Р·РЅР°РµС‚ Рѕ MD-Р»РёРЅРёРё Рё arkaim-media; 4 С‚РµСЃС‚Р° РїР°РґР°СЋС‚ РїРѕ СЃС‚Р°СЂРѕР№ РїСЂРёС‡РёРЅРµ (РЅРµ СЃРІСЏР·Р°РЅС‹ СЃ С‚РµРєСѓС‰РµР№ СЂР°Р±РѕС‚РѕР№). **РћРґРЅРѕ РЅРѕРІРѕРµ:** mtime-flaky С‚РµСЃС‚ `test_routes_abcd_files_untouched` вЂ” РёСЃРїСЂР°РІР»РµРЅ РґРѕРїСѓСЃРєРѕРј 0.5s (pre-existing, РїР°РґР°Р» Рё РЅР° С‡РёСЃС‚РѕРј HEAD).

5. **Р§С‚Рѕ РїСЂРµРґР»Р°РіР°РµС‚СЃСЏ РґР°Р»СЊС€Рµ?** вЂ” РќРёС‡РµРіРѕ РЅРµ РґРµР»Р°СЋ. Р–РґСѓ РІР°С€РµРіРѕ GO (РІР°СЂРёР°РЅС‚С‹ РІ В§16).

---

## 1. Executive Summary

**РџСЂРѕРµРєС‚** вЂ” В«РќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°В»: С†РёС„СЂРѕРІРѕРµ СЃРѕР·РЅР°РЅРёРµ РєРЅРёРіРё. Backend FastAPI (:8642) + В«BookPulseВ» (СЏРґСЂРѕ Р·РЅР°РЅРёР№ Р±РµР· LLM) + World Engine (547 СЃСѓС‰РЅРѕСЃС‚РµР№) + temporal-РјРѕРґРµР»СЊ РјРёСЂР° (12 СЌРїРѕС… + Present + СЌРєСЃС‚СЂР°РїРѕР»СЏС†РёСЏ Р±СѓРґСѓС‰РµРіРѕ) + РІРёР·СѓР°Р»СЊРЅР°СЏ РіРµРЅРµСЂР°С†РёСЏ (5 РјР°СЂС€СЂСѓС‚РѕРІ С‡РµСЂРµР· MediaPlan v0) + 2 С„СЂРѕРЅС‚РµРЅРґР° (legacy `arkaim-web` РЅР° 34 СЃС‚СЂР°РЅРёС†С‹; РЅРѕРІС‹Р№ `arkaim-web-v2` РЅР° 10 СЃС‚СЂР°РЅРёС†) + РјРѕР±РёР»СЊРЅРѕРµ РїСЂРёР»РѕР¶РµРЅРёРµ (React Native, Р·Р°РіРѕС‚РѕРІРєР°).

**РўРµРєСѓС‰Р°СЏ С„Р°Р·Р° СЂР°Р·СЂР°Р±РѕС‚РєРё** вЂ” РІСЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7) Рё РІСЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6) Р·Р°РєСЂС‹С‚С‹. G0 (OpenAI-compatible API) СЃР»РёС‚ РІ master (merge `57d85f0`). C2 (provenance РЅР° СЂС‘Р±СЂР°С…) РёСЃРїСЂР°РІР»РµРЅ (commit `f1d5d60`, РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ РІ `7c8ab27`). F-12 (film-studio Р‘Р”) FUNCTIONALLY ACCEPTED / CLOSED (`c022e77`). MEDIA_CONTRACT v1.0 ACCEPTED (arkaim-media `f0327cd`). РЎР»РµРґСѓСЋС‰РёР№ СЌС‚Р°Рї С‚СЂРµР±СѓРµС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ owner-GO.

**Git-С„Р°РєС‚ (arkaim):** branch `master`, HEAD `8aef0f9` (fix: add missing .github and pre-commit config), СЂР°Р±РѕС‡РёР№ РЅР°Р±РѕСЂ: С‚РѕР»СЊРєРѕ `core/CORE/genome/history/index.json` (Р°РІС‚РѕР·Р°РїРёСЃСЊ, pre-existing). **Git-С„Р°РєС‚ (arkaim-media):** branch `master`, HEAD `f0327cd`, СЂР°Р±РѕС‡РµРµ РґРµСЂРµРІРѕ С‡РёСЃС‚РѕРµ. **Frontend v2:** arkaim-web-v2/src/ вЂ” 25 СЃС‚Р°С‚РёС‡РЅС‹С… СЃС‚СЂР°РЅРёС† (F1вЂ“F6 РІСЃРµ Р·Р°РєРѕРјРјРёС‡РµРЅС‹ РІ master); typed-РєРѕРЅС‚СЂР°РєС‚С‹ РёР· OpenAPI (290 РїСѓС‚РµР№), RBAC-РјР°С‚СЂРёС†Р° (298 РјР°СЂС€СЂСѓС‚РѕРІ), 37 test-С„Р°Р№Р»РѕРІ. РџРѕР»РЅС‹Р№ F1вЂ“F6 ACCEPTED & CLOSED.

**РљР»СЋС‡РµРІС‹Рµ СЂРµС€РµРЅРёСЏ, РЅРµ С‚СЂРµР±СѓСЋС‰РёРµ РїРѕРІС‚РѕСЂРЅРѕРіРѕ РѕР±СЃСѓР¶РґРµРЅРёСЏ:** ADR_ARKAIM_MEDIA_BOUNDARY (РіСЂР°РЅРёС†Р° РґРІСѓС… РїСЂРѕРµРєС‚РѕРІ), ADR_MEDIA_PLAN_V0 (РєРѕРЅС‚СЂР°РєС‚ MediaPlan + 10 owner-decisions), ADR_TEMPORAL_WORLD_MODEL (4 СЂРµС€РµРЅРёСЏ AвЂ“D Рѕ РІСЂРµРјРµРЅРё РјРёСЂР°), ADR M8.1 (Present-СЏРєРѕСЂСЊ). Р’СЃРµ вЂ” ACCEPTED/РєР°РЅРѕРЅРёС‡РµСЃРєРёРµ.

**РўРµСЃС‚С‹ (С„Р°РєС‚РёС‡РµСЃРєРёРµ РїСЂРѕРіРѕРЅС‹ СЌС‚РѕРіРѕ Р°СѓРґРёС‚Р°):** MD-3+MD-4 suite 141/141 PASS; temporal chunk 237/237 PASS; md2/m7/m10.x 74/74 PASS; visual-family 45 passed/4 skipped; visual+assets+film+md2 114 passed/4 failed (4 pre-existing `ModuleNotFoundError: runtime.core`); arkaim-media 42/42 PASS (РїСЂРё РїРѕР»РЅРѕР№ Р¤РЎ); arkaim-web-v2 134/134 PASS + 14 E2E PASS; backend test-С„Р°Р№Р»РѕРІ: 106; frontend test-С„Р°Р№Р»РѕРІ: 37.

---

## 2. Project Purpose

| Р’РѕРїСЂРѕСЃ | Р¤Р°РєС‚ | РСЃС‚РѕС‡РЅРёРє |
|---|---|---|
| РСЃС…РѕРґРЅР°СЏ С†РµР»СЊ | В«Р¦РёС„СЂРѕРІРѕРµ СЃРѕР·РЅР°РЅРёРµ РєРЅРёРіРё вЂћРќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°вЂњ (Рћ Р’Р»Р°РґРёРјРёСЂРѕРІРёС‡)В»: СЃРёСЃС‚РµРјР° СЃ Р¶РёРІС‹Рј СЏРґСЂРѕРј (Pulse), Р·РЅР°СЋС‰РёРј РєРЅРёРіСѓ **Р±РµР· LLM**; LLM вЂ” С‚РѕР»СЊРєРѕ В«РіРѕР»РѕСЃВ» (РјРёРєСЂРѕС„РѕРЅ) | README.md:1вЂ“53; AGENTS.md В«РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°В» |
| РљРѕРЅРµС‡РЅР°СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєР°СЏ Р·Р°РґР°С‡Р° | Р§РёС‚Р°С‚РµР»СЊ СЃРїСЂР°С€РёРІР°РµС‚ РєРЅРёРіСѓ в†’ Pulse РёС‰РµС‚ РѕС‚РІРµС‚ РІ СЃР»РѕСЏС… в†’ BookVoice С„РѕСЂРјСѓР»РёСЂСѓРµС‚ (LLM РїСЂРё РЅРёР·РєРѕР№ СѓРІРµСЂРµРЅРЅРѕСЃС‚Рё) в†’ IdentityLayer.validate() вЂ” С„РёРЅР°Р»СЊРЅР°СЏ РїСЂРѕРІРµСЂРєР°; РїР»СЋСЃ РёСЃСЃР»РµРґРѕРІР°РЅРёРµ РјРёСЂР°/РІСЂРµРјРµРЅРё, РІРёР·СѓР°Р»РёР·Р°С†РёСЏ СЃС†РµРЅ, СЃРѕРѕР±С‰РµСЃС‚РІРѕ | AGENTS.md В«РђСЂС…РёС‚РµРєС‚СѓСЂРЅС‹Рµ РїСЂРёРЅС†РёРїС‹В»; docs/AI_ENGINEER_GUIDE.md:18вЂ“39 |
| Р“Р»Р°РІРЅС‹Р№ РїСЂРѕРґСѓРєС‚ | РњРѕРЅРѕСЂРµРїРѕ `arkaim` (backend + СЏРґСЂРѕ + С„СЂРѕРЅС‚РµРЅРґС‹ + РґР°РЅРЅС‹Рµ РєРЅРёРіРё) | СЃС‚СЂСѓРєС‚СѓСЂР° СЂРµРїРѕ; git remote `github.com/Ovladimirovich/arkaim` |
| РћС‚РґРµР»СЊРЅС‹Р№ РїСЂРѕРµРєС‚/РїРѕРґСЃРёСЃС‚РµРјР° | **arkaim-media** вЂ” РёСЃРїРѕР»РЅРёС‚РµР»СЊ РіРµРЅРµСЂР°С†РёРё РёР·РѕР±СЂР°Р¶РµРЅРёР№/РІРёРґРµРѕ (РІС‹РґРµР»РµРЅ РёР· РђСЂРєР°РёРјР° РїРѕ ADR MEDIA BOUNDARY) | ADR_ARKAIM_MEDIA_BOUNDARY Decision 1; arkaim-media/docs/MEDIA_CONTRACT.md |
| РџСЂРѕРµРєС‚С‹ СЂСЏРґРѕРј | ComfyUI-СЃРµСЂРІРµСЂ (`C:\cd\ComfyUI_AMD\`, РїРѕСЂС‚ 8188 вЂ” СЂР°Р±РѕС‚Р°РµС‚, РїСЂРѕРІРµСЂРµРЅРѕ HTTP 200) Рё ComfyUI Agent v1 (MCP-РѕР±С‘СЂС‚РєР° `comfyui_mcp_server.py`) вЂ” **РЅРµ С‡Р°СЃС‚СЊ** РЅРё РђСЂРєР°РёРјР°, РЅРё Media-РїСЂРѕРµРєС‚Р°; DSH-РёРЅСЃС‚СЂСѓРјРµРЅС‚Р°СЂРёР№, РіСЂР°РЅРёС†С‹ РЅРµ СЃРјРµС€РёРІР°С‚СЊ | MD4_PRE В§6; live-РїСЂРѕРІРµСЂРєР° СЌС‚РѕРіРѕ Р°СѓРґРёС‚Р° |
| РўРµРєСѓС‰РёР№ СЌС‚Р°Рї | **F6 CLOSED / G0 CLOSED / C2 CLOSED / F-12 CLOSED / MD-7 CLOSED** (HEAD `8aef0f9`, 2026-09-24). Р’СЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7), РІСЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6), G0, C2, F-12 СЂРµР°Р»РёР·РѕРІР°РЅС‹ Рё РїСЂРёРЅСЏС‚С‹. РЎР»РµРґСѓСЋС‰РёР№ вЂ” С‚СЂРµР±СѓРµС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ owner-GO. | POST_F6_NEXT_MILESTONES_AUDIT.md; G0_IMPLEMENTATION_PLAN.md |
| РЎРѕР·РЅР°С‚РµР»СЊРЅРѕ РѕС‚Р»РѕР¶РµРЅРѕ | audio; quality-РѕР¶РёРІР»РµРЅРёРµ; queue/batch/regenerate-РјРёРіСЂР°С†РёСЏ; mobile; i18n; production hardening | MD3_STAGE_CLOSURE В§5; ADR_TEMPORAL В§6; MEDIA_DIRECTION_FOUNDATION В§DEFERRED |
| F4вЂ“F6 СЃС‚Р°С‚СѓСЃ | **F4 ACCEPTED & CLOSED** (2026-09-18); **F5 ACCEPTED & CLOSED** (2026-09-23, commit `a090ec8`: /xray SSE, /history, WS toast, 5 СЃС‚СЂР°РЅРёС† Р·Р°РєРѕРјРјРёС‡РµРЅС‹); **F6 ACCEPTED & CLOSED** (2026-09-23, commit `b4e6893`: /help, a11y, 14 E2E С‚РµСЃС‚РѕРІ, eslint cleanup). Backend 0 РёР·РјРµРЅРµРЅРёР№ РЅР° РІСЃРµС… С„Р°Р·Р°С…. | F5_SPEC.md; F6 commit |
| G0 СЃС‚Р°С‚СѓСЃ | **CLOSED** (2026-09-16, merge `57d85f0`): BaseProvider.list_models(), /v1/models, /v1/chat/completions, /providers/health, per-provider rate limiting, 12 С‚РµСЃС‚РѕРІ РІ test_g0.py. Backend РёР·РјРµРЅРµРЅРёСЏ: +10 С„Р°Р№Р»РѕРІ, +2464 СЃС‚СЂРѕРє. | G0_IMPLEMENTATION_PLAN.md; commit dc59011 |

---

## 3. Project Boundaries

**РђСЂРєР°РёРј РІР»Р°РґРµРµС‚ (РґРѕРјРµРЅ РєРЅРёРіРё):** Pulse-СЃР»РѕРё, World Engine, Knowledge Graph, RAG, temporal-РјРѕРґРµР»СЊ, genome, SceneContext, MediaPlan (СЃРјС‹СЃР»РѕРІРѕРµ Р·Р°РґР°РЅРёРµ), РІСЃРµ HTTP-РјР°СЂС€СЂСѓС‚С‹ AвЂ“E, Film Studio (С†РµР»РёРєРѕРј, owner-СЂРµС€РµРЅРёРµ В§16-3), AssetStorage (С„Р°Р№Р»С‹ Р°СЃСЃРµС‚РѕРІ + SQLite-РјРµС‚Р°РґР°РЅРЅС‹Рµ), queue, РѕР±Р° С„СЂРѕРЅС‚РµРЅРґР°, mobile.

**Media-РїСЂРѕРµРєС‚ РІР»Р°РґРµРµС‚ (РёСЃРїРѕР»РЅРµРЅРёРµ):** РїСЂРѕРІР°Р№РґРµСЂС‹ РіРµРЅРµСЂР°С†РёРё (СЃРµР№С‡Р°СЃ С‚РѕР»СЊРєРѕ ComfyUI РїРµСЂРµРЅРµСЃС‘РЅ), workflows-РєР°С‚Р°Р»РѕРі, ffmpeg-РјРµС…Р°РЅРёРєР° (С‡Р°СЃС‚РёС‡РЅРѕ: image_sequence РµС‰С‘ РІ РђСЂРєР°РёРјРµ), backend-config (COMFYUI_URL), `media_id`-СЂРµРµСЃС‚СЂ.

**Р—Р°РїСЂРµС‰РµРЅРѕ СЃРІСЏР·С‹РІР°С‚СЊ:** (ADR_ARKAIM_MEDIA_BOUNDARY Decision 5, РёРЅРІР°СЂРёР°РЅС‚С‹)
1. Core РђСЂРєР°РёРј вЂ” media-agnostic: РЅРё ComfyUI/workflow/node/checkpoint РІ РЅРѕРІС‹С… РґРѕРјРµРЅРЅС‹С… РјРѕРґСѓР»СЏС….
2. РќРёРєР°РєРёС… РїСЂСЏРјС‹С… Arkaimв†’ComfyUI HTTP РІРЅРµ Media-РєРѕРЅС‚СЂР°РєС‚Р°.
3. LLM РЅРµ СѓРїСЂР°РІР»СЏРµС‚ media-execution; Р°РіРµРЅС‚ РЅРµ СѓРїСЂР°РІР»СЏРµС‚ ComfyUI.
4. PromptBuilder РЅРµ РІС‹Р±РёСЂР°РµС‚ capability.
5. Scene Context вЂ” РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ РёСЃС‚РѕС‡РЅРёРє РІСЃРµС… РїР»Р°РЅРѕРІ.
6. Temporal вЂ” read-only РґР»СЏ media; РїР»Р°РЅС‹ РЅР°СЃР»РµРґСѓСЋС‚ provenance.
7. Media Plan в‰  Workflow в‰  Node Graph в‰  Capability в‰  Provider; Asset в‰  Media Request в‰  File.

**Р’СЂРµРјРµРЅРЅС‹Рµ РјРѕСЃС‚С‹ (Р»РµРіР°Р»СЊРЅС‹Рµ РґРѕ MD-5):** ExecutionDispatch (`core/CORE/media_plan/dispatch.py` вЂ” В«TEMPORARY MIGRATION BRIDGE вЂ” REMOVE IN MD-5В»); legacy prompt-РїСЂРѕРµРєС†РёРё A/B/C/E; MediaPlan-РєРѕРЅРІРµСЂС‚ РІ РєРѕРЅС‚СЂР°РєС‚Рµ v1 (5 execution-РїРѕР»РµР№).

---

## 4. Repository Map

| Р РµРїРѕР·РёС‚РѕСЂРёР№ | РџСѓС‚СЊ | Branch/HEAD | РќР°Р·РЅР°С‡РµРЅРёРµ |
|---|---|---|---|
| **arkaim** (РјРѕРЅРѕСЂРµРїРѕ) | `c:\proect_arkaim\arkaim` | master / `8aef0f9` | Р’СЃС‘, РєСЂРѕРјРµ РёСЃРїРѕР»РЅРµРЅРёСЏ РіРµРЅРµСЂР°С†РёРё; F1вЂ“F6 вњ…, G0 вњ…, C2 вњ…, F-12 вњ…, MD-1..MD-7 вњ…; fresh-start (`48c19c9`) вЂ” reference |
| **arkaim-media** | `c:\proect_arkaim\arkaim-media` | master / `d4bcef2` в†ђ `8e465cc` (root) | РСЃРїРѕР»РЅРёС‚РµР»СЊ РіРµРЅРµСЂР°С†РёРё (Media Contract v1.0 DRAFT + ComfyUI-РїСЂРѕРІР°Р№РґРµСЂ) |
| ComfyUI-СЃРµСЂРІРµСЂ (РІРЅРµ СЂРµРї) | `C:\cd\ComfyUI_AMD\` | вЂ” | Р“РµРЅРµСЂР°С†РёСЏ, HTTP :8188, DirectML 1GB VRAM |
| ComfyUI Agent v1 (РІРЅРµ СЂРµРї) | `C:\cd\ComfyUI_AMD\comfyui_mcp_server.py` | вЂ” | MCP-РёРЅСЃС‚СЂСѓРјРµРЅС‚ DSH-СЃРµСЃСЃРёР№; РќР• С‡Р°СЃС‚СЊ Media-РїСЂРѕРµРєС‚Р° |

**arkaim (РєР»СЋС‡РµРІС‹Рµ РєР°С‚Р°Р»РѕРіРё):**

| РџСѓС‚СЊ | Р§С‚Рѕ СЌС‚Рѕ |
|---|---|
| `runtime/` | FastAPI-Р±СЌРєРµРЅРґ: `core/main.py` (app), `core/adc_deps.py` (DI, 24+ СЃРµСЂРІРёСЃР°), `core/routes/` (10 СЂРѕСѓС‚-С„Р°Р№Р»РѕРІ), `auth/`, `bot/`, `memory/`, `tests/` (106 С‚РµСЃС‚-С„Р°Р№Р»РѕРІ) |
| `core/CORE/` | РЇРґСЂРѕ Р·РЅР°РЅРёР№: `pulse/` (СЃР»РѕРё, voice), `narrative_engine/` (world_engine, temporal/, story/, research/), `knowledge_graph/`, `intelligence/` (RAG), `visualization/` (СЃР»РѕР№ 1), `visual/` (СЃР»РѕР№ 2, SceneContext), `visual_assets/` (СЃР»РѕР№ 3, pipeline), `media_plan/` (MediaPlan v0), `film_studio/`, `providers/` (image/video + gigachat-LLM), `genome/`, `GENOME/` (РґР°РЅРЅС‹Рµ + workflows/), `KNOWLEDGE/` (50+ JSON), `CHROMA_DB/` |
| `arkaim-web/` | Legacy-С„СЂРѕРЅС‚РµРЅРґ: Next.js 16, React 19, AntD 6, 34 СЃС‚СЂР°РЅРёС†С‹, FSD, vitest+playwright. **Р—Р°РјРѕСЂРѕР¶РµРЅ** (РЅРµ СЂР°Р·РІРёРІР°РµС‚СЃСЏ РґРѕ Р·Р°РІРµСЂС€РµРЅРёСЏ arkaim-web-v2, FRONTEND_ARCHITECTURE В§12) |
| `arkaim-web-v2/` | РќРѕРІС‹Р№ С„СЂРѕРЅС‚РµРЅРґ (F1вЂ“F6 ACCEPTED & CLOSED; 25 СЃС‚СЂР°РЅРёС† РІ master; typed-РєРѕРЅС‚СЂР°РєС‚С‹ РёР· OpenAPI (290 РїСѓС‚РµР№), RBAC-РјР°С‚СЂРёС†Р° (298 РјР°СЂС€СЂСѓС‚РѕРІ), 37 test-С„Р°Р№Р»РѕРІ) |
| `arkaim-mobile/` | React Native + Expo, 8 СЌРєСЂР°РЅРѕРІ (chat, reading, login, profileвЂ¦), РѕР±С‰РёР№ API-СЃР»РѕР№. РќРµ РѕС‚РґРµР»СЊРЅС‹Р№ git-СЂРµРїРѕ |
| `docs/` | 100+ РґРѕРєСѓРјРµРЅС‚РѕРІ: ADR/ (3), MD-СЃРµСЂРёСЏ, M-СЃРµСЂРёСЏ (0вЂ“10.2), F-СЃРµСЂРёСЏ (1вЂ“3), temporal-СЃРµСЂРёСЏ, СЃС‚Р°СЂС‹Рµ РіР°Р№РґС‹ |
| `SCHEMAS/` | 5 JSON-Schema: MEDIA_PLAN, CHARACTER, ENTITY, QUOTE, THEME |
| `ADR/` (РєРѕСЂРµРЅСЊ) | **РџРЈРЎРўРђРЇ РґРёСЂРµРєС‚РѕСЂРёСЏ** вЂ” ADR-С„Р°Р№Р»С‹ С„Р°РєС‚РёС‡РµСЃРєРё РІ `docs/ADR/` (РЅРµСЃРѕРѕС‚РІРµС‚СЃС‚РІРёРµ AGENTS.md) |

**arkaim-media (13+ С„Р°Р№Р»РѕРІ, РїРѕ git + С‚РµСЃС‚РѕРІС‹Р№ РїСЂРѕРіРѕРЅ):**
`docs/MEDIA_CONTRACT.md` (v1.0 **ACCEPTED**, arkaim-media `f0327cd`), `schemas/` (4 СЃС…РµРјС‹), `examples/` (3), `tests/` (2 С„Р°Р№Р»Р°, 42+ С‚РµСЃС‚Р°), `media/config.py`, `media/image/{__init__,comfyui}.py`, `workflows/default.json` (SHA256 = Р°СЂРєР°РёРјСЃРєРѕРјСѓ, РїСЂРѕРІРµСЂРµРЅРѕ).

---

## 5. Architecture Map

### 5.1 РЎР»РѕРё (С„Р°РєС‚РёС‡РµСЃРєРёРµ, runtime-РїСѓС‚СЊ)

```
Р§РёС‚Р°С‚РµР»СЊ в†’ arkaim-web(-v2) (:3000/:3001) в†’ Next rewrites в†’ FastAPI (:8642)
  в†’ auth (JWT cookie / API-key) в†’ routes/* (9 СЂРѕСѓС‚РµСЂРѕРІ: book, visual, assets,
    film_studio, reader, temporal, temporal_updates, world_engine)
  в†’ adc_deps ServiceRegistry (DI) в†’ core/CORE/*
      Pulse (СЃР»РѕРё Р·РЅР°РЅРёР№, Р±РµР· LLM) в†” BookVoice (LLM: GigaChatв†’OpenRouter)
      WorldEngine (547 СЃСѓС‰РЅРѕСЃС‚РµР№) В· WorldModel (temporal, 12 СЌРїРѕС…+today)
      KnowledgeGraph В· RAG (ChromaDB) В· ReaderMemory (SQLite)
  Р’РёР·СѓР°Р»СЊРЅС‹Р№ РєРѕРЅС‚СѓСЂ (РєР°РЅРѕРЅРёС‡РµСЃРєРёР№ РїСѓС‚СЊ MD-3):
    request в†’ VisualContextBuilder.build_scene_context* (SceneContext =
      VisualContext + scene_extras{temporal,source_refs,integrity})
      в†’ MediaPlanBuilder в†’ MediaPlan (pydantic extra=forbid, 22 РїРѕР»СЏ)
      в†’ ExecutionDispatch (TEMPORARY)
      в†’ legacy prompt projection (byte-identical)
      в†’ AssetGenerationPipeline в†’ ImageProviderChain [ComfyUI, Mock]
        / VideoProviderChain [ImageSequence(ffmpeg), Mock]
      в†’ AssetStorage (SQLite data/visual_assets.db + files data/visual_assets/)
```

### 5.2 Р—Р°РІРёСЃРёРјРѕСЃС‚Рё Рё С‚РѕС‡РєРё СЃРѕРїСЂСЏР¶РµРЅРёСЏ

- **Р•РґРёРЅР°СЏ С‚РѕС‡РєР° DI:** `runtime/core/adc_deps.py` вЂ” РІСЃРµ media-СЃРµСЂРІРёСЃС‹ РёРЅСЃС‚Р°РЅС†РёСЂСѓСЋС‚СЃСЏ С‚РѕР»СЊРєРѕ РІ С„Р°Р±СЂРёРєР°С… (L63вЂ“109: image/video chain, pipeline, store, queue, film_store; L184вЂ“193: visual_context_builder СЃ world_model). Р­С‚Рѕ Р¶Рµ вЂ” РЅР°Р·РЅР°С‡РµРЅРЅР°СЏ С‚РѕС‡РєР° РїРѕРґРјРµРЅС‹ С†РµРїРё РЅР° MediaClient РІ M4.4 (MD4_PRE В§11).
- **Media-РјРѕРґСѓР»СЊ `core/CORE/media_plan/`** РёРјРїРѕСЂС‚РёСЂСѓРµС‚ РўРћР›Р¬РљРћ visual/ (SceneContext-СЃР»РѕР№) вЂ” РЅРё providers, РЅРё visual_assets (ADR_MEDIA_PLAN_V0 Decision 1; РїСЂРѕРІРµСЂРµРЅРѕ СЃС‚СЂСѓРєС‚СѓСЂРѕР№ С„Р°Р№Р»РѕРІ).
- **ComfyUI Р·РЅР°РµС‚ С‚РѕР»СЊРєРѕ:** adc_deps (СЂРµРіРёСЃС‚СЂР°С†РёСЏ), 2 С‚РµСЃС‚-С„Р°Р№Р»Р°, visualization/__init__ (СЂРµСЌРєСЃРїРѕСЂС‚ B4), scripts/. Р РѕСѓС‚С‹ Р·РЅР°СЋС‚ С‚РѕР»СЊРєРѕ С†РµРїСЊ (MD4_PRE В§2.3).
- **Р¦РёРєР»РёС‡РµСЃРєРёС… Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№ РЅРµС‚** (MD4_PRE В§2.2).

### 5.3 РЎС‚Р°Р±РёР»СЊРЅРѕРµ / РјРѕСЃС‚С‹ / legacy

| РљР»Р°СЃСЃ | РљРѕРјРїРѕРЅРµРЅС‚С‹ |
|---|---|
| **РЎС‚Р°Р±РёР»СЊРЅРѕРµ (РєР°РЅРѕРЅ, Р·Р°РјРѕСЂРѕР¶РµРЅРѕ РєРѕРЅС‚СЂР°РєС‚Р°РјРё)** | MediaPlan v0 (22 РїРѕР»СЏ + BANNED-РёРЅРІР°СЂРёР°РЅС‚), SceneContext (extras 3), 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E, temporal-РјРѕРґРµР»СЊ (M8.1 + B1/C1), M10.2 pending-updates, Voice-РїСЂРѕС‚РѕРєРѕР», genome, Media Contract v1.0 DRAFT (РІ arkaim-media), РјРёСЂРєРѕСЃС…РµРјС‹ SCHEMAS/ |
| **Р’СЂРµРјРµРЅРЅС‹Рµ РјРѕСЃС‚С‹ (СѓРґР°Р»РµРЅС‹ / РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹)** | ExecutionDispatch вЂ” СѓРґР°Р»С‘РЅ (MD-5, commit `d73d29a`); `/comfyui/*` СЂРѕСѓС‚С‹ вЂ” РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹ (MD-5); legacy-РїСЂРѕРјРїС‚-РїСЂРѕРµРєС†РёРё (PromptBuilder A/B) вЂ” byte-frozen, РЅРµ С‚СЂРѕРіР°С‚СЊ; GENOME/workflows-РєРѕРїРёСЏ РІ РђСЂРєР°РёРјРµ вЂ” СЃРѕС…СЂР°РЅСЏРµС‚СЃСЏ РґРѕ РєРѕРЅСЃР»РёРґСЃР°С†РёРё |
| **Legacy/debt** | visualization/prompt_builder (SD-РїСЂРѕРјРїС‚С‹, СЃР»РѕРІР°СЂСЊ 1); GenerationParams.quality (РјС‘СЂС‚РІРѕРµ РїРѕР»Рµ, D-7); stable_diffusion.py (РЅРµ РІ DI); pollinations.pyc (stale); providers.registry-РёРјРїРѕСЂС‚С‹ (РјС‘СЂС‚РІС‹Рµ, 4 С„Р°Р№Р»Р°); PromptComposer РєР°Рє DI-С‚РѕС‡РєР° (D5, РјС‘СЂС‚РІР°СЏ); СЃР»РѕРІР°СЂРё СЃС‚РёР»РµР№ Г—3 (MP-F8); D-3 (video-РїР»Р°РЅ Route C РЅРµ РґРѕС…РѕРґРёС‚ РґРѕ generate_video); D-4 (queue/async/batch/regenerate Р±РµР· РїР»Р°РЅР°) |

---

## 6. Implemented Milestones

Р¤РѕСЂРјР°С‚ СЃС‚Р°С‚СѓСЃРѕРІ: CLOSED (РїСЂРёРЅСЏС‚ РІР»Р°РґРµР»СЊС†РµРј) / ACCEPTED (РїСЂРёРЅСЏС‚, Р¶РґС‘С‚ С„РёРЅР°Р»СЊРЅРѕР№ С„РёРєСЃР°С†РёРё) / IMPLEMENTED+TESTED (Р¶РґС‘С‚ owner-СЂРµС€РµРЅРёСЏ) / DEFERRED.

### 6.1 Р Р°РЅРЅСЏСЏ Р»РёРЅРµР№РєР° (РёСЋР»СЊ 2026, Р·Р°С„РёРєСЃРёСЂРѕРІР°РЅР° CHANGELOG 1.0.0/2.0.0)

| Milestone | Р§С‚Рѕ СЃРґРµР»Р°РЅРѕ | Commit-РѕСЂРёРµРЅС‚РёСЂ | РЎС‚Р°С‚СѓСЃ |
|---|---|---|---|
| BookPulse v1 | 4 СЃР»РѕСЏ Pulse, BookVoice, ReaderMemory, Presence, EvolutionTracker, 349 С‚РµСЃС‚РѕРІ | `CHANGELOG.md` [1.0.0] 2026-07-09 | CLOSED |
| World Engine v2 | 547 СЃСѓС‰РЅРѕСЃС‚РµР№, 287 СЃРІСЏР·РµР№, 55 С„РѕСЂРј, 10 СЂРµР¶РёРјРѕРІ, 10 API; СЃР»РѕРё Pulse в†’ 10; 34 СЃС‚СЂР°РЅРёС†С‹ | `CHANGELOG.md` [2.0.0] 2026-07-20; commits 635868e, 0d393cb | CLOSED |
| World Explorer (15 СЌС‚Р°РїРѕРІ) | РџРѕРґСЃРёСЃС‚РµРјР° РёСЃСЃР»РµРґРѕРІР°РЅРёСЏ РјРёСЂР°: 111 С‚РµСЃС‚РѕРІ, 24 СЂРѕСѓС‚Р°, РёСЃС‚РѕСЂРёСЏ РІ SQLite, WebSocket | commits a9f251eвЂ¦f888913 (Р­С‚Р°РїС‹ 1вЂ“16) | CLOSED |
| Community/Enhanced | РЈРІРµРґРѕРјР»РµРЅРёСЏ, РєРѕРјРјРµРЅС‚Р°СЂРёРё, РїСЂРѕС„РёР»СЊ, СЂР°СЃС€РёСЂРµРЅРЅС‹Р№ РїРѕРёСЃРє, crowdfunding | commits 23ac86bвЂ¦e4179be | CLOSED |
| GigaChatв†’OpenRouter С†РµРїСЊ | LLM-РїСЂРѕРІР°Р№РґРµСЂС‹; HF/Pollinations СѓРґР°Р»РµРЅС‹ | commits 9a7f3dd, c38f64d; СѓРґР°Р»РµРЅРёРµ: 963322a | CLOSED |

### 6.2 Temporal-Р»РёРЅРµР№РєР° M0вЂ“M10.2 (СЃРµРЅС‚СЏР±СЂСЊ 2026)

| Milestone | Р—Р°РґСѓРјР°РЅРѕ | Р РµР°Р»РёР·РѕРІР°РЅРѕ | РўРµСЃС‚С‹ (РїРѕ РѕС‚С‡С‘С‚Р°Рј) | РЎС‚Р°С‚СѓСЃ | Р”РѕРєСѓРјРµРЅС‚ |
|---|---|---|---|---|---|
| M0 audit | РљР°СЂС‚Р° Р°СЂС…РёС‚РµРєС‚СѓСЂС‹ РїРµСЂРµРґ temporal | Р°СѓРґРёС‚ 0 РєРѕРґР° | вЂ” | CLOSED | M0_ARCHITECTURE_AUDIT.md |
| M1 canon+provenance | РРµСЂР°СЂС…РёСЏ РёСЃС‚РѕС‡РЅРёРєРѕРІ, 8 РєР°С‚РµРіРѕСЂРёР№ ProvenanceCategory | SourceHierarchy, ProvenanceTag | вЂ” | CLOSED | M1_CANON_PROVENANCE.md |
| M2 temporal model | TemporalNode/Relation/Graph | РјРѕРґРµР»СЊ + WorldModel-РјРѕСЃС‚ | вЂ” | CLOSED | M2_TEMPORAL_MODEL.md |
| M3 reconstruction | BACKWARD-СЂРµРєРѕРЅСЃС‚СЂСѓРєС†РёСЏ РїСѓС‚РµР№ | TemporalReconstructionEngine | вЂ” | CLOSED | M3_TEMPORAL_RECONSTRUCTION_MODEL.md |
| M4 integration | WorldModel.get_temporal_chain (M4-РјРѕСЃС‚) | С†РµРїРѕС‡РєР° PRECEDES РІ API | вЂ” | CLOSED | M4_INTEGRATION_MODEL.md |
| M5 temporal integration | API-СЂРѕСѓС‚С‹ /book/temporal/* | 7 СЂРѕСѓС‚РѕРІ temporal.py | 41 С‚РµСЃС‚ | CLOSED | M5_TEMPORAL_INTEGRATION_MODEL.md; commit 1f7c5db |
| M7.2 epoch visual | POST /visualize/epoch вЂ” temporalв†’visual РјРѕСЃС‚ | СЂРѕСѓС‚ B | test_m7_epoch_visual | CLOSED | M7_2_PRE_AUDIT |
| M8 future extrapolation | РЎС†РµРЅР°СЂРёРё Р±СѓРґСѓС‰РµРіРѕ РѕС‚ СЏРєРѕСЂСЏ | FutureExtrapolator, FUTURE_EXTRAPOLATION-РјР°СЂРєРёСЂРѕРІРєР° | test_m8_future_extrapolation | CLOSED | M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md |
| **M8.1 present anchor** | PRESENT=РјРµС‚РѕРґРѕР»РѕРіРёС‡РµСЃРєРёР№ СѓР·РµР», HYPOTHESIS; orphan-СѓРґР°Р»РµРЅРёРµ; enrichment СЏРєРѕСЂСЏ | reconstruction_engine 563вЂ“621; node.present_anchor | 13/13 PASS (РѕС‚С‡С‘С‚) | CLOSED | M8_1_ARCHITECTURE_DECISION.md |
| M9 temporal-aware Expansion | ExpansionLayer РѕС‚РІРµС‡Р°РµС‚ РЅР° temporal-Р·Р°РїСЂРѕСЃС‹ С‡РµСЂРµР· facade | intent-detection, provenance-С‚РµРіРё | 28/28 audit, 38/38 | CLOSED | M9_SPEC.md В«ACCEPTED & CLOSEDВ» |
| M10 pending updates | Р”РµС‚РµРєС‚РѕСЂв†’pendingв†’confirm/reject (in-memory) | temporal_update_manager | 432/432 | CLOSED | M10_* |
| **M10.2 API-РѕР±С‘СЂС‚РєР°** | 7 HTTP-СЌРЅРґРїРѕРёРЅС‚РѕРІ РѕС‡РµСЂРµРґРё, RBAC editor/admin | routes/temporal_updates.py | 16/16 audit | **ACCEPTED & CLOSED 2026-09-08** | M10_2_POST_AUDIT.md |

### 6.3 Frontend-Р»РёРЅРµР№РєР° F1вЂ“F6 (arkaim-web-v2, СЃРµРЅС‚СЏР±СЂСЊ 2026)

| Milestone | Р РµР°Р»РёР·РѕРІР°РЅРѕ | РўРµСЃС‚С‹ (С„Р°РєС‚) | РЎС‚Р°С‚СѓСЃ |
|---|---|---|---|
| FRONTEND_ARCHITECTURE | РџСЂРѕРµРєС‚ РЅРѕРІРѕРіРѕ С„СЂРѕРЅС‚РµРЅРґР° (РЅРµ РєРѕРґ) | вЂ” | DOCUMENTED |
| F1 С„СѓРЅРґР°РјРµРЅС‚ | arkaim-web-v2: РєР°СЂРєР°СЃ, auth, RBAC-РјР°С‚СЂРёС†Р° 298, typed-РєРѕРЅС‚СЂР°РєС‚С‹ (OpenAPI 290), WS/SSE | 85/85 (СЃСѓРјРјР°СЂРЅРѕ) | ACCEPTED & CLOSED |
| F2 В«Р”РёР°Р»РѕРі СЃ РєРЅРёРіРѕР№В» | Р­РєСЂР°РЅС‹ /, /reading, /profile, /status; SourceBadge; B1/B2-С„РёРєСЃС‹ | (РІС…РѕРґСЏС‚ РІ СЃСѓРјРјР°СЂРЅРѕ) | ACCEPTED & CLOSED |
| F3 В«Р’СЂРµРјСЏ РјРёСЂР°В» | /temporal (12 СЌРїРѕС…, provenance-Р±РµР№РґР¶Рё, today-РєР°СЂС‚РѕС‡РєР°, СЃС†РµРЅР°СЂРёРё Р±СѓРґСѓС‰РµРіРѕ) + /temporal/queue (M10.2 UI); ProvenanceBadge | (РІС…РѕРґРёС‚ РІ СЃСѓРјРјР°СЂРЅРѕ) | **ACCEPTED & CLOSED 2026-09-18** |
| F4 В«РџСЂРµРґР»РѕР¶РµРЅРёСЏ/РћС‡РµСЂРµРґРёВ» | 5 capabilities вЂ” community + presence/email/drafts/moderation (4 new pages + 26 tests). Backend: 0 РёР·РјРµРЅРµРЅРёР№. next build: 5/5 green. | 9 test-С„Р°Р№Р»РѕРІ (60 pre-existing + 26 new), 5 СЃС‚СЂР°РЅРёС† | **ACCEPTED & CLOSED 2026-09-18** |
| F5 В«Realtime/AdminВ» | /xray (SSE-Р»РµРЅС‚Р°), /history (reader sessions), WsToast (5 WS СЃРѕР±С‹С‚РёР№), +5 Р·Р°РєРѕРјРјРёС‡РµРЅРЅС‹С… СЃС‚СЂР°РЅРёС† (/admin, /analytics, /profile, /status, /upload). envelope +6 Р·Р°РїРёСЃРµР№. Backend: 0 РёР·РјРµРЅРµРЅРёР№. | 134/134 unit PASS; 14 E2E PASS | **ACCEPTED & CLOSED 2026-09-23** (commit `a090ec8`) |
| F6 В«PolishВ» | /help СЃС‚СЂР°РЅРёС†Р° (22 pages, 5 РєР°С‚РµРіРѕСЂРёР№); a11y РїСЂРѕС…РѕРґ; 14 E2E С‚РµСЃС‚РѕРІ (S1вЂ“S7 + help + mobile 375px); eslint cleanup. Backend: 0 РёР·РјРµРЅРµРЅРёР№. | 134/134 unit PASS; 14 E2E PASS | **ACCEPTED & CLOSED 2026-09-23** (commit `b4e6893`) |
| **F-12 film-studio Р‘Р”** | Production DB repair: `_migrate_schema()` idempotent guard for `film_shots.quality`; 5 regression tests; 3 shots preserved | 5 tests PASS; 45 film-related PASS | **FUNCTIONALLY ACCEPTED / CLOSED 2026-09-23** (commit `c022e77`) |

### 6.4 G0-Р»РёРЅРµР№РєР° (OpenAI-compatible API, СЃРµРЅС‚СЏР±СЂСЊ 2026)

| Milestone | Р РµР°Р»РёР·РѕРІР°РЅРѕ | Р¤Р°Р№Р»С‹ | РўРµСЃС‚С‹ | РЎС‚Р°С‚СѓСЃ |
|---|---|---|---|---|
| **G0 model discovery + OpenAI API** | BaseProvider.list_models(); GigaChat: 14 models via GET /models; OpenRouter: list_models СЃ 403-handling; /v1/models; /v1/chat/completions; /providers/health; per-provider rate limiting; DTO openai.py | +10 С„Р°Р№Р»РѕРІ, +2464 СЃС‚СЂРѕРє (runtime/core/dto/openai.py, providers/base.py, providers/gigachat.py, providers/openrouter.py, provider_registry.py, main.py, test_g0.py) | 12 new tests (test_g0.py) + updated test_providers.py | **CLOSED** (merge `57d85f0`, 2026-09-16) |

### 6.4 MD-Р»РёРЅРµР№РєР° (media-РєРѕРЅС‚СѓСЂ, СЃРµРЅС‚СЏР±СЂСЊ 2026)

| Milestone | Р РµР°Р»РёР·РѕРІР°РЅРѕ | Р¤Р°Р№Р»С‹ | РўРµСЃС‚С‹ | РЎС‚Р°С‚СѓСЃ |
|---|---|---|---|---|
| **MD-1 Foundation** | Forensic-Р°СѓРґРёС‚ РІРёР·СѓР°Р»СЊРЅРѕРіРѕ СЃС‚РµРєР° + ADR РіСЂР°РЅРёС†С‹ | MEDIA_DIRECTION_FOUNDATION.md, docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md | 0 (РґРѕРєСѓРјРµРЅС‚С‹) | CLOSED (РѕСЃРЅРѕРІР° Р»РёРЅРµР№РєРё) |
| **MD-2 Scene Context** | SceneContext=VisualContext+extras{temporal,source_refs,integrity}; 5 РјР°СЂС€СЂСѓС‚РѕРІ РЅР° РµРґРёРЅС‹Р№ РІС…РѕРґ; DEPRECATED-РјРµС‚РєРё; F-11 fix | scene_context.py (new), visual_context*.py, pipeline.py, routes/{visual,assets,film_studio}.py, adc_deps.py | 23+15 РЅРѕРІС‹С…; **РєРѕРЅС‚СЂРѕР»СЊ Р°СѓРґРёС‚Р°: MD-2-family 438/1 pre-existing** | **CLOSED / FINAL GREEN 2026-09-11** (MD2_POST_AUDIT В§0) |
| **MD-3 MediaPlan v0** | РљРѕРЅС‚СЂР°РєС‚ (22 РїРѕР»СЏ, BANNED), Builder, Dispatch; РІСЃРµ 5 РјР°СЂС€СЂСѓС‚РѕРІ РјРёРіСЂРёСЂРѕРІР°РЅС‹ (3.2 A/B/C/D/E РїРѕ РѕРґРЅРѕРјСѓ, SHA-СЃРІРµСЂРєРё РїСЂРѕРјРїС‚РѕРІ); SCHEMAS/MEDIA_PLAN.schema.json; 2 deprecation-РјРµС‚РєРё (D1/D5); СЂРµРµСЃС‚СЂ | media_plan/{schemas,builder,dispatch}.py; routes; pipeline; С‚РµСЃС‚С‹ 7 С„Р°Р№Р»РѕРІ (134) | **134/134 PASS** | **CLOSED 2026-09-12** (MD3_STAGE_CLOSure) |
| **MD-4 bootstrap** | Р’Р°СЂРёР°РЅС‚ A (РјРёРЅРёРјР°Р»СЊРЅС‹Р№): РѕС‚РґРµР»СЊРЅС‹Р№ СЂРµРїРѕ arkaim-media; M4.1вЂ“M4.5 РІСЃРµ Р·Р°РєСЂС‹С‚С‹ | СЃРј. В§6.5 | вЂ” | **CLOSED** |
| **MD-5 integration** | вњ… ACCEPTED (2026-09-14, commit `d73d29a`): ExecutionDispatch СѓРґР°Р»С‘РЅ, /comfyui/* РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹, РІСЃРµ 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E С‡РµСЂРµР· MediaPlan | 141/141 | **CLOSED** |
| **MD-6 Legacy cleanup** | 24 С„Р°Р№Р»Р° РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅС‹ РІ git (routes/providers/media_plan/tests); contract hardening | commit `4be2a40` | вЂ” | **CLOSED 2026-09-18** |
| **MD-7 M4.5 cleanup** | workflows/env РїРµСЂРµРµР·Рґ Р·Р°РІРµСЂС€С‘РЅ; /comfyui/* РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹ (РїРѕРґС‚РІРµСЂР¶РґРµРЅРѕ test_media_boundary); ExecutionDispatch СѓРґР°Р»С‘РЅ; РјС‘СЂС‚РІС‹Рµ Р°Р»РёР°СЃС‹ comfy/comfyui РІ image/__init__.py; stale comments РІ media_client.py. 4 С„Р°Р№Р»Р°, ~20 СЃС‚СЂРѕРє. | POST_F6_NEXT_MILESTONES_AUDIT.md В§2 | existing tests pass | **CLOSED 2026-09-23** |

### 6.5 MD-4 РїРѕРґСЌС‚Р°РїС‹ (РІСЃРµ Р·Р°РєСЂС‹С‚С‹)

| РџРѕРґСЌС‚Р°Рї | Р§С‚Рѕ СЃРґРµР»Р°РЅРѕ | РђСЂС‚РµС„Р°РєС‚С‹ | РўРµСЃС‚С‹ (С„Р°РєС‚) | РЎС‚Р°С‚СѓСЃ |
|---|---|---|---|---|
| Pre-audit | РРЅРІРµРЅС‚Р°СЂРёР·Р°С†РёСЏ РёСЃРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ СЃР»РѕСЏ, MOVE/KEEP-С‚Р°Р±Р»РёС†С‹, РІР°СЂРёР°РЅС‚С‹ A/B | MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md | 0 (РґРѕРєСѓРјРµРЅС‚) | CLOSED |
| Р­С‚Р°Рї 1: test-isolation fix | M8.1-С‚РµСЃС‚: try/finally `we._temporal_engine=None`; РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ РІ `7c8ab27` | M8_1_TEST_ISOLATION_FIX_REPORT.md | 237/237 temporal PASS | CLOSED (РІ master) |
| **M4.1 bootstrap** | Р РµРїРѕ arkaim-media + Media Contract v1.0 (4 СЃС…РµРјС‹, 5-РїРѕР»РµР№ execution-РєРѕРЅРІРµСЂС‚, 7 РєРѕРґРѕРІ РѕС€РёР±РѕРє) | arkaim-media root-commit `8e465cc` (13 С„Р°Р№Р»РѕРІ) | 15/15 | **CLOSED** |
| M4.2.1 inventory | Forensic-РѕРїРёСЃСЊ 7 РїСЂРѕРІР°Р№РґРµСЂРѕРІ; Q1=SD РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ, Q2=quality РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ, Q3=РїР°РєРµС‚ media/ | MD4_M42_1_PROVIDER_INVENTORY.md | 0 (РґРѕРєСѓРјРµРЅС‚) | CLOSED |
| **M4.2.2 ComfyUI migration** | comfyui.py в†’ media/image/ (152 СЃС‚СЂ.); workflows/default.json Р±Р°Р№С‚-РІ-Р±Р°Р№С‚ (SHA СЃРІРµСЂРµРЅ) | arkaim-media commit `d4bcef2` (5 С„Р°Р№Р»РѕРІ) | **42/42 PASS** | **CLOSED** |
| **M4.2.3 video** | image_sequence.py + mock.py в†’ media/video/ | arkaim-media commit `0256140` | **42/42 PASS** | **CLOSED** |
| **M4.2.4 chain/mock/svg** | ImageProviderChain + MockImage + SVGTemplate в†’ media/image/ | arkaim-media commit `4ccfd8e` | **PASS** | **CLOSED** |
| **M4.3 MediaClient-bridge** | Р—Р°РјРµРЅР° С†РµРїРё РІ adc_deps: legacy providers в†’ MediaClient РїРѕ РєРѕРЅС‚СЂР°РєС‚Сѓ v1.0 | arkaim `81612b7`; media `5922dcc` | **15/15 PASS** | **CLOSED** |
| **M4.4 Р¶РёРІРѕР№ РїСЂРѕРіРѕРЅ** | Live byte-gate: 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E С‡РµСЂРµР· MediaClient | arkaim `b5d399d`; media `0d10396` | **207/207 PASS** | **CLOSED** |
| **M4.5 workflows/env** | workflows/env РїРµСЂРµРµР·Рґ + РґРµ-РїСѓР±Р»РёРєР°С†РёСЏ | MD-5 | вЂ” | **CLOSED (РІ MD-5)** |

---

## 7. Accepted ADR / Decisions

РўСЂРё ADR С„РёР·РёС‡РµСЃРєРё РЅР°С…РѕРґСЏС‚СЃСЏ РІ `docs/ADR/` (РїСѓСЃС‚РѕР№ РєРѕСЂРЅРµРІРѕР№ `ADR/` вЂ” СЃРј. В§14-1).

### 7.1 ADR_TEMPORAL_WORLD_MODEL (docs/ADR/, 2026-09-09)
**РЎС‚Р°С‚СѓСЃ-РїРѕРјРµС‚РєР° РІ С„Р°Р№Р»Рµ: PROPOSED вЂ” РѕР¶РёРґР°РµС‚ ACCEPTED** вЂ” РќРћ РїРѕ С„Р°РєС‚Сѓ РїРѕСЃР»РµРґСѓСЋС‰РёС… СЂРµР°Р»РёР·Р°С†РёР№ (B1+C1 РІС‹РїРѕР»РЅРµРЅС‹, F3 РїРѕСЃС‚СЂРѕРµРЅ РЅР° РµРіРѕ РёРЅРІР°СЂРёР°РЅС‚Р°С…, TEMPORAL_API_ALIGNMENT_REPORT РЅР°Р·С‹РІР°РµС‚ РµРіРѕ В«ACCEPTEDВ») СЂРµС€РµРЅРёСЏ РїСЂРёР·РЅР°РЅС‹ РєР°РЅРѕРЅРёС‡РµСЃРєРёРјРё. Р­С‚Рѕ РЅРµСЃРѕРѕС‚РІРµС‚СЃС‚РІРёРµ СЃС‚Р°С‚СѓСЃР° вЂ” СЃРј. В§14-4.

| Р РµС€РµРЅРёРµ | РЎСѓС‚СЊ | Р§С‚Рѕ Р·Р°РїСЂРµС‰Р°РµС‚ | Р РµР°Р»РёР·РѕРІР°РЅРѕ |
|---|---|---|---|
| **A. TODAY** | `temporal_today` вЂ” РјРµС‚РѕРґРѕР»РѕРіРёС‡РµСЃРєРёР№ TemporalNode (HYPOTHESIS, confidence 1.0), Р’ РіСЂР°С„Рµ, Р‘Р•Р— relations; РµРґРёРЅСЃС‚РІРµРЅРЅР°СЏ С„Р°Р±СЂРёРєР° `present_anchor()` | РЎРѕР·РґР°РІР°С‚СЊ Today-СѓР·Р»С‹ РёРЅР°С‡Рµ; today РІ chains; AUTHOR_CANON РґР»СЏ Present | вњ… engine (M8.1) + API B1 (nodes РІРєР»СЋС‡Р°РµС‚ today) |
| **B. Relation** | PRECEDES вЂ” РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ С‚РёРї РѕСЃРё; СЂРµР±СЂРѕ С‚РѕР»СЊРєРѕ РјРµР¶РґСѓ СЃРѕСЃРµРґСЏРјРё; РґСѓР±Р»Рё Р·Р°РїСЂРµС‰РµРЅС‹; DEVELOPS_FROM/TRANSFORMS_INTO вЂ” С‚РѕР»СЊРєРѕ С‡РµР»РѕРІРµРє С‡РµСЂРµР· M10.2 | РќРѕРІС‹Рµ С‚РёРїС‹ СЂР°РґРё РѕСЃРё; Р±РёРґРёСЂРµРєС†РёРѕРЅРЅС‹Рµ СЂС‘Р±СЂР°; Р°РІС‚РѕСЃРѕР·РґР°РЅРёРµ РєРѕРЅС‚РµРєСЃС‚РЅС‹С… СЃРІСЏР·РµР№ | вњ… (11 PRECEDES вЂ” live-С„Р°РєС‚С‹) |
| **C. Provenance** | ProvenanceTag РЅР° РєР°Р¶РґРѕРј СѓР·Р»Рµ/СЂРµР±СЂРµ; РєР°С‚РµРіРѕСЂРёРё: СѓР·Р»С‹ AUTHOR_CANON+EXTERNAL_SOURCE/HYPOTHESIS; СЂС‘Р±СЂР° DERIVED/RECONSTRUCTION **РќРРљРћР“Р”Рђ AUTHOR_CANON**; FUTURE_EXTRAPOLATION РґР»СЏ M8; UI РѕР±СЏР·Р°РЅ РїРѕРєР°Р·С‹РІР°С‚СЊ Р±РµР№РґР¶Рё | AUTHOR_CANON РЅР° СЂС‘Р±СЂР°С… РѕСЃРё; UI-СЃР°РјРѕРґРµСЏС‚РµР»СЊРЅРѕСЃС‚СЊ; РѕС‚РґРµР»СЊРЅС‹Р№ СЂРµРµСЃС‚СЂ provenance | вњ… C2 РёСЃРїСЂР°РІР»РµРЅ (commit `f1d5d60`, РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ `7c8ab27`): `precedes()` СЃС‚Р°РІРёС‚ `ProvenanceCategory.DERIVED`; С‚РµСЃС‚ `test_precedes_is_derived_from_epoch_order` PASS |
| **D. Anchor** | `temporal_arkaim_era` РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ СЏРєРѕСЂСЊ; ArkaimAnchor-dataclass вЂ” С‚РѕР»СЊРєРѕ РёСЃС‚РѕС‡РЅРёРє enrichment; alias-РїСЂР°РІРёР»Рѕ РґРѕРєСѓРјРµРЅС‚РЅРѕРµ | Р’С‚РѕСЂРѕР№ anchor-СѓР·РµР»; С‚СЂРµС‚СЊСЏ СЃСѓС‰РЅРѕСЃС‚СЊ | вњ… (orphan СѓРґР°Р»СЏРµС‚СЃСЏ engine-РїСѓС‚С‘Рј) |
| РРЅРІР°СЂРёР°РЅС‚ В§5 | Р¤СЂРѕРЅС‚РµРЅРґ РЅРµ РґРѕСЃС‚СЂР°РёРІР°РµС‚ temporal graph | РЎРёРЅС‚РµС‚РёС‡РµСЃРєРёРµ СЃРІСЏР·Рё, В«СЃРєСЂС‹С‚С‹Рµ Р»РёРЅРёРёВ», РІС‹С‡РёСЃР»РµРЅРёРµ РїСЂРѕРїСѓС‰РµРЅРЅС‹С… СЌРїРѕС… | вњ… (F3-С‚РµСЃС‚С‹ + live) |

Unresolved (РЅРµ Р±Р»РѕРєРёСЂСѓСЋС‚): U1 provenance РґР»СЏ Р±СѓРґСѓС‰РµРіРѕ computed-path; U3 bounds В«2025 CEВ» Сѓ today. (U2 вЂ” C2 вЂ” Р·Р°РєСЂС‹С‚).

### 7.2 ADR_ARKAIM_MEDIA_BOUNDARY (docs/ADR/, 2026-09-09)
РџРѕ MEDIA_DIRECTION_FOUNDATION Рё M4.1-РѕС‚С‡С‘С‚Сѓ вЂ” РїСЂРёРЅСЏС‚ РІР»Р°РґРµР»СЊС†РµРј (GO РЅР° MD-Р»РёРЅРёСЋ). РЎРј. В§3 РІС‹С€Рµ (5 Decisions + РёРЅРІР°СЂРёР°РЅС‚С‹ + findings MB-1вЂ¦MB-5). Р РµР°Р»РёР·РѕРІР°РЅРѕ: РіСЂР°РЅРёС†Р° Р·Р°С„РёРєСЃРёСЂРѕРІР°РЅР° РґРѕРєСѓРјРµРЅС‚Р°Р»СЊРЅРѕ (MD-1), РєРѕРЅС‚СЂР°РєС‚ MediaPlan (MD-3), bootstrap Media-СЂРµРїРѕ (M4.1вЂ“M4.2.2 С‡Р°СЃС‚РёС‡РЅРѕ). РќРµ СЂРµР°Р»РёР·РѕРІР°РЅРѕ: С„РёР·РёС‡РµСЃРєРёР№ РІС‹РЅРѕСЃ РІСЃРµРіРѕ СЃС‚РµРєР° (B1 pipeline РѕСЃС‚Р°С‘С‚СЃСЏ РІ РђСЂРєР°РёРјРµ РґРѕ MD-5), РґРµ-РїСѓР±Р»РёРєР°С†РёСЏ /comfyui/* (D-5), С‡РёСЃС‚РєР° GenerationParams (MB-3).

### 7.3 ADR_MEDIA_PLAN_V0 (docs/ADR/, 2026-09-11)
**РЎС‚Р°С‚СѓСЃ: ACCEPTED** (10 owner-decisions). РљР»СЋС‡РµРІРѕРµ: MediaPlan вЂ” РґРѕРјРµРЅРЅС‹Р№ РєРѕРЅС‚СЂР°РєС‚ Р±РµР· execution-СЃРµРјР°РЅС‚РёРєРё (BANNED 20 РїРѕР»РµР№ РІРєР». quality); negative_constraints вЂ” СЃРјС‹СЃР»РѕРІРѕРµ РїРѕР»Рµ; provenance+lineage РѕР±СЏР·Р°С‚РµР»СЊРЅС‹; ExecutionDispatch вЂ” РІСЂРµРјРµРЅРЅС‹Р№ РјРѕСЃС‚ (REMOVE IN MD-5); PA-F1 Р·Р°РєСЂС‹С‚ РЅР° СѓСЂРѕРІРЅРµ РїР»Р°РЅР°; frontend РЅРµ РјРµРЅСЏРµС‚СЃСЏ; РІРµСЂСЃРёРѕРЅРёСЂРѕРІР°РЅРёРµ 0.1.0 + JSON-Schema; РїРѕСЂСЏРґРѕРє MD-3.1в†’3.2в†’3.3 СЃРѕ STOP РЅР° РєР°Р¶РґРѕРј; STRICTLY FORBIDDEN-СЃРїРёСЃРѕРє (MD-4 РІ scope MD-3 Р±С‹Р» Р·Р°РїСЂРµС‰С‘РЅ вЂ” С‚РµРїРµСЂСЊ MD-4 РёРґС‘С‚ СЃРІРѕРёРј С‡РµСЂРµРґРѕРј РїРѕ РѕС‚РґРµР»СЊРЅС‹Рј GO). Р РµР°Р»РёР·РѕРІР°РЅРѕ: РїРѕР»РЅРѕСЃС‚СЊСЋ (MD-3 CLOSED).

### 7.4 ADR M8.1 (РґРѕРєСѓРјРµРЅС‚-СЂРµС€РµРЅРёРµ, РЅРµ РІ docs/ADR/)
`docs/M8_1_ARCHITECTURE_DECISION.md` вЂ” PRESENT-СЃРµРјР°РЅС‚РёРєР° (HYPOTHESIS-РёСЃРїСЂР°РІР»РµРЅРёРµ, computed path РІРјРµСЃС‚Рѕ relation). Р РµР°Р»РёР·РѕРІР°РЅРѕ РІ engine (E2 ADR_TEMPORAL). РљР°РЅРѕРЅРёР·РёСЂРѕРІР°РЅРѕ ADR_TEMPORAL Decision A/D.

### 7.5 Р—Р°РјРѕСЂРѕР¶РµРЅРЅС‹Рµ Architecture Decisions РІР»Р°РґРµР»СЊС†Р° (СѓРїРѕРјСЏРЅСѓС‚С‹ ADR_MEDIA_BOUNDARY Decision 3)
Assetв‰ File, Capabilityв‰ Workflow, Providerв‰ Model, Providerв‰ Backend, Workflowв‰ Node Graph, ComfyUIв‰ Agent, LLM Р±РµР· РїСЂСЏРјРѕРіРѕ РґРѕСЃС‚СѓРїР° Рє ComfyUI, Agent РЅРµ СѓРїСЂР°РІР»СЏРµС‚ ComfyUI РЅР°РїСЂСЏРјСѓСЋ, PromptBuilder РЅРµ РІС‹Р±РёСЂР°РµС‚ capability, media-execution-backend РЅРµ РІС…РѕРґРёС‚ РІ domain logic, core media-agnostic вЂ” В«Р·Р°С„РёРєСЃРёСЂРѕРІР°РЅС‹ Р·РґРµСЃСЊ РІРїРµСЂРІС‹Рµ РєР°Рє РєР°РЅРѕРЅВ».

### 7.6 Owner-СЂРµС€РµРЅРёСЏ MD-4 (M4.1-РѕС‚С‡С‘С‚ В§2)
Р’Р°СЂРёР°РЅС‚ A (РјРёРЅРёРјР°Р»СЊРЅС‹Р№ bootstrap); Quality РјС‘СЂС‚РІ; Film Studio С†РµР»РёРєРѕРј РІ Arkaim; СЂРµРїРѕ arkaim-media СЂСЏРґРѕРј; media_id СЂР°Р·СЂРµС€С‘РЅ РЅР°СЂСѓР¶Сѓ; shot_assembler РЅРµ С‡РёРЅРёС‚СЊ (D-2); ExecutionDispatch в‰  РїРѕСЃС‚РѕСЏРЅРЅС‹Р№ API (REMOVE IN MD-5). Р РµС€РµРЅРёСЏ M4.2.1: Q1 SD-stub РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ; Q2 quality РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ; Q3 РїР°РєРµС‚ `media/`.

---

## 8. Current Git State

### 8.1 arkaim

| РџР°СЂР°РјРµС‚СЂ | Р¤Р°РєС‚ |
|---|---|
| Branch | `master` |
| HEAD | `8aef0f9` В«fix: add missing .github and pre-commit config to restore commitВ» (2026-09-24) |
| Remote | origin в†’ https://github.com/Ovladimirovich/arkaim.git |
| РўРµРіРё/СЃС‚СЌС€Рё | РЅРµС‚ / РїСѓСЃС‚Рѕ |
| Working tree | **CLEAN** (С‚РѕР»СЊРєРѕ CRLF noise РІ `core/DEVELOPER_GUIDE.md`, `core/PROJECT_BIBLE/README.md` вЂ” pre-existing; genome/history/index.json вЂ” Р°РІС‚РѕР·Р°РїРёСЃСЊ) |
| Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РІРµС‚РєРё | `fresh-start` (`48c19c9`) вЂ” reference; `g0-clean` вЂ” СЃР»РёС‚ РІ master (`57d85f0`); `security-fix` вЂ” РєРѕРґ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ РІ `7c8ab27`; `push-test-*` вЂ”еЋ†еЏІРЅС‹Рµ |

**РџРѕСЃР»РµРґРЅРёРµ С‚РµРјР°С‚РёС‡РµСЃРєРёРµ РєРѕРјРјРёС‚С‹ (РЅРѕРІРµРµ в†’ СЃС‚Р°СЂРµРµ):**
- `8aef0f9` fix: add missing .github and pre-commit config
- `7c8ab27` feat: restore orphaned security-fix code (F1-F6, MD-1..MD-6, C2) вЂ” 276 С„Р°Р№Р»РѕРІ
- `59ae5c6` docs: F-12 closure вЂ” FUNCTIONALLY ACCEPTED / CLOSED
- `c022e77` feat(film-studio): F-12 production DB repair вЂ” quality column migration
- `b4e6893` feat(frontend): F6 polish вЂ” help page, a11y, E2E scenarios, eslint cleanup
- `a090ec8` feat(frontend): finalize F5 вЂ” xray, history, WS toast, 5 pages committed
- `28514fb` feat(frontend): finalize F4
- `4be2a40` feat(md-6): legacy cleanup + contract hardening
- `57d85f0` Merge branch g0-clean (G0: OpenAI-compatible API)
- `dc59011` feat(G0): model discovery + OpenAI-compatible API
- (СЂР°РЅРµРµ: MD-Р»РёРЅРµР№РєР°, temporal, World Explorer, Community Рё С‚.Рґ.)

**РЎС‚Р°С‚СѓСЃ frontend:** F1вЂ“F6 РІРµСЃСЊ РєРѕРґ Р·Р°РєРѕРјРјРёС‡РµРЅ РІ master. 25 СЃС‚СЂР°РЅРёС†, 37 test-С„Р°Р№Р»РѕРІ, 134 unit + 14 E2E PASS.

### 8.2 arkaim-media

Branch `master`; HEAD `f0327cd` В«docs(medium): accept MEDIA_CONTRACT v1.0 вЂ” С„Р°РєС‚РёС‡РµСЃРєРё СЂРµР°Р»РёР·РѕРІР°РЅ Рё РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏВ» (СЂРѕРґРёС‚РµР»СЊ `c942043`, РґР°Р»РµРµ `0d10396`в†’`ca2c3a5`в†’`4f60229`в†’`4ccfd8e`в†’`6f39b76`в†’`0256140`в†’`d4bcef2`в†’`8e465cc`). РџРѕР»РЅС‹Р№ MD-4 РїРѕРґСЌС‚Р°РїС‹ M4.1вЂ“M4.4 Р·Р°РєСЂС‹С‚С‹, MEDIA_CONTRACT v1.0 ACCEPTED. Р Р°Р±РѕС‡РёР№ С‡РёСЃС‚С‹Р№ (С‚РѕР»СЊРєРѕ __pycache__, РёРіРЅРѕСЂРёСЂСѓРµС‚СЃСЏ). Remote РЅРµС‚ (Р»РѕРєР°Р»СЊРЅС‹Р№ СЂРµРїРѕР·РёС‚РѕСЂРёР№).

### 8.3 Р Р°СЃС…РѕР¶РґРµРЅРёСЏ РґРѕРєСѓРјРµРЅС‚Р°С†РёРё Рё РєРѕРґР°

РЎРј. В§14.

---

## 9. Current Contracts

### 9.1 РљРѕРЅС‚СЂР°РєС‚ Arkaim в†” Media (РІРЅРµС€РЅРёР№, v1.0 DRAFT)

| РђСЃРїРµРєС‚ | Р¤Р°РєС‚ |
|---|---|
| Р’Р»Р°РґРµР»РµС† | РЎРѕРІРјРµСЃС‚РЅРѕ: РґРѕРєСѓРјРµРЅС‚ РІ arkaim-media/docs/MEDIA_CONTRACT.md; MediaPlan-С‡Р°СЃС‚СЊ вЂ” Р±Р°Р№С‚-РІ-Р±Р°Р№С‚ Р°СЂРєР°РёРјСЃРєР°СЏ `SCHEMAS/MEDIA_PLAN.schema.json` (SHA256 `B52B7E7AвЂ¦50F635` вЂ” СЃРІРµСЂРµРЅРѕ) |
| РўСЂР°РЅСЃРїРѕСЂС‚ | HTTP POST `/v1/generate` (РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ endpoint; СЃРёРЅС…СЂРѕРЅРЅС‹Р№) |
| Р”Р°РЅРЅС‹Рµ РІРЅРёР· | `plan` (MediaPlan v0.1.0) + `execution` (СЂРѕРІРЅРѕ 5 РїРѕР»РµР№: media_kind, size, preferred_backend, duration_sec, fps) |
| Р”Р°РЅРЅС‹Рµ РІРІРµСЂС… | `media_id`, kind, bytes_b64, content_format, backend, workflow_used? |
| **РќР• РїРµСЂРµРґР°С‘С‚СЃСЏ (С„РёР·РёС‡РµСЃРєРё Р·Р°РїСЂРµС‰РµРЅРѕ СЃС…РµРјР°РјРё additionalProperties:false)** | quality, model, checkpoint, steps, cfg, sampler, seed, workflow, node_graph, provider (в†’ preferred_backend), comfyui, loras, denoise, negative РєР°Рє execution-РїРѕР»Рµ |
| РћС€РёР±РєРё | 400 INVALID_REQUEST / 422 UNSUPPORTED_MEDIA_KINDВ·UNSUPPORTED_SIZEВ·BACKEND_NOT_AVAILABLE / 429 OVERLOADED / 500 GENERATION_FAILED / 504 GENERATION_TIMEOUT; С‚РµР»Рѕ `{error:{code,message,retryable}}` |
| Р’СЂРµРјРµРЅРЅС‹Р№ СЌР»РµРјРµРЅС‚ | execution-РєРѕРЅРІРµСЂС‚ = СЃРµСЂРёР°Р»РёР·Р°С†РёСЏ Р¶РёРІРѕРіРѕ ExecutionDispatch (dispatch.py:42вЂ“64) вЂ” В«РЅРµ РЅРѕРІС‹Р№ РґРёР·Р°Р№РЅВ»; СѓРјРёСЂР°РµС‚ РІ MD-5 |
| РЎС‚Р°С‚СѓСЃ | **ACCEPTED & CLOSED** (arkaim-media `f0327cd` вЂ” В«accept MEDIA_CONTRACT v1.0В»). Р”Рµ-С„Р°РєС‚Рѕ РёСЃРїРѕР»СЊР·РѕРІР°Р»СЃСЏ СЃ M4.3 (MediaClient bridge). |

### 9.2 Р’РЅСѓС‚СЂРµРЅРЅРёРµ РєРѕРЅС‚СЂР°РєС‚С‹ РђСЂРєР°РёРјР° (Р·Р°РјРѕСЂРѕР¶РµРЅРЅС‹Рµ)

| РљРѕРЅС‚СЂР°РєС‚ | Р“РґРµ | Р’Р»Р°РґРµР»РµС† |
|---|---|---|
| MediaPlan v0 (pydantic extra=forbid + BANNED) | core/CORE/media_plan/schemas.py | Arkaim (MD-3 CLOSED) |
| SceneContext (extras: temporal/source_refs/integrity) | visual/scene_context.py + visual_context.py | Arkaim (MD-2 CLOSED) |
| 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E (РѕС‚РІРµС‚С‹ byte-identical) | routes/visual.py, assets.py, film_studio.py | Arkaim; РїРѕРґРјРµРЅР° С†РµРїРё вЂ” С‚РѕР»СЊРєРѕ Р·Р° DI |
| Temporal API (14 РїСѓС‚РµР№: 7 M4/M8 + 7 M10.2) | routes/temporal.py, temporal_updates.py | Arkaim (B1/C1/C2 done) |
| AssetStorage/С„Р°Р№Р»С‹ Р°СЃСЃРµС‚РѕРІ | visual_assets/storage.py + data/ | **Arkaim вЂ” РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ РІР»Р°РґРµР»РµС†** (РєРѕРЅС‚СЂР°РєС‚ В§6) |
| Frontendв†”Backend | OpenAPI-СЃР»РµРїРѕРє 290 РїСѓС‚РµР№ (web-v2/contracts/) + RBAC-РјР°С‚СЂРёС†Р° 298; F1вЂ“F6 ACCEPTED (25 СЃС‚СЂР°РЅРёС†), backend 0 РёР·РјРµРЅРµРЅРёР№ | backend вЂ” РёСЃС‚РѕС‡РЅРёРє РёСЃС‚РёРЅС‹ |
| G0 OpenAI-compatible | /v1/models, /v1/chat/completions, /providers/health | runtime/core/dto/openai.py + main.py + provider_registry.py | Arkaim (CLOSED, merge `57d85f0`) |
| LLM-С†РµРїСЊ GigaChatв†’OpenRouter | runtime/core/provider_registry.py + core/CORE/providers/gigachat.py | Arkaim (LLM в‰  media) |

### 9.3 Р“СЂР°РЅРёС†С‹ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕСЃС‚Рё Рё РІСЂРµРјРµРЅРЅС‹Рµ РєРѕРЅС‚СЂР°РєС‚С‹

- **shot_assembler (Arkaim)** С‡РёС‚Р°РµС‚ Р°СЃСЃРµС‚С‹ РїРѕ СЃС‹СЂС‹Рј РїСѓС‚СЏРј СЃ РґРёСЃРєР° (РЅРµ С‡РµСЂРµР· storage-API) вЂ” СЂР°Р±РѕС‚Р°РµС‚, РїРѕРєР° РѕР±Р° РїСЂРѕРµРєС‚Р° РЅР° РѕРґРЅРѕР№ РјР°С€РёРЅРµ; **Р·Р°РґРѕРєСѓРјРµРЅС‚РёСЂРѕРІР°РЅРЅС‹Р№ РѕР±С…РѕРґ (D-2), РќР• С‡РёРЅРёС‚СЃСЏ РґРѕ MD-5** (РєРѕРЅС‚СЂР°РєС‚ В§6, owner В§16-6).
- **queue/async/batch/regenerate** вЂ” 4 Р¶РёРІС‹С… РїСѓС‚Рё Р‘Р•Р— РїР»Р°РЅР° (chapter/scene_id/overrides; style/quality) вЂ” РјРёРіСЂР°С†РёСЏ Р±С‹Р»Р° Р·Р°РїСЂРµС‰РµРЅР° РІ MD-3, РѕСЃС‚Р°С‘С‚СЃСЏ РѕС‚РґРµР»СЊРЅС‹Рј СЂРµС€РµРЅРёРµРј РїРѕСЃР»Рµ MD-4 (MD4_PRE В§9).
- **`/comfyui/*` Рё `/providers/*` СЂРѕСѓС‚С‹ РђСЂРєР°РёРјР°** вЂ” РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹ (MD-5, test_media_boundary РїРѕРґС‚РІРµСЂР¶РґР°РµС‚ РѕС‚СЃСѓС‚СЃС‚РІРёРµ РїСѓС‚РµР№). РљРѕРґ СѓРґР°Р»С‘РЅ РёР· routes/, stub РѕСЃС‚Р°РІР»РµРЅ РІ providers/image/comfyui.py. MediaClient bridge СЂР°Р±РѕС‚Р°РµС‚ С‡РµСЂРµР· adc_deps.
- **Genome-history churn:** РєР°Р¶РґС‹Р№ Р·Р°РїСѓСЃРє Р±СЌРєРµРЅРґР°/С‚РµСЃС‚РѕРІ РґРѕРїРёСЃС‹РІР°РµС‚ СЃРЅР°РїС€РѕС‚ РІ `core/CORE/genome/history/index.json` + РїР»РѕРґРёС‚ С„Р°Р№Р»С‹ GENOME/history вЂ” runtime-Р°СЂС‚РµС„Р°РєС‚, В«РЅРµ sourceВ», РЅРѕ РїР°С‡РєР°РµС‚ git-СЃС‚Р°С‚СѓСЃ (РЅР°Р±Р»СЋРґРµРЅРёРµ F3 В§12-4).

---

## 10. Current Visual Production Project State (arkaim-media)

| Р’РѕРїСЂРѕСЃ | Р¤Р°РєС‚ |
|---|---|
| Р—Р°С‡РµРј СЃРѕР·РґР°РЅ | РСЃРїРѕР»РЅРёС‚РµР»СЊ РіРµРЅРµСЂР°С†РёРё: РђСЂРєР°РёРј РїСЂРѕРёР·РІРѕРґРёС‚ СЃРјС‹СЃР» (Scene Context в†’ Media Plan), Media РёСЃРїРѕР»РЅСЏРµС‚ (workflow в†’ provider в†’ backend в†’ bytes). РћСЃРЅРѕРІР°: ADR_ARKAIM_MEDIA_BOUNDARY; С†РµР»СЊ вЂ” РІС‹РЅРµСЃС‚Рё Р·РЅР°РЅРёРµ ComfyUI РёР· СЏРґСЂР° РђСЂРєР°РёРјР° (MB-1) |
| Р§С‚Рѕ СЃСѓС‰РµСЃС‚РІСѓРµС‚ | РљРѕРЅС‚СЂР°РєС‚ v1.0 DRAFT (4 СЃС…РµРјС‹ + 15 РєРѕРЅС‚СЂР°РєС‚РЅС‹С… С‚РµСЃС‚РѕРІ); РїР°РєРµС‚ `media/` (config.py + image/{__init__,comfyui}.py); workflows/default.json; 27 ComfyUI-С‚РµСЃС‚РѕРІ; README/pyproject/gitignore |
| РџСЂРѕРІР°Р№РґРµСЂС‹ СЂРµР°Р»СЊРЅРѕ РёСЃРїРѕР»СЊР·СѓРµРјС‹Рµ | **РџРµСЂРµРЅРµСЃС‘РЅ: ComfyUIProvider** (media/image/comfyui.py). РќР• РїРµСЂРµРЅРµСЃРµРЅС‹: MockImage, SVGTemplate (в†’M4.2.4), StableDiffusion (РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЃСЏ, Q1), ImageSequenceVideo + MockVideo (в†’M4.2.3), С†РµРїРё (в†’M4.2.4). **РђСЂРєР°РёРј-С†РµРїСЊ РІ adc_deps РїРѕ-РїСЂРµР¶РЅРµРјСѓ СЂР°Р±РѕС‚Р°РµС‚ РЅР° РЎРўРђР РћРњ СЃС‚РµРєРµ** (ComfyUI РёР· core/CORE/providers) вЂ” РґРІРѕР№РЅР°СЏ РєРѕРїРёСЏ РїСЂРѕРІР°Р№РґРµСЂР° СЃРѕР·РЅР°С‚РµР»СЊРЅР° РґРѕ MD-5 (РјР°РЅРґР°С‚ 17: legacy РЅРµ СѓРґР°Р»СЏС‚СЊ) |
| Р“РґРµ workflows | `arkaim-media/workflows/default.json` (SHA256 = Р°СЂРєР°РёРјСЃРєРѕРјСѓ `core/GENOME/workflows/default.json`, Р±Р°Р№С‚-РІ-Р±Р°Р№С‚; РїСЂРѕРІРµСЂРµРЅРѕ СЌС‚РёРј Р°СѓРґРёС‚РѕРј). РђСЂРєР°РёРј-РєРѕРїРёСЏ РѕСЃС‚Р°С‘С‚СЃСЏ РґРѕ MD-5 |
| Р§С‚Рѕ РїРµСЂРµРЅРµСЃРµРЅРѕ | РўРѕР»СЊРєРѕ 5 С„Р°Р№Р»РѕРІ M4.2.2 (СЃРј. В§6.5). РђСЂРєР°РёРј-side РЅРµ РјРµРЅСЏР»СЃСЏ |
| Р§С‚Рѕ РІ РёСЃС…РѕРґРЅРѕРј РїСЂРѕРµРєС‚Рµ | Р’РµСЃСЊ РѕСЃС‚Р°Р»СЊРЅРѕР№ РёСЃРїРѕР»РЅРёС‚РµР»СЊРЅС‹Р№ СЃР»РѕР№: pipeline, storage, queue, film_studio (РІРєР»СЋС‡Р°СЏ ffmpeg-СЃР±РѕСЂРєСѓ), providers/{mock,svg,SD,video}, media_plan/dispatch |
| РљРѕРЅС‚СЂР°РєС‚ СЃ РѕСЃРЅРѕРІРЅС‹Рј РїСЂРѕРµРєС‚РѕРј | MEDIA_CONTRACT.md v1.0 (В§9.1): РїР»Р°РЅ+РєРѕРЅРІРµСЂС‚ в†’ Р±Р°Р№С‚С‹+media_id; Arkaim РІР»Р°РґРµРµС‚ Р°СЃСЃРµС‚Р°РјРё; Media stateless |
| РЎРѕР·РЅР°С‚РµР»СЊРЅРѕ РќР• РїРµСЂРµРЅРѕСЃРёС‚СЃСЏ | quality-РјРµС…Р°РЅРёРєР° (Q2); StableDiffusion (Q1); GigaChat/LLM (K7); pollinations.pyc/registry.py (K6); pipeline/storage/queue (РІР°СЂРёР°РЅС‚ B РѕС‚РІРµСЂРіРЅСѓС‚); Film Studio; frontend; audio; ComfyUI Agent v1 (РЅРµ РїРѕРіР»РѕС‰Р°РµС‚СЃСЏ) |
| Р”РµС„РµРєС‚С‹, РїРµСЂРµРЅРµСЃС‘РЅРЅС‹Рµ РєР°Рє РµСЃС‚СЊ | seed = hash(prompt) (РЅРµРґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅ РјРµР¶РґСѓ СЂРµСЃС‚Р°СЂС‚Р°РјРё вЂ” РјР°РЅРґР°С‚ В«РЅРµ С‡РёРЅРёС‚СЊВ»); РїРµСЂРµС‡РёС‚С‹РІР°РЅРёРµ COMFYUI_URL РїСЂРё РєР°Р¶РґРѕРј РІС‹Р·РѕРІРµ (СЃРѕС…СЂР°РЅРµРЅРѕ) |

---

## 11. Deferred / Rejected Work

### 11.1 РћС‚РІРµСЂРіРЅСѓС‚С‹Рµ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Рµ РІР°СЂРёР°РЅС‚С‹ (РїРѕ ADR/Р°СѓРґРёС‚Р°Рј)

| Р’Р°СЂРёР°РЅС‚ | РџРѕС‡РµРјСѓ РѕС‚РІРµСЂРіРЅСѓС‚ | РСЃС‚РѕС‡РЅРёРє |
|---|---|---|
| РџСЂРѕРІР°Р№РґРµСЂС‹ РѕСЃС‚Р°СЋС‚СЃСЏ РІ core РђСЂРєР°РёРјР° | РЈР¶Рµ РїРѕРєР°Р·Р°Р»Рѕ С†РµРЅСѓ: 3 СЃР»РѕСЏ РІРёР·СѓР°Р»Р°, provider-СЃРїРµС†РёС„РёРєР° РІ РґРѕРјРµРЅРЅС‹С… СЃС…РµРјР°С… | ADR_MEDIA_BOUNDARY Decision 1 Rejected |
| Arkaimв†’ComfyUI HTTP СЃ workflow-РїР°СЂР°РјРµС‚СЂР°РјРё | РЈС‚РµС‡РєР° knowledge РѕР± РёСЃРїРѕР»РЅРµРЅРёРё РІ РђСЂРєР°РёРј | С‚Р°Рј Р¶Рµ |
| Present РєР°Рє РјРµС‚Р°РґР°РЅРЅС‹Рµ РІРЅРµ РіСЂР°С„Р° | today РЅРµРІРёРґРёРј РґР»СЏ graph-Р°Р»РіРѕСЂРёС‚РјРѕРІ; С‚РѕС‡РєР° СЃС‚Р°СЂС‚Р° В«РёР· РЅРёРѕС‚РєСѓРґР°В» | ADR_TEMPORAL Decision A Rejected |
| Present РєР°Рє РёСЃС‚РѕСЂРёС‡РµСЃРєРёР№ СѓР·РµР» СЃ relation Рє arkaim | Р›РѕР¶РЅР°СЏ РёСЃС‚РѕСЂРёС‡РЅРѕСЃС‚СЊ; РЅР°СЂСѓС€Р°РµС‚ Р·Р°РїСЂРµС‚ | С‚Р°Рј Р¶Рµ |
| DEVELOPS_FROM РєР°Рє РєР°РЅРѕРЅ РѕСЃРё / РЅРѕРІС‹Р№ С‚РёРї CONNECTS_TO / Р±РёРґРёСЂРµРєС†РёРѕРЅРЅС‹Рµ СЂС‘Р±СЂР° | РРЅС‚РµСЂРїСЂРµС‚Р°С†РёСЏ РІРјРµСЃС‚Рѕ РїРѕСЂСЏРґРєР°; РЅРѕРІС‹Рµ СЃСѓС‰РЅРѕСЃС‚Рё; РґСѓР±Р»Рё | ADR_TEMPORAL Decision B Rejected |
| Provenance РІ РѕС‚РґРµР»СЊРЅРѕРј СЂРµРµСЃС‚СЂРµ / С‚РѕР»СЊРєРѕ SourceLevel / UI-РІС‹С‡РёСЃР»РµРЅРёРµ | Р Р°СЃСЃРёРЅС…СЂРѕРЅ; РїРѕС‚РµСЂСЏ СЃРµРјР°РЅС‚РёРєРё; РЅР°СЂСѓС€РµРЅРёРµ РёРЅРІР°СЂРёР°РЅС‚Р° | ADR_TEMPORAL Decision C Rejected |
| РўСЂРµС‚РёР№ anchor-СѓР·РµР» / РѕСЃС‚Р°РІРёС‚СЊ РѕР±Р° / СѓРґР°Р»РёС‚СЊ ArkaimAnchor-dataclass | РќРѕРІР°СЏ РјРёРіСЂР°С†РёСЏ; РґРІРѕР№РЅРѕРµ Р·РЅР°РЅРёРµ; РїРѕС‚РµСЂСЏ curated-provenance | ADR_TEMPORAL Decision D Rejected |
| MD-4 РІР°СЂРёР°РЅС‚ B (РїРѕР»РЅС‹Р№ РїРµСЂРµРЅРѕСЃ pipeline+storage+queue+ffmpeg) | РќР°СЂСѓС€РµРЅРёРµ 3 РёРЅРІР°СЂРёР°РЅС‚РѕРІ MD-3 СЃСЂР°Р·Сѓ; byte-identical РЅРµРІРѕР·РјРѕР¶РµРЅ | MD4_PRE В§11 |
| Media С…СЂР°РЅРёС‚ С„Р°Р№Р»С‹ Р°СЃСЃРµС‚РѕРІ (Р°Р»СЊС‚РµСЂРЅР°С‚РёРІР° v1) | Р›РѕРјР°РµС‚ 6 СЂР°Р±РѕС‚Р°СЋС‰РёС… СЂРѕСѓС‚РѕРІ С‡С‚РµРЅРёСЏ + frontend | MD4_PRE В§8 |
| РџРµСЂРµРЅРѕСЃ quality РІ Media | РћР¶РёРІРёС‚ РјС‘СЂС‚РІС‹Р№ СЃР»РѕРІР°СЂСЊ; owner В«quality РјС‘СЂС‚РІВ»; standard==DEFAULT_WF в†’ Р±Р°Р№С‚С‹ РёРґРµРЅС‚РёС‡РЅС‹ Рё Р±РµР· РЅРµРіРѕ | M4.2.1 K5/Q2 |

### 11.2 РћС‚Р»РѕР¶РµРЅРЅС‹Рµ Р·Р°РґР°С‡Рё (РґРѕСЂРѕРіР°)

MD-5 (adapter РЅР° РєРѕРЅС‚СЂР°РєС‚Рµ; РґРµ-РїСѓР±Р»РёРєР°С†РёСЏ /comfyui/*; СѓРґР°Р»РµРЅРёРµ ExecutionDispatch/legacy-РїСЂРѕРµРєС†РёР№/GENOME-workflows-РєРѕРїРёРё; D-6 СЂРµСЌРєСЃРїРѕСЂС‚; B1 plan-only pipeline) вЂ” **CLOSED (MD-5 + MD-7)**. C2 вњ… вЂ” **CLOSED** (commit `f1d5d60`). D-10 вњ… вЂ” **CLOSED**. F4+ С„СЂРѕРЅС‚ вЂ” **CLOSED (F4+F5+F6)**. audio-РґРѕРјРµРЅ (extension point, СЃС…РµРјР° РЅРµ РѕРїСЂРµРґРµР»СЏРµС‚СЃСЏ); quality-СЂРµС€РµРЅРёРµ (D-7, СѓРґР°Р»РµРЅРёРµ/РґРµРїСЂРµРєР°РЅРёРµ GenerationParams.quality); negative-to-provider (MP-F2); video-РїР»Р°РЅ РІ Route C (D-3, СЃРёРіРЅР°С‚СѓСЂР° pipeline); persistence M10.2-РёСЃС‚РѕСЂРёРё; M25 Experience; РєРѕРЅСЃРѕР»РёРґР°С†РёСЏ СЃР»РѕРІР°СЂРµР№ СЃС‚РёР»РµР№ (MP-F8, D-8); async/queue/batch/regenerate РјРёРіСЂР°С†РёСЏ (D-4); РїРµСЂРµРёРјРµРЅРѕРІР°РЅРёРµ measurement-РєР»Р°СЃСЃР° SceneContext (visual_models.py:7).

### 11.3 Р—Р°РїСЂРµС‰С‘РЅРЅС‹Рµ РЅР°РїСЂР°РІР»РµРЅРёСЏ (РґРµР№СЃС‚РІСѓСЋС‰РёРµ)

РР· ADR_MEDIA_PLAN_V0 Decision 7 (STRICTLY FORBIDDEN РґР»СЏ MD-3 вЂ” РёСЃС‚РѕСЂРёС‡РµСЃРєРёРµ, РЅРѕ РґСѓС… СЃРѕС…СЂР°РЅС‘РЅ): РїР°СЂР°Р»Р»РµР»СЊРЅС‹Р№ SceneContext; РїР°СЂР°Р»Р»РµР»СЊРЅР°СЏ prompt-Р°СЂС…РёС‚РµРєС‚СѓСЂР°; РѕР¶РёРІР»РµРЅРёРµ quality; РёР·РјРµРЅРµРЅРёРµ provider semantics РІРЅРµ adapter/dispatch. РР· ADR_MEDIA_BOUNDARY РёРЅРІР°СЂРёР°РЅС‚РѕРІ (В§3). РР· MD4_PRE В§14 (scope MD-4): quality-РѕР¶РёРІР»РµРЅРёРµ; negative-to-provider РІ РђСЂРєР°РёРјРµ; video-РїР»Р°РЅ РґРѕ generate_video; РїСЂР°РІРєРё MediaPlan/SceneContext/WorldModel/temporal; СѓРґР°Р»РµРЅРёРµ legacy; РїРµСЂРµРЅРѕСЃС‹ queue/batch/regenerate/async; frontend; audio; РёР·РјРµРЅРµРЅРёРµ 5 РјР°СЂС€СЂСѓС‚РѕРІ; film_studio-РґРѕРјРµРЅ; СЃР»РѕРІР°СЂРё СЃС‚РёР»РµР№; ComfyUI Agent v1.

---

## 12. Technical Debt

| ID | Debt | Р“РґРµ | РџРѕС‡РµРјСѓ СЃСѓС‰РµСЃС‚РІСѓРµС‚ | РљРѕРіРґР° СЂРµС€Р°РµС‚СЃСЏ | РўСЂРѕРіР°С‚СЊ СЃРµР№С‡Р°СЃ? |
|----|------|-----|-------------------|-----------------|-----------------|
| D-1 | ExecutionDispatch-РјРѕСЃС‚ | core/CORE/media_plan/dispatch.py вЂ” **С„Р°Р№Р» СѓРґР°Р»С‘РЅ** (MD-5, commit `d73d29a`) | РџСЂРѕРєСЃРё-РјРѕСЃС‚ СѓРґР°Р»С‘РЅ; MediaClient bridge СЂР°Р±РѕС‚Р°РµС‚ С‡РµСЂРµР· adc_deps | вњ… **CLOSED MD-5** | вЂ” |
| D-2 | shot_assembler СЃС‹СЂС‹Рµ РїСѓС‚Рё | core/CORE/film_studio/shot_assembler.py:37вЂ“46 | Р§РёС‚Р°РµС‚ С„Р°Р№Р»С‹ Р°СЃСЃРµС‚РѕРІ РјРёРјРѕ storage-API | MD-7+/РѕР±С‰РµРµ СЂРµС€РµРЅРёРµ | РќРµС‚ (owner В§16-6) |
| D-3 | Video-РїР»Р°РЅ Route C РЅРµ РґРѕС…РѕРґРёС‚ РґРѕ generate_video | routes/assets.py (video-РІРµС‚РєР°) + pipeline.generate_video (СЃРёРіРЅР°С‚СѓСЂР° Р±РµР· plan) | РЎРёРіРЅР°С‚СѓСЂСѓ РјРµРЅСЏС‚СЊ Р·Р°РїСЂРµС‰РµРЅРѕ РІ MD-3 | РћС‚РґРµР»СЊРЅРѕРµ СЂРµС€РµРЅРёРµ (Р·Р°РІРёСЃРёС‚ РѕС‚ MVP) | РќРµС‚ |
| D-4 | Queue/async/batch/regenerate Р±РµР· РїР»Р°РЅР° | visual_assets/queue.py:44вЂ“62; assets.py:411 | РњРёРіСЂР°С†РёСЏ Р·Р°РїСЂРµС‰РµРЅР° РІ MD-3 | РђСЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ СЂРµС€РµРЅРёР№, РЅРµ Р·Р°РґР°С‡Р° | РќРµС‚ |
| D-5 | /comfyui/* РїСѓР±Р»РёС‡РЅС‹Рµ СЂРѕСѓС‚С‹ | routes/visual.py вЂ” **РґРµРїСѓР±Р»РёРєРѕРІР°РЅС‹** (MD-5, test_media_boundary РїРѕРґС‚РІРµСЂР¶РґР°РµС‚) | Backend-СѓРїСЂР°РІР»РµРЅРёРµ РґРµРїСѓР±Р»РёРєРѕРІР°РЅРѕ | вњ… **CLOSED MD-5/MD-7** | вЂ” |
| D-6 | visualization/__init__:18 СЂРµСЌРєСЃРїРѕСЂС‚ РїСЂРѕРІР°Р№РґРµСЂРѕРІ | core/CORE/visualization/__init__.py | Р”РѕРјРµРЅ-СЃР»РѕР№ Р·РЅР°РµС‚ РїСЂРѕРІР°Р№РґРµСЂРЅС‹Рµ С‚РёРїС‹ (B4) | MD-7-cleanup | РќРµС‚ |
| D-7 | GenerationParams.quality вЂ” РјС‘СЂС‚РІРѕРµ РїРѕР»Рµ | visual_assets/schemas.py:50 | РќРµ С‡РёС‚Р°РµС‚СЃСЏ runtime-РјР°СЂС€СЂСѓС‚Р°РјРё; MediaPlan BANNED_FIELDS СѓР¶Рµ РёСЃРєР»СЋС‡Р°РµС‚ | РћС‚РґРµР»СЊРЅРѕРµ СЂРµС€РµРЅРёРµ: СѓРґР°Р»РёС‚СЊ/РґРµРїСЂРµРєР°РЅРёСЂРѕРІР°С‚СЊ | РќРµС‚ |
| D-8 | РўСЂРё СЃР»РѕРІР°СЂСЏ СЃС‚РёР»РµР№ | visual_assets/prompt_builder.py (8 РїСЂРµСЃРµС‚РѕРІ), visualization, visual | РСЃС‚РѕСЂРёС‡РµСЃРєРёРµ СЃР»РѕРё | РћС‚РґРµР»СЊРЅРѕРµ СЂРµС€РµРЅРёРµ | РќРµС‚ |
| D-9 | F-12: film_studio.db вЂ” **РёСЃРїСЂР°РІР»РµРЅРѕ** (commit `c022e77`) | data/film_studio.db | ALTER TABLE ADD COLUMN quality РІС‹РїРѕР»РЅРµРЅ | вњ… **CLOSED F-12** | вЂ” |
| D-10 | SharedSettings: вњ… CLOSED (PROVIDER_CHAIN=gigachat,openrouter; THRESHOLD=3; COOLDOWN=60s) | runtime/.env + provider_registry.py | вЂ” | вњ… **CLOSED** | вЂ” |
| D-11 | test_assets_new_params Г—4 | runtime/tests/test_assets_new_params.py | `from runtime.core.routes...` вЂ” РјРѕРґСѓР»СЊ РЅРµРґРѕСЃС‚СѓРїРµРЅ РёР· pytest-cwd | РўРµСЃС‚-РёРЅС„СЂР°, РѕС‚РґРµР»СЊРЅРѕ | РќРµС‚ |
| D-12 | РњС‘СЂС‚РІС‹Рµ РёРјРїРѕСЂС‚С‹ providers.registry | narrative_engine/story/api_routes.py:243, research/{entity_extractor,source_searcher}.py, community/vk.py | providers/registry.py РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚; try/except-fallback | Cleanup | РќРµС‚ |
| D-13 | pollinations.pyc stale + stable_diffusion.py РЅРµ РІ DI | core/CORE/providers/image/__pycache__/pollinationsвЂ¦pyc; stable_diffusion.py | РЈРґР°Р»С‘РЅРЅС‹Рµ РїСЂРѕРІР°Р№РґРµСЂС‹ (963322a) РѕСЃС‚Р°РІРёР»Рё pyc; SD вЂ” Р·Р°РіР»СѓС€РєР° | Cleanup | РќРµС‚ |
| D-14 | Р’РёСЃСЏС‡Р°СЏ `__all__`-СЃС‚СЂРѕРєР° get_prompt_composer | runtime/core/adc_deps.py:~366 | Р¤СѓРЅРєС†РёСЏ РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚ (F-33-4) | Cleanup | РќРµС‚ |
| D-15 | Р›РµРіР°СЃРё-РїСЂРѕРјРїС‚-РїСЂРѕРµРєС†РёРё A/B/C/E (byte-frozen) | visualization/prompt_builder.py + visual_assets/prompt_builder.py | PA-F1: РєРѕРЅС‚СЂР°РєС‚ СЃРѕС…СЂР°РЅС‘РЅ | РќРµ С‚СЂРѕРіР°С‚СЊ | вЂ” |
| D-16 | C2: provenance РЅР° СЂС‘Р±СЂР°С… вЂ” **РРЎРџР РђР’Р›Р•РќРћ** | core/CORE/narrative_engine/temporal/relation.py:186вЂ“205 | `precedes()` СЃС‚Р°РІРёС‚ `ProvenanceCategory.DERIVED`; С‚РµСЃС‚ PASS | вњ… **CLOSED (f1d5d60 + 7c8ab27)** | вЂ” |
| D-17 | Genome-history churn РїСЂРё РєР°Р¶РґРѕРј Р·Р°РїСѓСЃРєРµ | core/CORE/genome/history/ (+ index.json) | Runtime-РїРѕРІРµРґРµРЅРёРµ СЃРЅР°РїС€РѕС‚РѕРІ | РћС‚РґРµР»СЊРЅРѕРµ СЂРµС€РµРЅРёРµ (.gitignore?) | РќРµС‚ |


---

## 13. Test State (С„Р°РєС‚РёС‡РµСЃРєРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ РЅР° HEAD `8aef0f9`)

Р’СЃРµ backend-РїСЂРѕРіРѕРЅС‹: `runtime/.venv`, `COMFYUI_URL=http://127.0.0.1:18188` (РѕС„Р»Р°Р№РЅ-Р·Р°РіР»СѓС€РєР°, РєСЂРѕРјРµ РѕС‚РјРµС‡РµРЅРЅРѕРіРѕ), pytest `-q`.

| Suite | Р¤Р°Р№Р»РѕРІ | Р РµР·СѓР»СЊС‚Р°С‚ |
|---|---|---|
| MD-3 (РєРѕРЅС‚СЂР°РєС‚+5 РјР°СЂС€СЂСѓС‚РѕРІ+deprecations) | 7 test_md3_* | **134 passed, 0 failed** |
| Temporal chunk (СЂР°СЃС€РёСЂРµРЅРЅС‹Р№) | temporal_model, temporal_reconstruction, m8_1, m9, m5, m8, temporal_routes | **237 passed, 0 failed** |
| MD2/M7/M10/M10.2 | test_md2_routes, test_m7_epoch_visual, test_m10_temporal_updates, test_m10_2_pending_updates_api | **74 passed, 0 failed** |
| Visual-family core | test_visual_conflict, test_visual_meaning, test_visual_archetype, test_genome, test_genome_narrative | **45 passed, 4 skipped** |
| Visual+assets+film+md2 chunk | test_visual_comfyui, test_visual_assets_provider_chain, test_visualization, test_assets_new_params, test_film_endpoints, test_md2_scene_context, test_md2_routes | **114 passed, 4 failed** (4 pre-existing `ModuleNotFoundError: runtime.core` вЂ” D-11) |
| arkaim-media (РїРѕР»РЅС‹Р№ suite) | pytest tests | **42 passed** (РїСЂРё РїРѕР»РЅРѕР№ Р¤РЎ) |
| arkaim-web-v2 (unit) | node scripts/run-tests.mjs | **134 passed, 0 failed** |
| arkaim-web-v2 (E2E) | playwright | **14 passed, 0 failed** (F6-scenarios.spec.ts) |
| G0 (OpenAI API) | test_g0.py | **12 passed, 0 failed** |
| ComfyUI-СЃРµСЂРІРµСЂ | GET :8188/system_stats | **HTTP 200** (Р¶РёРІ) |

**РС‚РѕРіРѕ:** backend test-С„Р°Р№Р»РѕРІ: **106**; frontend test-С„Р°Р№Р»РѕРІ: **37** (33 unit + 4 e2e). Pre-existing failures: С‚Рµ Р¶Рµ 4 `ModuleNotFoundError` (D-11) + РёСЃС‚РѕСЂРёС‡РµСЃРєРёРµ sandbox-РѕРіСЂР°РЅРёС‡РµРЅРёСЏ. РќРёРєР°РєРёС… РЅРѕРІС‹С… РїР°РґРµРЅРёР№, СЃРІСЏР·Р°РЅРЅС‹С… СЃ F4/F5/F6/G0/C2.

---

## 14. Documentation vs Code Gaps (РЅРµСЃРѕРѕС‚РІРµС‚СЃС‚РІРёСЏ)

| # | РќРµСЃРѕРѕС‚РІРµС‚СЃС‚РІРёРµ | Р”РѕРєСѓРјРµРЅС‚ РіРѕРІРѕСЂРёС‚ | РљРѕРґ/С„Р°РєС‚ РґРµР»Р°РµС‚ | Р§С‚Рѕ РёСЃС‚РёРЅР° |
|---|---|---|---|---|
| 1 | **AGENTS.md в†’ ADR/** | В«ADR/ вЂ” Architecture Decision RecordsВ» (СЃС‚СЂСѓРєС‚СѓСЂР° РїСЂРѕРµРєС‚Р°) | РљРѕСЂРЅРµРІРѕР№ `ADR/` **РїСѓСЃС‚**; ADR-С„Р°Р№Р»С‹ РІ `docs/ADR/` | Р¤Р°РєС‚: docs/ADR/. AGENTS.md СѓСЃС‚Р°СЂРµР» РїРѕ РїСѓС‚Рё |
| 2 | **AGENTS.md СЃР»РѕРё Pulse** | В«6 СЃР»РѕС‘РІВ» РІ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅРѕР№ РґРёР°РіСЂР°РјРјРµ; В«8 СЃР»РѕС‘РІ PulseВ» РґР°Р»РµРµ; В«WorldEngineLayerV2В» | РџСЂРѕРІРµСЂРµРЅРѕ СЌС‚РёРј Р°СѓРґРёС‚РѕРј (`grep '^class \w+Layer' pulse/layers.py`): **10 РєРѕРЅРєСЂРµС‚РЅС‹С… СЃР»РѕС‘РІ** (Knowledge, VisualStyle, NarrativeArc, Scene, Meaning, Identity, Mission, Expansion, Screenplay, WorldEngine) + BaseLayer; РєР»Р°СЃСЃ РЅР°Р·С‹РІР°РµС‚СЃСЏ `WorldEngineLayer`, РЅРµ V2 | Р¤Р°РєС‚: 10 СЃР»РѕС‘РІ; CHANGELOG 2.0.0 (В«СЃ 4 РґРѕ 10В») С‚РѕС‡РµРЅ; AGENTS.md Рё PROJECT_STATE (6/8) СѓСЃС‚Р°СЂРµР»Рё |
| 3 | **AGENTS.md РїРѕСЂС‚С‹/СЃС‚СЂСѓРєС‚СѓСЂР°** | В«Ant Design 6В», В«/_ui/* Jinja2+HTMXВ», docker-compose РєР°Рє РѕСЃРЅРѕРІРЅРѕР№ СЃС‚Р°СЂС‚ | РЎСѓС‰РµСЃС‚РІСѓРµС‚; РЅРѕ РЅРµ СѓРїРѕРјРёРЅР°РµС‚ arkaim-web-v2, arkaim-media, MD-Р»РёРЅРµР№РєСѓ, РїРѕСЂС‚ 3001 v2-С„СЂРѕРЅС‚РµРЅРґР° | AGENTS.md РѕРїРёСЃС‹РІР°РµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ ~05.09 (РїРѕСЃР»РµРґРЅРµРµ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёРµ), РЅРµ Р·РЅР°РµС‚ С‚РµРєСѓС‰РµР№ С„Р°Р·С‹ |
| 4 | **ADR_TEMPORAL СЃС‚Р°С‚СѓСЃ В«PROPOSEDВ»** | Р—Р°РіРѕР»РѕРІРѕРє: В«РѕР¶РёРґР°РµС‚ ACCEPTED РІР»Р°РґРµР»СЊС†Р°В» | B1/C1 СЂРµР°Р»РёР·РѕРІР°РЅС‹ (TEMPORAL_API_ALIGNMENT_REPORT РЅР°Р·С‹РІР°РµС‚ РµРіРѕ В«ACCEPTEDВ»), F3 РїРѕСЃС‚СЂРѕРµРЅ РЅР° РµРіРѕ РёРЅРІР°СЂРёР°РЅС‚Р°С… | Р¤Р°РєС‚: СЂРµС€РµРЅРёСЏ РєР°РЅРѕРЅРёС‡РµСЃРєРёРµ (СЂРµР°Р»РёР·РѕРІР°РЅС‹); СЃС‚Р°С‚СѓСЃ РІ С€Р°РїРєРµ ADR РЅРµ РѕР±РЅРѕРІР»С‘РЅ |
| 5 | **docs/PROJECT_STATE.md, PROJECT_STATUS.md, PROJECT_SUMMARY.md (08.08)** | В«219+ СЂРѕСѓС‚РѕРІВ», В«34 СЃС‚СЂР°РЅРёС†С‹В», В«AntD 6В», РѕРїРёСЃС‹РІР°СЋС‚ legacy-СЃС‚РµРє РєР°Рє С‚РµРєСѓС‰РёР№ | РђРєС‚СѓР°Р»СЊРЅРµРµ: web-v2-РєРѕРЅС‚СЂР°РєС‚С‹ (289 OpenAPI-РїСѓС‚РµР№, 298 RBAC), MD-Р»РёРЅРёСЏ, media-РіСЂР°РЅРёС†Р° | Р”РѕРєСѓРјРµРЅС‚С‹ Р°РІРіСѓСЃС‚Р° СѓСЃС‚Р°СЂРµР»Рё РєР°Рє В«С‚РµРєСѓС‰РµРµ СЃРѕСЃС‚РѕСЏРЅРёРµВ»; СЃРѕС…СЂР°РЅСЏСЋС‚ С†РµРЅРЅРѕСЃС‚СЊ РєР°Рє РёСЃС‚РѕСЂРёС‡РµСЃРєРёР№ СЃСЂРµР· |
| 6 | **docs/CLAUDE.md** | В«111+ unit-С‚РµСЃС‚РѕРІ backendВ», В«World Engine РќРћР’Р«Р™В», С‚СЂРµР±СѓРµС‚ start_all.bat | РЎРµР№С‡Р°СЃ 66 С‚РµСЃС‚-С„Р°Р№Р»РѕРІ (СЃРѕС‚РЅРё С‚РµСЃС‚РѕРІ); start*.bat РІ .gitignore (РїРµСЂРµРјРµС‰РµРЅС‹ РІ scripts/) | CLAUDE.md СѓСЃС‚Р°СЂРµР» (20.07); РґСѓР±Р»РёСЂРѕРІР°РЅРЅС‹Рµ СЃРµРєС†РёРё РІРЅСѓС‚СЂРё РЅРµРіРѕ |
| 7 | **README РјРµС‚СЂРёРєРё** | В«РЎР»РѕС‘РІ Pulse 10В», В«API 219В», В«С‚РµСЃС‚РѕРІ 349+В» | Р РµР°Р»СЊРЅС‹Рµ С†РёС„СЂС‹ РґСЂРµР№С„СѓСЋС‚ (OpenAPI 289 РїСѓС‚РµР№ РїРѕ F1-СЃРЅРёРјРєСѓ) | README вЂ” РјР°СЂРєРµС‚РёРЅРіРѕРІС‹Р№ СЃСЂРµР· 08.08; РЅРµ РѕРїРµСЂР°С‚РёРІРЅС‹Р№ СЃС‚Р°С‚СѓСЃ |
| 8 | **F3 СЃС‚Р°С‚СѓСЃ** | F3_REPORT: В«IMPLEMENTED & TESTED & VERIFIED. Р–РґСѓ СЂРµС€РµРЅРёСЏ РІР»Р°РґРµР»СЊС†Р°В» + FOLLOW-UP Р·Р°РєСЂС‹Р» PA-1/PA-2 | F3 ACCEPTED owner-GO D1 (2026-09-18): 85/85 С‚РµСЃС‚РѕРІ, 14/14 live-smoke, forensic post-audit РІС‹РїРѕР»РЅРµРЅ, backend РЅРµ С‚СЂРѕРЅСѓС‚ | Р¤Р°РєС‚: F3 вЂ” ACCEPTED & CLOSED (D1). |
| 8.5 | **F4 STATUS** | Р Р°РЅСЊС€Рµ: F4 WIP РЅР° РґРёСЃРєРµ, untracked; РЅРµС‚ SPEC, PRE-AUDIT, GO | РЎР•Р™Р§РђРЎ: F4 ACCEPTED & CLOSED 2026-09-18 (owner-GO РџР РРќРЇРўРћ); Р·Р°РєРѕРјРјРёС‡РµРЅ (`28514fb`); 80 С‚РµСЃС‚РѕРІ green; 5 СЃС‚СЂР°РЅРёС† РІ next build; backend 0 РёР·РјРµРЅРµРЅРёР№ | Р¤Р°РєС‚: F4 вЂ” ACCEPTED & CLOSED, РєРѕРґ РІ master. |
| 8.6 | **F5/F6 СЃС‚Р°С‚СѓСЃ** | РћС‚СЃСѓС‚СЃС‚РІСѓСЋС‚ РІ РґРѕРєСѓРјРµРЅС‚Рµ (Р°СѓРґРёС‚ 18 СЃРµРЅС‚СЏР±СЂСЏ) | F5 CLOSED (`a090ec8`, 2026-09-23): /xray, /history, WS toast, 5 СЃС‚СЂР°РЅРёС† Р·Р°РєРѕРјРјРёС‡РµРЅС‹. F6 CLOSED (`b4e6893`, 2026-09-23): /help, a11y, 14 E2E С‚РµСЃС‚РѕРІ. | Р­С‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ РЅРµ РѕС‚СЂР°Р¶Р°Р» F5/F6 РґРѕ GO-1. РСЃРїСЂР°РІР»РµРЅРѕ. |
| 8.7 | **G0 СЃС‚Р°С‚СѓСЃ** | РћС‚СЃСѓС‚СЃС‚РІСѓРµС‚ РІ РґРѕРєСѓРјРµРЅС‚Рµ | G0 CLOSED (merge `57d85f0`, 2026-09-16): /v1/models, /v1/chat/completions, /providers/health, per-provider rate limiting, 12 С‚РµСЃС‚РѕРІ. | Р­С‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ РЅРµ РѕС‚СЂР°Р¶Р°Р» G0 РґРѕ GO-1. РСЃРїСЂР°РІР»РµРЅРѕ. |
| 8.8 | **C2 СЃС‚Р°С‚СѓСЃ** | РЎС‚СЂРѕРєР° 218: В«C2 РєСЂРѕРјРµвЂ¦ РЅРµ РёСЃРїСЂР°РІР»РµРЅВ»; СЃС‚СЂРѕРєР° 382: D-16 В«C2-findingВ» | Р¤Р°РєС‚: C2 РёСЃРїСЂР°РІР»РµРЅ РІ commit `f1d5d60` (2026-09-16): `relation.py:precedes()` в†’ `ProvenanceCategory.DERIVED`; С‚РµСЃС‚ `test_precedes_is_derived_from_epoch_order` PASS. Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ РІ `7c8ab27`. | РџСЂРѕС‚РёРІРѕСЂРµС‡РёРІС‹Рµ СѓС‚РІРµСЂР¶РґРµРЅРёСЏ РІ РґРѕРєСѓРјРµРЅС‚Рµ. РСЃРїСЂР°РІР»РµРЅРѕ РІ В§7.1 Рё В§12. |
| 9 | **MD-С„Р°Р·С‹ vs M-С„Р°Р·С‹ РЅСѓРјРµСЂР°С†РёСЏ** | MD4-РґРѕРєСѓРјРµРЅС‚С‹ РіРѕРІРѕСЂСЏС‚ В«M4.1, M4.2.2вЂ¦В» | MEDIA_DIRECTION_FOUNDATION РёСЃРїРѕР»СЊР·СѓРµС‚ В«MD-4В» РґР»СЏ РІСЃРµРіРѕ СЌС‚Р°РїР° | В«M4.xВ» = РїРѕРґСЌС‚Р°РїС‹ MD-4; РєРѕРЅС„Р»РёРєС‚РѕРІ РїРѕ СЃРѕРґРµСЂР¶Р°РЅРёСЋ РЅРµС‚, С‚РѕР»СЊРєРѕ РїРѕ РёРјРµРЅРѕРІР°РЅРёСЋ |
| 10 | **ADR_MEDIA_BOUNDARY СЃС‚Р°С‚СѓСЃ** | РЁР°РїРєР°: В«PROPOSED вЂ” РѕР¶РёРґР°РµС‚ ACCEPTEDВ» | M4.1-РѕС‚С‡С‘С‚ В§2 РЅР°Р·С‹РІР°РµС‚ owner-СЂРµС€РµРЅРёСЏ РїРѕ РЅРµРјСѓ РїСЂРёРЅСЏС‚С‹РјРё; MD-2/3/4 РІС‹РїРѕР»РЅСЏР»РёСЃСЊ РІ РµРіРѕ СЂР°РјРєР°С… | Р¤Р°РєС‚: СЂР°Р±РѕС‚Р°РµС‚ РєР°Рє РїСЂРёРЅСЏС‚С‹Р№; СЃС‚Р°С‚СѓСЃ-СЃС‚СЂРѕРєР° РЅРµ РѕР±РЅРѕРІР»РµРЅР° |
| 17 | **MD-7 РЅРµ РѕС‚СЂР°Р¶С‘РЅ** | Р”РѕРєСѓРјРµРЅС‚ Р·Р°РєР°РЅС‡РёРІР°РµС‚СЃСЏ MD-6 | MD-7 Р·Р°РєСЂС‹С‚ (POST_F6_NEXT_MILESTONES_AUDIT.md В§2): 4 С„Р°Р№Р»Р° cleanup, С‚РµСЃС‚С‹ pass | Р­С‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ РЅРµ РѕС‚СЂР°Р¶Р°Р» MD-7 РґРѕ GO-1. РСЃРїСЂР°РІР»РµРЅРѕ РІ В§6.4. |
| 18 | **F-12 РЅРµ РІ В§6.3** | F-12 СѓРїРѕРјСЏРЅСѓС‚ РІ В§6.3 РЅРѕ Р±РµР· СЃС‚Р°С‚СѓСЃР° CLOSED | F-12 FUNCTIONALLY ACCEPTED / CLOSED (`c022e77`, 2026-09-23) | РЎС‚Р°С‚СѓСЃ РІ В§6.3 СѓР¶Рµ РІРµСЂРЅС‹Р№; РґРѕР±Р°РІР»РµРЅ РІ СЃРІРѕРґРєСѓ. |
| 11 | **GET /assets/{id}/file Рё С‡С‚РµРЅРёСЏ** | MD4_PRE: В«СЂРѕСѓС‚С‹ РѕС‚РґР°СЋС‚ РёС… РёР· data/В» | РџРѕРґС‚РІРµСЂР¶РґРµРЅРѕ: assets.py 317вЂ“410 СЃСѓС‰РµСЃС‚РІСѓРµС‚ | РЎРѕРѕС‚РІРµС‚СЃС‚РІСѓРµС‚ |
| 12 | **РџР°СЂР° В«arkaim-web РїСЂРѕС‚РёРІ arkaim-web-v2В»** | FRONTEND_ARCHITECTURE В§1: В«Р›РѕРєР°С†РёСЏ РєРѕРґР° arkaim-web/ вЂ” РїРѕР»РЅР°СЏ Р·Р°РјРµРЅР° СЃРѕРґРµСЂР¶РёРјРѕРіРѕВ» | Р РµР°Р»СЊРЅРѕ РїРѕСЃС‚СЂРѕРµРЅ РћРўР”Р•Р›Р¬РќР«Р™ РєР°С‚Р°Р»РѕРі arkaim-web-v2/ (РїРѕСЂС‚ 3001), legacy РЅРµ С‚СЂРѕРЅСѓС‚ | Р¤Р°РєС‚: РґРІР° С„СЂРѕРЅС‚РµРЅРґР° СЃРѕСЃСѓС‰РµСЃС‚РІСѓСЋС‚; РІРѕРїСЂРѕСЃ С„РёРЅР°Р»СЊРЅРѕР№ РєРѕРЅСЃРѕР»РёРґР°С†РёРё РѕС‚РєСЂС‹С‚ (FRONTEND_ARCHITECTURE В§12 вЂ” В«СЂРµС€РµРЅРёРµ РІР»Р°РґРµР»СЊС†Р°В») |
| 13 | **WORLD_ENGINE_* / World_Explorer_* РІ РєРѕСЂРЅРµ** | Р”РѕРєСѓРјРµРЅС‚С‹ СЃСѓС‰РµСЃС‚РІСѓСЋС‚ РІ РєРѕСЂРЅРµ (РёСЋР»СЊ) | .gitignore: В«Duplicate docs in rootВ» вЂ” РёРіРЅРѕСЂРёСЂСѓСЋС‚СЃСЏ | РњС‘СЂС‚РІС‹Рµ РєРѕРїРёРё; canonical вЂ” docs/ |
| 14 | **TEST_REPORT.md (20.07)** | В«Р’СЃРµ 56 С‚РµСЃС‚РѕРІ РїСЂРѕР№РґРµРЅС‹В» | РќС‹РЅРµ СЃРѕС‚РЅРё С‚РµСЃС‚РѕРІ; РѕС‚РґРµР»СЊРЅС‹Рµ С†РёС„СЂС‹ РЅРµР°РєС‚СѓР°Р»СЊРЅС‹ | РСЃС‚РѕСЂРёС‡РµСЃРєРёР№ СЃСЂРµР· |
| 15 | **Media-Contract РїСЂРёРјРµСЂ С‚Р°Р№РјР°СѓС‚РѕРІ** | РљРѕРЅС‚СЂР°РєС‚: В«image в‰¤300 СЃ (РєР°Рє ComfyUIProvider._poll)В» | comfyui.py _poll timeout=300 вЂ” СЃРѕРѕС‚РІРµС‚СЃС‚РІСѓРµС‚ | РЎРѕРѕС‚РІРµС‚СЃС‚РІСѓРµС‚ |
| 16 | **`comfy_generate` MCP-РѕРїРёСЃР°РЅРёРµ DSH (СЃСЂРµРґР°)** | Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ AGENTS.md DSH: ComfyUI-РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹ В«Media-agnostic РіРµРЅРµСЂР°С†РёСЏ С‡РµСЂРµР· AgentВ» | РќРµ С‡Р°СЃС‚СЊ СЂРµРїРѕ; СѓРїРѕРјСЏРЅСѓС‚Рѕ, С‡С‚РѕР±С‹ РЅРµ РїСѓС‚Р°С‚СЊ: MCP-РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹ в‰  Media-РїСЂРѕРµРєС‚ | РРЅСЃС‚СЂСѓРјРµРЅС‚Р°Р»СЊРЅР°СЏ СЃСЂРµРґР°, РІРЅРµ РіСЂР°РЅРёС† РїСЂРѕРµРєС‚Р° |

---

## 15. Current Development Position

| Р’РѕРїСЂРѕСЃ | РћС‚РІРµС‚ | РСЃС‚РѕС‡РЅРёРє |
|---|---|---|
| РџРѕСЃР»РµРґРЅРёР№ Р·Р°РІРµСЂС€С‘РЅРЅС‹Р№ СЌС‚Р°Рї | **F6 CLOSED** (2026-09-23, `b4e6893`). РџР°СЂР°Р»Р»РµР»СЊРЅРѕ: G0 CLOSED (`57d85f0`), C2 CLOSED (`f1d5d60`), F-12 CLOSED (`c022e77`), MD-7 CLOSED. Р’СЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7), РІСЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6), G0, C2, F-12 вЂ” СЂРµР°Р»РёР·РѕРІР°РЅС‹ Рё РїСЂРёРЅСЏС‚С‹. | В§6.3вЂ“6.5, POST_F6_NEXT_MILESTONES_AUDIT.md |
| РљР°РєРѕР№ СЌС‚Р°Рї СЃРµР№С‡Р°СЃ СЂР°Р·СЂРµС€С‘РЅ | Р¤РѕСЂРјР°Р»СЊРЅРѕ вЂ” **РЅРёРєР°РєРѕР№ РЅРµ В«СЂР°Р·СЂРµС€С‘РЅВ»**: РєР°Р¶РґС‹Р№ milestone С‚СЂРµР±СѓРµС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ owner-GO. РЎР»РµРґСѓСЋС‰РёР№ С€Р°Рі вЂ” РѕРїСЂРµРґРµР»РµРЅРёРµ MVP Arkaim v2 Рё РїСЂРѕРІРµСЂРєР° E2E-С†РµР»РѕСЃС‚РЅРѕСЃС‚Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ С†РёРєР»Р°. | РђРЅР°Р»РёС‚РёС‡РµСЃРєРёР№ РѕС‚С‡С‘С‚ v2 |
| Р§С‚Рѕ РґРµР»Р°С‚СЊ РќР•Р›Р¬Р—РЇ (Р±РµР· owner-GO) | Р’СЃС‘ РёР· В§11.3; РїР»СЋСЃ: РЅРµ СЃС‚СЂРѕРёС‚СЊ РІС‚РѕСЂСѓСЋ architecture/planner/workflow engine; РЅРµ РѕР¶РёРІР»СЏС‚СЊ quality; РЅРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ queue/batch/regenerate Р±РµР· Р°СЂС…РёС‚РµРєС‚СѓСЂРЅРѕРіРѕ СЂРµС€РµРЅРёСЏ; РЅРµ СѓРґР°Р»СЏС‚СЊ arkaim-web РґРѕ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РїРѕРєСЂС‹С‚РёСЏ v2; РЅРµ РЅР°С‡РёРЅР°С‚СЊ mobile/audio/i18n РґРѕ product-level coherence proof | MD3_CLOSURE В§3; ADR_MEDIA_BOUNDARY |
| Р РµС€РµРЅРёСЏ, РЅРµ С‚СЂРµР±СѓСЋС‰РёРµ РїРѕРІС‚РѕСЂРЅРѕРіРѕ РѕР±СЃСѓР¶РґРµРЅРёСЏ | ADR TEMPORAL (AвЂ“D + РёРЅРІР°СЂРёР°РЅС‚); ADR MEDIA BOUNDARY (5 decisions + РёРЅРІР°СЂРёР°РЅС‚С‹); ADR MEDIA PLAN V0 (10 owner-decisions); M8.1; MD-2/MD-3/MD-7 РєРѕРЅС‚СЂР°РєС‚С‹; MD-4 owner-СЂРµС€РµРЅРёСЏ; Q1/Q2/Q3 M4.2.1; frozen AD-СЃР»РѕРІР°СЂСЊ | В§7 |
| Р“РґРµ С‚СЂРµР±СѓРµС‚СЃСЏ РѕС‚РґРµР»СЊРЅС‹Р№ GO РІР»Р°РґРµР»СЊС†Р° | РћРїСЂРµРґРµР»РµРЅРёРµ MVP Arkaim v2; D-3 (video-РїР»Р°РЅ Route C) вЂ” Р·Р°РІРёСЃРёС‚ РѕС‚ MVP; D-4 (queue/async РјРѕРґРµР»СЊ) вЂ” Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ; arkaim-web retirement; РЅРѕРІС‹Рµ ADR; Р»СЋР±С‹Рµ РёР·РјРµРЅРµРЅРёСЏ backend-РєРѕРЅС‚СЂР°РєС‚РѕРІ | вЂ” |
---

## 16. Next Allowed Step (РїРѕ СЂРµРіР»Р°РјРµРЅС‚Сѓ РїСЂРѕРµРєС‚Р°)

**Р РµРіР»Р°РјРµРЅС‚:** РєР°Р¶РґС‹Р№ milestone = pre-audit в†’ СЂРµР°Р»РёР·Р°С†РёСЏ в†’ STOP в†’ owner-GO. РќРёС‡РµРіРѕ РЅРµ РЅР°С‡РёРЅР°РµС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё.

**РўРµРєСѓС‰Р°СЏ РїРѕР·РёС†РёСЏ:** РІСЃРµ MD-СЌС‚Р°РїС‹ (1вЂ“7), РІСЃРµ F-СЌС‚Р°РїС‹ (F1вЂ“F6), G0, C2, F-12 Р·Р°РєСЂС‹С‚С‹. MEDIA_CONTRACT v1.0 ACCEPTED. HEAD `8aef0f9`.

**РљР°РЅРґРёРґР°С‚С‹ РЅР° СЃР»РµРґСѓСЋС‰РёР№ СЌС‚Р°Рї (С‚СЂРµР±СѓСЋС‚ РѕС‚РґРµР»СЊРЅРѕРіРѕ owner-GO, РЅРё РѕРґРёРЅ РЅРµ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРёР№):**

- **MVP definition** вЂ” С„РёРєСЃР°С†РёСЏ РјРёРЅРёРјР°Р»СЊРЅРѕРіРѕ СЂР°Р±РѕС‡РµРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ С†РёРєР»Р° Arkaim v2 (РєР°РєРѕР№ СЃС†РµРЅР°СЂРёР№ СЃС‡РёС‚Р°РµС‚СЃСЏ В«РїСЂРѕРґСѓРєС‚ РіРѕС‚РѕРІВ»)
- **D-3 video-plan** вЂ” РїРѕРґРєР»СЋС‡РµРЅРёРµ Route C MediaPlan Рє `generate_video` (Р·Р°РІРёСЃРёС‚ РѕС‚ MVP definition)
- **D-4 async/job РјРѕРґРµР»СЊ** вЂ” Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ: submit в†’ status в†’ cancel в†’ result (Р·Р°РІРёСЃРёС‚ РѕС‚ MVP)
- **arkaim-web retirement** вЂ” РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ С‡С‚Рѕ v2 РїРѕРєСЂС‹РІР°РµС‚ РІСЃРµ С„СѓРЅРєС†РёРё legacy, Р·Р°С‚РµРј СѓРґР°Р»РµРЅРёРµ
- **D-7 quality cleanup** вЂ” СѓРґР°Р»РµРЅРёРµ/РґРµРїСЂРµРєР°РЅРёРµ GenerationParams.quality
- **РђСЂС…РёС‚РµРєС‚СѓСЂРЅС‹Рµ СЂРµС€РµРЅРёСЏ** вЂ” РЅРѕРІС‹Рµ ADR РїРѕ Р¶РµР»Р°РЅРёСЋ РІР»Р°РґРµР»СЊС†Р°

**GO-1 Р·Р°РІРµСЂС€С‘РЅ:** СЌС‚РѕС‚ РґРѕРєСѓРјРµРЅС‚ Р°РєС‚СѓР°Р»РёР·РёСЂРѕРІР°РЅ РЅР° HEAD `8aef0f9`.

---

## 17. Explicitly Forbidden Work (РЅР° С‚РµРєСѓС‰РµР№ РїРѕР·РёС†РёРё)

1. **РќРёРєР°РєРѕРіРѕ РєРѕРґР°** РґРѕ РѕС‚РґРµР»СЊРЅРѕРіРѕ owner-GO.
2. РќРµ РїРµСЂРµРЅРѕСЃРёС‚СЊ РЅРёС‡РµРіРѕ РёР· РђСЂРєР°РёРјР° РІ Media Р±РµР· GO; РЅРµ СЂР°СЃС€РёСЂСЏС‚СЊ СЃРѕСЃС‚Р°РІ РїРµСЂРµРЅРѕСЃР° (SD-stub, quality, GigaChat, pollinations-РѕСЃС‚Р°С‚РєРё вЂ” РЅРµ РїРµСЂРµРЅРѕСЃСЏС‚СЃСЏ).
3. РќРµ РјРµРЅСЏС‚СЊ: 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E; MediaPlan/SceneContext/WorldModel/temporal/M10.2-РєРѕРЅС‚СЂР°РєС‚С‹; SCHEMAS/MEDIA_PLAN.schema.json (Р±Р°Р№С‚-РёРґРµРЅС‚РёС‡РЅРѕСЃС‚СЊ вЂ” РёРЅРІР°СЂРёР°РЅС‚); film_studio; РїСЂРѕРІР°Р№РґРµСЂРЅС‹Рµ СЃРёРіРЅР°С‚СѓСЂС‹.
4. РќРµ РѕР¶РёРІР»СЏС‚СЊ: quality (MP-F1); negative-to-provider РІ РђСЂРєР°РёРјРµ; dead-РїРѕР»СЏ С€РѕС‚Р° E.
5. РќРµ СѓРґР°Р»СЏС‚СЊ arkaim-web РґРѕ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ С‡С‚Рѕ v2 РїРѕРєСЂС‹РІР°РµС‚ РІСЃРµ С„СѓРЅРєС†РёРё legacy.
6. РќРµ С‡РёРЅРёС‚СЊ РїРѕРїСѓС‚РЅРѕ: seed-hash; test_assets_new_params (D-11); genome-history churn (D-17).
7. РќРµ СЃРјРµС€РёРІР°С‚СЊ ComfyUI Agent v1 (MCP) СЃ Media-РїСЂРѕРµРєС‚РѕРј; РЅРµ РїРѕРіР»РѕС‰Р°С‚СЊ Agent.
8. РќРµ РЅР°С‡РёРЅР°С‚СЊ: audio; queue/batch/regenerate-РјРёРіСЂР°С†РёСЋ (D-4 вЂ” Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ); РЅРѕРІС‹Рµ relation-С‚РёРїС‹; TemporalEngine-СЃРµСЂРІРёСЃ; mobile; i18n; production hardening.
9. РќРµ РѕРїСЂРµРґРµР»СЏС‚СЊ MVP Р±РµР· separate GO РІР»Р°РґРµР»СЊС†Р°.

---

## 18. Р¤РёРЅР°Р»СЊРЅР°СЏ РєР°СЂС‚Р°

```
РџР РћР•РљРўР«
в”њв”Ђв”Ђ arkaim (master 8aef0f9) вЂ” РґРѕРјРµРЅ РєРЅРёРіРё; F1вЂ“F6 вњ…, G0 вњ…, C2 вњ…, F-12 вњ…, MD-1..MD-7 вњ…
в”‚   в”њв”Ђв”Ђ runtime/ вЂ” FastAPI :8642, DI (adc_deps), 10 СЂРѕСѓС‚РµСЂРѕРІ, auth, 106 С‚РµСЃС‚-С„Р°Р№Р»РѕРІ
в”‚   в”њв”Ђв”Ђ core/CORE/ вЂ” Pulse В· WorldEngine В· temporal (12 СЌРїРѕС…+today) В· KG В· RAG
в”‚   в”‚     В· visual (SceneContext MD-2) В· media_plan (MediaPlan v0 MD-3)
в”‚   в”‚     В· visual_assets (pipeline+storage+queue) В· film_studio В· providers (legacy stubs)
в”‚   в”‚     В· GENOME (РґР°РЅРЅС‹Рµ+workflows-РєРѕРїРёСЏ) В· KNOWLEDGE В· CHROMA_DB
в”‚   в”‚     В· dto/openai.py (G0), identity/, repositories/, services/
в”‚   в”њв”Ђв”Ђ arkaim-web/ (legacy, Р·Р°РјРѕСЂРѕР¶РµРЅ РґРѕ retirement GO)
в”‚   в”њв”Ђв”Ђ arkaim-web-v2/ (F1вЂ“F6 CLOSED; 25 СЃС‚СЂР°РЅРёС† РІ master; 37 test-С„Р°Р№Р»РѕРІ)
в”‚   в”њв”Ђв”Ђ arkaim-mobile/ (RN+Expo, Р·Р°РіРѕС‚РѕРІРєР°)
в”‚   в””в”Ђв”Ђ docs/ (100+: ADRГ—7, MD-СЃРµСЂРёСЏ, M-СЃРµСЂРёСЏ, F-СЃРµСЂРёСЏ, archive/)
в”њв”Ђв”Ђ arkaim-media (master f0327cd) вЂ” РёСЃРїРѕР»РЅРёС‚РµР»СЊ РіРµРЅРµСЂР°С†РёРё
в”‚   в”њв”Ђв”Ђ docs/MEDIA_CONTRACT.md (v1.0 ACCEPTED) + schemas/Г—4 + examples/Г—3
в”‚   в”њв”Ђв”Ђ media/ (config + image/comfyui + video/image_sequence+mock + chains)
в”‚   в””в”Ђв”Ђ workflows/default.json (= Р°СЂРєР°РёРјСЃРєРёР№, SHA СЃРІРµСЂРµРЅ)
в””в”Ђв”Ђ ComfyUI-СЃРµСЂРІРµСЂ :8188 (Р¶РёРІ) + ComfyUI Agent v1 (MCP, РІРЅРµ РїСЂРѕРµРєС‚РѕРІ)

РљРћРќРўР РђРљРўР«
в”њв”Ђв”Ђ Arkaimв†’Media: POST /v1/generate {plan + executionГ—5} в†’ {bytes_b64, media_idвЂ¦}
в”‚     В· forbidden: quality/model/seed/workflow/provider/вЂ¦ (additionalProperties:false)
в”‚     В· MediaPlan-СЃС…РµРјР° Р±Р°Р№С‚-РёРґРµРЅС‚РёС‡РЅР° РјРµР¶РґСѓ СЂРµРїРѕ (SHA B52B7E7AвЂ¦)
в”њв”Ђв”Ђ Р’РЅСѓС‚СЂРё Arkaim: MediaPlan v0 (BANNED) В· SceneContext В· 5 РјР°СЂС€СЂСѓС‚РѕРІ (byte-frozen)
в”‚     В· temporal API Г—14 (B1/C1/C2 done) В· OpenAPI-290/RBAC-298 (web-v2)
в”‚     В· G0: /v1/models, /v1/chat/completions, /providers/health
в””в”Ђв”Ђ Р’СЂРµРјРµРЅРЅС‹Рµ: D-2 СЃС‹СЂС‹Рµ РїСѓС‚Рё; D-3 video-plan; D-4 queue РјРѕРґРµР»СЊ; D-7 quality field

РўР•РљРЈР©РР™ MILESTONE
F6 CLOSED (b4e6893) В· G0 CLOSED (57d85f0) В· C2 CLOSED (f1d5d60) В· F-12 CLOSED (c022e77)
MD-7 CLOSED В· MD-6 CLOSED (4be2a40) В· MEDIA_CONTRACT v1.0 ACCEPTED (f0327cd)

NEXT ALLOWED STEP (С‚СЂРµР±СѓРµС‚ owner-GO)
1) MVP definition вЂ” С„РёРєСЃР°С†РёСЏ РјРёРЅРёРјР°Р»СЊРЅРѕРіРѕ СЂР°Р±РѕС‡РµРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ С†РёРєР»Р°
2) D-3 video-plan вЂ” РїРѕРґРєР»СЋС‡РµРЅРёРµ Route C Рє generate_video (Р·Р°РІРёСЃРёС‚ РѕС‚ MVP)
3) D-4 async/job РјРѕРґРµР»СЊ вЂ” Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ (Р·Р°РІРёСЃРёС‚ РѕС‚ MVP)
4) arkaim-web retirement вЂ” РїРѕСЃР»Рµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РїРѕРєСЂС‹С‚РёСЏ v2
5) D-7 quality cleanup вЂ” СѓРґР°Р»РµРЅРёРµ/РґРµРїСЂРµРєР°РЅРёРµ GenerationParams.quality
6) РќРѕРІС‹Рµ ADR вЂ” РїРѕ Р¶РµР»Р°РЅРёСЋ РІР»Р°РґРµР»СЊС†Р°

РќР• РўР РћР“РђРўР¬ РЎР•Р™Р§РђРЎ
вЂў 5 РјР°СЂС€СЂСѓС‚РѕРІ AвЂ“E Рё РёС… РѕС‚РІРµС‚С‹ (byte-frozen)
вЂў MediaPlan/SceneContext/SCHEMAS (Р±Р°Р№С‚-РёРґРµРЅС‚РёС‡РЅРѕСЃС‚СЊ вЂ” РёРЅРІР°СЂРёР°РЅС‚)
вЂў WorldModel/temporal-РґР°РЅРЅС‹Рµ (read-only)
вЂў queue/async/batch/regenerate (D-4 вЂ” Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РєР»Р°СЃС‚РµСЂ)
вЂў quality/negative/dead-РїРѕР»СЏ вЂ” РЅРµ РѕР¶РёРІР»СЏС‚СЊ
вЂў seed-hash Рё РґСЂ. РїРµСЂРµРЅРµСЃС‘РЅРЅС‹Рµ РґРµС„РµРєС‚С‹ вЂ” РЅРµ С‡РёРЅРёС‚СЊ
вЂў arkaim-web вЂ” РЅРµ СѓРґР°Р»СЏС‚СЊ РґРѕ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РїРѕРєСЂС‹С‚РёСЏ v2
вЂў ComfyUI Agent v1 вЂ” РЅРµ РїРѕРіР»РѕС‰Р°С‚СЊ
вЂў audio/mobile/i18n/production вЂ” РЅРµ РЅР°С‡РёРЅР°С‚СЊ Р±РµР· GO
вЂў MVP definition вЂ” РЅРµ РѕРїСЂРµРґРµР»СЏС‚СЊ Р±РµР· separate GO РІР»Р°РґРµР»СЊС†Р°
```

---

## 19. Evidence / Source Files

**Git-С„Р°РєС‚С‹:** `git branch/rev-parse/log/status/diff` РѕР±РµРёС… СЂРµРї (РІС‹РІРѕРґС‹ РІ В§8); arkaim-media log `8e465cc`в†’`d4bcef2`.

**РљР»СЋС‡РµРІС‹Рµ РґРѕРєСѓРјРµРЅС‚С‹ (РІСЃРµ РІ `docs/` РµСЃР»Рё РЅРµ СѓРєР°Р·Р°РЅРѕ РёРЅРѕРµ):** MEDIA_DIRECTION_FOUNDATION.md В· MD2_IMPLEMENTATION_REPORT.md + MD2_POST_IMPLEMENTATION_FORENSIC_AUDIT.md В· MD3_1/3_2_ROUTE_{A,B,C,D,E}_{BASELINE,REPORT} В· MD3_3_DEPRECATION_REGISTRY.md В· MD3_STAGE_CLOSURE.md В· MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md В· MD4_M41_IMPLEMENTATION_REPORT.md В· MD4_M42_1_PROVIDER_INVENTORY.md В· MD4_M42_2_COMFYUI_MIGRATION_REPORT.md В· M8_1_ARCHITECTURE_DECISION.md + M8_1_TEST_ISOLATION_FIX_REPORT.md В· M9_SPEC.md В· M10_2_POST_IMPLEMENTATION_AUDIT.md В· TEMPORAL_API_ALIGNMENT_{PLAN,REPORT,FORENSIC_AUDIT}.md В· F1/F2/F3_*REPORTS В· FRONTEND_ARCHITECTURE.md В· NEXT_PHASE_ARCHITECTURAL_AUDIT.md В· ADR/ADR_TEMPORAL_WORLD_MODEL.md В· ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md В· ADR/ADR_MEDIA_PLAN_V0.md В· PROJECT_STATE.md (СѓСЃС‚Р°СЂ.) В· README/CHANGELOG/AGENTS.md (РєРѕСЂРµРЅСЊ).

**РљРѕРґ (РїСЂРѕРІРµСЂРµРЅРѕ РїРѕСЃС‚СЂРѕС‡РЅРѕ РІ СЌС‚РѕРј Р°СѓРґРёС‚Рµ):** `core/CORE/media_plan/dispatch.py` (РїРѕР»РЅРѕСЃС‚СЊСЋ) В· `core/CORE/providers/image/comfyui.py` (РїРѕР»РЅРѕСЃС‚СЊСЋ, 169 СЃС‚СЂ.) В· `core/CORE/providers/image/__init__.py` (РїРѕР»РЅРѕСЃС‚СЊСЋ) В· `core/CORE/visualization/__init__.py` В· `core/config.py` (РїРѕР»РЅРѕСЃС‚СЊСЋ) В· `runtime/core/adc_deps.py` (L1вЂ“373, С„Р°Р±СЂРёРєРё+СЂРµРµСЃС‚СЂ) В· `runtime/core/routes/visual.py` (L20вЂ“79, Route A) В· `runtime/core/book_routes.py` (РїРѕР»РЅРѕСЃС‚СЊСЋ) В· `runtime/core/provider_registry.py` (L1вЂ“80) В· `runtime/core/routes/{assets,film_studio,temporal,temporal_updates}.py` (РґРµРєРѕСЂР°С‚РѕСЂС‹ СЂРѕСѓС‚РѕРІ) В· `arkaim-media/media/config.py` + `media/image/comfyui.py` (С€Р°РїРєР°) В· `arkaim-media/docs/MEDIA_CONTRACT.md` (РїРѕР»РЅРѕСЃС‚СЊСЋ, 165 СЃС‚СЂ.) В· narrative_engine-РёРјРїРѕСЂС‚С‹ providers.registry (4 С„Р°Р№Р»Р°).

**РҐРµС€-РґРѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІР°:** workflows/default.json SHA256 `40F788FC3F08B8C6вЂ¦28063D2` (СЂР°РІРµРЅ РІ РѕР±РѕРёС… СЂРµРїРѕ); MEDIA_PLAN.schema.json SHA256 `B52B7E7AD0C340E8вЂ¦86A50F635` (СЂР°РІРµРЅ РІ РѕР±РѕРёС… СЂРµРїРѕ).

**РўРµСЃС‚-РїСЂРѕРіРѕРЅС‹ (СЌС‚РѕС‚ Р°СѓРґРёС‚):** РїРµСЂРµС‡РёСЃР»РµРЅС‹ РІ В§13 СЃ РєРѕРјР°РЅРґР°РјРё Рё С†РёС„СЂР°РјРё.

**Live-РїСЂРѕРІРµСЂРєРё:** ComfyUI :8188 /system_stats в†’ 200.

---

*Р”РѕРєСѓРјРµРЅС‚ Р°РєС‚СѓР°Р»РёР·РёСЂРѕРІР°РЅ РїРѕ GO-1 РЅР° HEAD `8aef0f9` (2026-09-24). Р’СЃРµ Р·Р°РєСЂС‹С‚С‹Рµ СЌС‚Р°РїС‹ (F1вЂ“F6, G0, C2, F-12, MD-1..MD-7) РѕС‚СЂР°Р¶РµРЅС‹. РўРµС…РЅРёС‡РµСЃРєРёРµ РґРѕР»РіРё D-1/D-5/D-9/D-10/D-16 РёСЃРїСЂР°РІР»РµРЅС‹ РёР»Рё РїРѕРјРµС‡РµРЅС‹ РєР°Рє CLOSED. РЎР»РµРґСѓСЋС‰РёР№ С€Р°Рі вЂ” owner-GO РЅР° MVP definition.*

**STOP. GO-1 Р·Р°РІРµСЂС€С‘РЅ. Р–РґСѓ СЂРµС€РµРЅРёСЏ РІР»Р°РґРµР»СЊС†Р°.**