# MD-3.2 Route B — BASELINE (зафиксировано ДО миграции)

**Дата фиксации:** 2026-09-12 20:15 (TestClient + spy-провайдер + dependency_overrides; скрипт-снимок удалён после фиксации).

## Endpoint + request contract (неизменны)

```
POST /book/visualize/epoch/{epoch_id}     (VisualizeResponse; auth: reader-role)
  body JSON: {reader_id?: str}            # EpochVisualRequest (единственное поле)
```

## Response contract — фактический снапшот (200, epoch_id=arkaim_era)

```
{prompt, image_bytes, content_type}          # ровно 3 ключа (VisualizeResponse)
content_type: "image/svg+xml"                 # image_bytes: base64(SVG)
```

## Фактический исторический промпт (epoch_id="arkaim_era")

```
epic fantasy scene, Эпоха Аркаима, Эпоха расцвета Аркаима — центра духовного знания.,
dramatic lighting, epic revelation scene, grand unveiling, professional photography,
8k, sharp focus, beautiful detailed environment
```
SHA256[:16] = `f460318283a4cbf8` (контроль идентичности после миграции).

## Epoch/temporal input — фактический источник (существующий, read-only)

```
WorldModel.get_temporal_context(epoch_id) → {epoch: {name_ru, description,
  civilizations_active…}, characters, events, technologies, temporal_node,
  character_count, event_count}
visual_ctx_builder.build_scene_context_for_epoch(epoch_id, time_of_day="dawn"):
  SceneContext(title=name_ru) · scene.description · historical(civilizations) ·
  environment/lighting/palette/atmosphere/camera(wide 24mm)/style/emotion ·
  temporal = _temporal_ref_from_epoch(epoch_id) · source_refs(entity_refs=[epoch_id])
  ДЛЯ НЕСУЩЕСТВУЮЩЕЙ эпохи: ctx с пустым temporal (is_temporal=False) —
  маршрут обязан сам ответить 404 (контракт прежний).
```

## Provider/runtime path (фактический, spy-доказательство)

```
ctx = build_scene_context_for_epoch(epoch_id)                  # MD-2 canonical (уже)
temporal = ctx.scene_extras.temporal; if not temporal.is_temporal → 404
wm = WorldModel.load(); context = wm.get_temporal_context(epoch_id)
prompt = prompt_builder.build_epoch_prompt(epoch_id, context)   # LEGACY prompt builder
image_bytes = image_provider.generate(prompt)                   # БЕЗ size/preferred
→ VisualizeResponse{prompt, image_bytes(base64), "image/svg+xml"}
```

**Ключевые факты для миграции:**
1. Провайдер получает prompt через `generate(prompt)` — без size/preferred (как Route A).
2. Промпт — исторический текст PromptBuilder.build_epoch_prompt (visualization/prompt_builder.py — СТАРЫЙ механизм).
3. 404 на несуществующую эпоху («Epoch 'x' not found») — источник истины: пустой temporal в WorldModel.
4. SceneContext строится canonical-билдером (MD-2) — как смысловая надстройка; в историческом промпте не участвует (то же исключение, что было у A — закрывается той же схемой: план + legacy-проекция).
5. **Все параметры, реально доходящие до execution:** ТОЛЬКО prompt (строка). Ни size, ни provider, ни иных — generate(prompt) с дефолтами провайдера.

## Семантика ошибок (сохранить)

| Вход | Ответ |
|------|-------|
| epoch_id="nonexistent_epoch" | **404** "Epoch '…' not found" |
| epoch_id="arkaim_era" | 200 + исторический промпт эпохи |
| body {} (без reader_id) | 200 (reader_id в Route B не используется для памяти — только в request-модели) |

## Baseline-тесты (существующие, до миграции)

test_md2_routes.py::TestRouteBVisualizeEpoch: test_epoch_contract_unchanged (200 + prompt + image_bytes) · test_epoch_404_unknown (404) · test_world_model_not_mutated (read-only WorldModel — инвариант миграции B) — все зелёные (57P).
