# MD-3.2 Route A — BASELINE (зафиксировано ДО миграции)

**Дата фиксации:** 2026-09-12 19:52 (TestClient + spy-провайдер + dependency_overrides — как тест-среда; скрипт `tests/_md32a_baseline_snapshot.py`).

## Endpoint + request contract (неизменны)

```
POST /book/visualize           (VisualizeResponse; auth: reader-role)
  body JSON: {chapter: int >=1, scene_id: str, reader_id?: str}
```

## Response contract — фактический снапшот (200)

```
{prompt, image_bytes, content_type}          # ровно 3 ключа (VisualizeResponse)
content_type: "image/svg+xml"                 # image_bytes: base64(SVG)
```

## Фактический исторический промпт (сцена ch.1 «Конфликт: Гиперборея vs Материальный путь Атлантиды»)

```
epic fantasy scene, Конфликт: Гиперборея vs Материальный путь Атлантиды,
harsh lighting, stormy atmosphere, clashing colors, tension, mystical landscape,
ancient world, timeless setting, symbolic themes: гиперборея, материальный_путь_атлантиды,
color palette dominated by #2C3E50, contrast, tense and volatile, unstable energy,
cinematic lighting, highly detailed, intricate details, epic composition, atmospheric
```
SHA256[:16] = `84c05d47047113b0` (контроль идентичности после миграции).

## Provider/runtime path (фактический, spy-доказательство)

```
ctx = visual_ctx_builder.build_scene_context(chapter, scene_id)      # MD-2 canonical (уже)
scene = scene_engine.get_scene(...)                                   # 404-источник истины
char_visuals/location = scene_engine.get_*_visual(...)                # genome-визуалы
prompt = prompt_builder.build_scene_prompt(scene, char_visuals, location)  # LEGACY prompt builder
image_bytes = image_provider.generate(prompt)                         # БЕЗ size/preferred!
visual_spec_hash/image_hash = sha256                                   # для reader_memory
→ VisualizeResponse{prompt, image_bytes(base64), "image/svg+xml"}
```

**Ключевые факты для миграции:**
1. Провайдер получает prompt через `generate(prompt)` — без size и preferred_provider (в отличие от Route D, где generate_with_metadata с size/preferred).
2. Промпт — исторический текст PromptBuilder (visualization/prompt_builder.py — СТАРЫЙ словарь-механизм, НЕ PromptComposer и НЕ MediaPlan).
3. 404 на несуществующую сцену (глава 99) — контракт валидатора; reader_id — сохранение visual_memory (sha256-хэши) при наличии.
4. SceneContext уже строится (MD-2), но в промпте НЕ участвует — только смысловая надстройка; в этом и состояло исключение PA-F1.

## Семантика ошибок (сохранить)

| Вход | Ответ |
|------|-------|
| chapter=99, scene_id="nope" | **404** "Scene not found" |
| корректная сцена + reader_id | 200 + visual_memory сохранён (sha256-хэши промпта/картинки) |
| валидный запрос без reader_id | 200 (память не пишется) |

## Baseline-тесты (существующие, до миграции)

test_md2_routes.py::TestRouteAVisualize: test_visualize_contract_unchanged (200 + prompt + image_bytes + content_type) · test_visualize_404_unknown_scene (404) — оба зелёные (57P).
