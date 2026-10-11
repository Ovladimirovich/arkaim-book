# MD-3.2 ROUTE E IMPLEMENTATION REPORT — миграция `/shots/generate` (film-studio) на canonical MediaPlan path

**Дата:** 2026-09-12
**Статус:** IMPLEMENTED + TESTED — Route E мигрирован; verdict: **ЗАКРЫТ ПОЛНОСТЬЮ** (§Final verdict). **MD-3.2 завершён полностью: все 5 маршрутов (A, B, C, D, E) мигрированы.**
**Основа:** GO владельца на MD-3.2 Route E; Routes A/B/C/D ACCEPTED; ADR_MEDIA_PLAN_V0; MP-F10 (dead camera/duration/negative).
**Граница подэтапа:** только production-зона generate_shot в film_studio.py;film-studio pipeline/providers/БД — не тронуты (forensic §11).

---

## Простыми словами

1. **Что было целью?** — перевести последний, пятый маршрут — «Генерацию шота» в киностудии — на канонический конвейер, сохранив исторический результат байт-в-байт и не оживляя мёртвые поля шота.

2. **Что реально сделано?** — маршрут строит смысловой план из канонического контекста сцены; промпт шота из сценария передаётся в план как смысловое поле (как и раньше — в пайплайн); до генератора данные идут через временный конверт. Мёртвые поля шота (камера, длительность, негатив) остались мёртвыми — как и было, ничего не оживлено. 14 тестов, включая инвариант «мёртвые поля не дают новых эффектов».

3. **Что получилось?** — **PASS.** Исторический промпт идентичен ДО/ПОСЛЕ (крипто-хэш `3287ab6c88314433`); ответ — те же 4 поля; 404/500-семантика прежняя; 14/14 новых; 118/118 комбинированных (все 5 маршрутов, оба порядка); тесты киностудии 40/40; основная база данных не тронута.

4. **Есть ли проблемы?** — нет. Задокументированы pre-existing факты (не дефекты миграции): мёртвые поля шота никогда не доходили до генератора (подтверждено кодом и тестом); параметр «настроение» не влияет на текст (как в маршруте C); неизвестный словарю стиль убирает префикс (разрозненность словарей стилей — вне моих полномочий).

5. **Что дальше?** — ваш ACCEPT по Route E. На этом миграция всех пяти маршрутов MD-3.2 завершена; следующие шаги (MD-3.3 deprecation/docs, MD-4, MD-5) — только по вашим отдельным решениям. Сам ничего не начинаю.

---

## 1. Baseline (создан ДО изменения: `docs/MD3_2_ROUTE_E_BASELINE.md`)

- **Endpoint:** POST `/book/film/{project_id}/scenes/{scene_db_id}/shots/{shot_id}/generate` (query: style?/mood?/quality?).
- **Ответ (200):** ровно 4 ключа {asset_id, file, shot_id, status: completed}.
- **Исторический промпт:** «cinematic fantasy, epic film still, dramatic lighting, test shot» — SHA `3287ab6c88314433`; формула: STYLE_PRESETS[style] + промпт шота (при неизвестном словарю стиле префикс пуст → «test shot», SHA `53a10b4f48714232`).
- **До execution доходят:** prompt, size (1024x576/1024x1024 по aspect_ratio), preferred_provider="comfyui" — единственные (spy).
- **Dead/showcase (BASELINE FACT, подтверждено кодом film_studio.py:330-365):** shot.camera, shot.duration_sec, shot.negative_prompt — НЕ передаются в pipeline (остаются полями БД/ответа); mood-параметр — не влияет на текст (emotion из ctx); quality — записывается в asset, до провайдера не доходит (MP-F1-семья). **НЕ оживлено** (GO п.4).
- **Ошибки:** unknown shot/scene_db/project → 404; шот для несуществующей genome-сцены → 500 «Generation failed: Scene not found…» (прежний контракт, НЕ 404).

## 2. Changed files

```
ИЗМЕНЕН (1 существующий; зона ТОЛЬКО generate_shot):
  runtime/core/routes/film_studio.py — MD-3.2-блок: MediaPlanBuilder.build_image_plan(
    ctx, intent="film_shot", created_from="film_shot", style_override, custom_prompt=shot.prompt)
    + ExecutionDispatch.from_plan(plan, size, preferred_provider="comfyui")
    + pipeline.generate_image(..., plan=plan, dispatch=dispatch). Docstring.
НОВЫЕ (3):
  runtime/tests/test_md3_route_e.py — 14 тестов
  docs/MD3_2_ROUTE_E_BASELINE.md   — снимок «до»
  docs/MD3_2_ROUTE_E_IMPLEMENTATION_REPORT.md — этот отчёт
НЕ ТРОНУТЫ: pipeline.py (сессия C — принята, mtime 21:38), film-БД store/schemas,
  providers, media_plan/* (16:27-16:38), A/B/C/D-зоны (assets 21:39, visual 20:29 —
  их собственные сессии), frontend, temporal.
```

## 3. Tests — `runtime/tests/test_md3_route_e.py`, 14/14 PASS

| GO-пункт | Тест |
|----------|------|
| 1. План из canonical SceneContext | test_plan_built_in_route + test_shot_prompt_flows_to_plan_custom_prompt (lineage.created_from="film_shot"; custom_prompt замещает текст) |
| 2. Provider через ExecutionDispatch | test_provider_receives_via_dispatch (spy: prompt+size+preferred из конверта) |
| 3. Spy подтверждает плановый prompt/dispatch | там же + test_historical_prompt_preserved |
| 4. Historical prompt сохранён | test_historical_prompt_preserved (SHA 3287ab6c88314433, байт-в-байт) |
| 5. Response contract | test_response_contract_4_keys (ровно 4 ключа) |
| 6. Shot semantics | test_shot_prompt_flows_to_plan_custom_prompt (промпт шота — смысловое; style → visual_style) |
| 7. Execution fields вне плана | test_no_execution_fields_in_plan (с учётом: camera/duration/fps — СЕМАНТИКА плана по контракту MD-3.1) |
| 8. Camera/duration/negative — dead (без новых эффектов) | test_camera_duration_negative_stay_dead (поля записаны в шот → промпт/параметры провайдера НЕ изменились) + test_quality_mood_stay_dead_for_execution (SHA 53a10b4f48714232) |
| 9. Existing error behavior | test_unknown_shot_404 · test_unknown_scene_db_404 · test_unknown_genome_scene_500 |
| 10. Нет второго canonical path | test_no_second_canonical_path |
| 11. WorldModel/temporal не изменяются | test_world_model_untouched_by_route_e (ctx стабилен, read-only) |
| 12. A/B/C/D не изменяются | test_routes_abcd_files_untouched (mtime-инвариант) |

Фикстуры: изолированная film-БД (собственный каталог — pytest tmp_path в DSH-sandbox недоступен, policy-артефакт задокументирован); auth-override snapshot→restore; spy-провайдер; rate_limits-clear.

## 4. Regression

| Набор | Результат |
|-------|-----------|
| test_md3_route_e.py | **14 passed** |
| Все 5 маршрутов + md3 + md2 (обе последовательности) | **118 passed** ×2 |
| 5 маршрутов A+B+C+D+E | **63 passed** |
| Visual-chunk 16 файлов (15 + route_e) | **226P / 4F** = база C (212P/4F) + 14; 4F = pre-existing test_assets_new_params |
| test_film_endpoints.py (вся E-зона film-studio) | **40 passed** |
| md2_routes::TestRouteEFilmShotGenerate | 2P (миграция не сломала MD-2-контракты) |
| MD-3.1 media_plan | 40P |
| ruff (мой тест; моя зона film_studio) | чист (F401/F811 FileResponse — pre-existing HEAD-импорт, не моя зона) |

## 5. Prompt compatibility

Исторический промпт **byte-identical** (SHA-доказательство `3287ab6c88314433`; spy == shot.prompt в БД после генерации). Формула не изменена: префикс стиля + промпт шота (custom_prompt); словари не переписаны. Путь: план (custom_prompt=shot.prompt — смысловое) → pipeline строит исторический текст → проекция в dispatch (`dispatch.prompt`, метка «MD-5: удалить») → провайдер. План несёт свой canonical-промпт — разделение слоёв как в A/B/C/D. Изменений промпта НЕТ.

## 6. Shot semantics

- shot.prompt → план (custom_prompt) И пайплайн — исторический вход сохранён.
- style → план (visual_style через style_override) И asset.style (исторический префикс).
- **camera/duration_sec/negative_prompt шота — dead (baseline-факт MP-F10):** НЕ передаются ни в план как execution-эффекты, ни в пайплайн — ровно как до миграции (тест п.8: после записи camera+duration в шот промпт и параметры провайдера идентичны baseline).
- mood — dead для текста (как Route C); quality — dead для execution (MP-F1-семья, не оживлено).

## 7. Execution dispatch flow

```
shot(film-БД) → project → ctx = build_scene_context(chapter, scene.scene_id)
  → MediaPlanBuilder.build_image_plan(ctx, intent="film_shot", created_from="film_shot",
                                       style_override, custom_prompt=shot.prompt)
  → MediaPlan (смысловые: scene/characters/location/temporal/style/atmosphere/
               composition(camera=семантика)/video-intent(duration/fps=семантика)/prompt)
  → ExecutionDispatch.from_plan(plan, size=<aspect_ratio→size>, preferred_provider="comfyui")
  → pipeline.generate_image(..., plan, dispatch)
  → dispatch.prompt = STYLE_PRESETS[style], custom_prompt   [legacy-проекция, ПОСЛЕ плана]
  → provider.generate_with_metadata(**dispatch.image_kwargs())
  → update_shot(asset_id, completed, prompt) → {asset_id, file, shot_id, status}
```
До execution: ТОЛЬКО prompt, size, preferred_provider (spy — как в baseline).

## 8. Execution leakage

- План не содержит execution-полей: model/steps/seed/cfg/sampler/workflow/provider/backend/quality/checkpoint/lora/size/negative_prompt (тест).
- **Уточнение по camera/duration_sec/fps:** эти поля в MediaPlan — СЕМАНТИЧЕСКИЕ (composition/video-intent; контракт и JSON-schema MD-3.1 — не расширялись). Провайдер их НЕ получает: до execution доходят только prompt/size/preferred (spy-доказательство).
- `verify_no_execution_fields()` = []; extra="forbid" действует; schema/builder/dispatch — mtime MD-3.1-окна (0 правок).
- provider/size — только через from_plan-аргументы dispatch (не в плане).

## 9. Camera/duration/negative findings (dead — зафиксировано, НЕ чинилось)

Подтверждено на коде и тестом: поля шота не доходили до pipeline и до миграции; migration НЕ дала им новых эффектов (после записи camera=close_up/low_angle/slow_zoom_in и duration=3.5 в шот — промпт SHA и все параметры провайдера идентичны baseline). Это showcase-поля ответа/БД. Оживление — за пределами MD-3.2 (решение владельца, кандидат MD-4+).

## 10. DB/F-12 status

Основная production film-БД **не тронута** (mtime июль 2026; тесты шли через изолированные БД film_test_*/film_probe_* в runtime-каталогах; временн́ые каталоги .tmp_md32e/.tmp_md3e и baseline-скрипт удалены после фиксации). **F-12 defect не проявлялся** в сессии E. (Примечание: pytest tmp_path недоступен в DSH-sandbox — policy-артефакт, тот же класс что TestFeedbackStore; тест использует собственный каталог с автоочисткой.)

## 11. Forensic scope

- film_studio.py: единственная вставка — generate_shot (hunk @@ -352 +37 строк; всё остальное — pre-existing MD-2).
- 1 canonical path: `from media_plan` = assets.py:88 (C) /197/237/276 (D) + visual.py:77 (A) /164 (B) + film_studio.py:368 (E) — все через один MediaPlanBuilder; новых типов/Builder'ов/контрактов не создано.
- A/B/C/D-зоны: mtime их собственных сессий (assets 21:39=C, visual 20:29=B, pipeline 21:38=C — до старта сессии E 22:00+); E-правка — film_studio.py 22:30.
- WorldModel — 05.09; media_plan/* — 16:27-16:38; schema — 16:30; frontend — 0 правок; film-store/schemas/providers — 0 правок.
- CJK 0; git status: M film_studio.py + 3 новых файла сессии E.

## 12. Pre-existing failures (не связанные с E)

- test_assets_new_params ×4 (ModuleNotFoundError runtime.core) — во всех базах (visual-chunk 4F).
- Словари стилей разрознены: pipeline-STYLE_PRESETS не знает mythic_realism (Route C-словарь знает) — префикс пустеет; вне scope.
- TestFeedbackStore ×12 / TEMP-policy; 15×W293 visual.py; unknown-reader FK-500 — прежние зафиксированные (Route B/C/D-отчёты).
- pytest tmp_path в DSH-sandbox — policy-артефакт (обойдён в тесте собственным каталогом).

## 13. Final verdict по Route E

**Route E ЗАКРЫТ ПОЛНОСТЬЮ:**
1. Канонический путь: SceneContext (существующий) → MediaPlan (существующий Builder; custom_prompt=shot.prompt, style_override) → ExecutionDispatch (существующий; size/preferred только здесь) → существующий pipeline/provider — без новых типов/Builder'ов/контрактов.
2. Внешний контракт и исторический промпт — байт-в-байт (SHA-доказательство); регрессии нулевые (118/118 combined ×2; 63/63 пять маршрутов; 226P/4F chunk; film_endpoints 40P).
3. Dead-поля шота (camera/duration/negative) остались dead — не оживлены (GO п.4; тест-инвариант). Dead mood/quality — без изменений.
4. Ограничения соблюдены: нет второго canonical path; нет execution leakage; error-семантика прежняя (404/404/500); WorldModel/temporal read-only; A/B/C/D/schema не тронуты; БД/F-12 — не проявлялся.

**MD-3.2 ПОЛНОСТЬЮ ЗАВЕРШЁН: все 5 маршрутов (A, B, C, D, E) мигрированы на единственный canonical MediaPlan path с сохранением исторических контрактов.**

**Остаточные оговорки (не blockers):** (а) legacy-промпт-проекции (dispatch.prompt во всех маршрутах) живут до MD-5 по плану владельца; (б) dead-поля (camera/duration/negative шота; mood/quality параметров; видео-провайдер Route C) — задокументированы, оживление = отдельные решения владельца; (в) план не персистируется (MD-4/Media-Project).

---

**STOP.** Это был последний маршрут MD-3.2. Ничего следующего не начинаю. Жду вашего отдельного ACCEPT по Route E и вашего решения о следующем шаге MD-3.
