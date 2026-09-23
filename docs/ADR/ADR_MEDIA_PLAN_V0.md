# ADR — MEDIA PLAN v0

**Тип:** Architecture Decision Record
**Дата:** 2026-09-11
**Статус:** ACCEPTED (owner GO на MD-3 implementation; решения зафиксированы владельцем до кода)
**Контекст:** MD-3 «MediaPlan Contract v0» по Roadmap Delta MD-1 (MEDIA_DIRECTION_FOUNDATION §Roadmap). Предшественники: ADR_ARKAIM_MEDIA_BOUNDARY (ACCEPTED), MD-2 Scene Context Consolidation (CLOSED), MD3_PRE_IMPLEMENTATION_AUDIT (принят владельцем).
**Owner decisions:** 10 решений владельца зафиксированы в GO-команде на MD-3 implementation (2026-09-11) и отражены ниже как обязательные.

---

## Простыми словами

1. **Решение** — в Аркаиме появляется один доменный контракт **MediaPlan v0** — «задание на генерацию картинки или видео»: кто в кадре, где, когда (эпоха), какой стиль, какие ограничения, откуда мы это знаем (provenance) и от какого плана этот план происходит (lineage). Контракт НЕ знает, как генерировать: в нём нет модели, шагов, сида, провайдера — это дело Media-стороны.

2. **Границы** — MediaPlan строится ТОЛЬКО из canonical Scene Context (VisualContext + MD-2-расширения temporal/source_refs/integrity). Никакого второго SceneContext, никакого параллельного промпт-стека, никакого фронтенда в этом этапе.

3. **Временный мост** — существующие провайдеры живут на старом конверте (текст промпта + размер + провайдер). Их трогать нельзя. Поэтому между планом и провайдерами — **ExecutionDispatch**: временный мост, который переводит план в текущий конверт провайдера. Мост явно помечен как временный и удаляется в MD-5, когда Media-проект начнёт принимать планы напрямую.

4. **Честность** — мёртвый параметр quality (MP-F1) НЕ оживляется и НЕ входит в план; негативный промпт — смысловое поле плана (constraints), а не починка старой цепочки; пробитие его до провайдеров — вне MD-3.

---

## Decision 1 — MediaPlan v0: отдельный доменный контракт

MediaPlan — НОВЫЙ доменный контракт, НЕ новый SceneContext. Canonical Scene Context остаётся существующим `VisualContext` (MD-2-расширения: `temporal`, `source_refs`, `integrity`). MediaPlan — проекция SceneContext на один носитель (image|video): N планов на одну сцену.

**Размещение:** `core/CORE/media_plan/` — канонический доменный слой Arkaim рядом с visual/media domain; НЕ смешивается с execution/runtime (visual_assets остаётся execution-legacy до MD-4/5). Домен-модуль не импортирует providers/visual_assets/pipeline — только SceneContext-слой и narrative-протоколы.

## Decision 2 — Запрет execution-семантики

MediaPlan v0 НЕ содержит: `model`, `checkpoint`, `steps`, `cfg`, `sampler`, `seed`, `workflow`, node graph, `provider`, `backend`, ComfyUI-specific fields, execution settings. Запрет — тест-инвариант (BANNED ∩ fields = ∅). План выражает интент; механику выбирает исполнитель.

**quality (MP-F1):** мёртвый параметр (фронт отправляет, до исполнителя не доходит — цепочка провайдеров его не передаёт). НЕ оживляется, НЕ протаскивается через провайдеры, НЕ включается в MediaPlan ради совместимости. Зафиксирован как documented gap (MD3_PRE §MP-F1): управление качеством — решение MD-4/5 на стороне Media-проекта.

**negative prompt:** существует в MediaPlan как `negative_constraints: list[str]` (смысловые запреты — утверждённая спецификация плана). Старая provider-цепочка НЕ чинится ради MD-3: до провайдеров негатив пробивается в MD-4/5 (MP-F2 остаётся documented gap).

## Decision 3 — Provenance и lineage обязательны

- **provenance наследуется:** план получает provenance сцены/эпохи из SceneContext (`scene_extras.temporal.provenance` + канонический ProvenanceTag-протокол). RECONSTRUCTION-эпоха → план с RECONSTRUCTION (ADR_ARKAIM_MEDIA_BOUNDARY, инвариант 7). План не выдумывает provenance — только проекция.
- **lineage:** `PlanLineage {parent_plan_id, derivation, created_from}` — derived/regenerate план обязан ссылаться на родителя; regenerate НЕ может молча создать независимый план без parent reference (при наличии известного родителя). Lineage — это родословная ЗАДАНИЯ, не storage/execution metadata: никаких статусов исполнения, файлов, очередей, attempt-счётчиков в lineage.
- **Immutable-паттерн:** regenerate создаёт НОВЫЙ план с parent-ссылкой (не мутирует старый) — как TemporalSceneRef в MD-2.

## Decision 4 — ExecutionDispatch: временный migration bridge

`ExecutionDispatch` — dataclass в media_plan-слое (не домен-контракт): {prompt, negative, size, preferred_provider, duration, fps} — legacy execution mapping, необходимый существующим провайдерам. Поля dispatch НЕ являются частью MediaPlan. Dispatch:
- явно помечен docstring как «TEMPORARY MIGRATION BRIDGE — REMOVE IN MD-5»;
- единственный способ дотянуть план до текущих провайдеров в переходный период;
- удаляется/заменяется в MD-5, когда Media-проект принимает план напрямую по контракту.

## Decision 5 — PA-F1 закрывается на уровне MD-3

Route A (`/visualize`) строит MediaPlan из canonical SceneContext (поток данных консолидирован через план), при этом существующий текстовый prompt contract сохраняется (byte-identical рендер прежним PromptBuilder-контрактом). Не возвращаться к старой реализации ради полного переписывания prompt path. Смена промпт-контракта A — отдельное решение владельца (вне MD-3).

## Decision 6 — Frontend не меняется

Существующие request/UI contracts сохранены. MediaPlan строится через backend Builder/adapter. Никакого frontend redesign в MD-3.

## Decision 7 — Порядок и границы реализации

MD-3.1 (контракт+builder+тесты) → STOP → MD-3.2 (пять маршрутов по одному, каждый со STOP) → MD-3.3 (deprecation+schema+docs). Массовая миграция запрещена. STICTLY FORBIDDEN (MD-3 scope): MD-4, Media Project bootstrap, перенос/изменение ComfyUI, MD-5 de-publication, C2, F-12, SharedSettings, frontend redesign, temporal/World Model изменения, массовый legacy cleanup, оживление quality, изменение provider semantics вне adapter/dispatch, новый LLM path, Audio-implementation, параллельный SceneContext, параллельная prompt architecture. Если что-то из этого понадобится — blocking finding, НЕ расширение scope.

## Decision 8 — Версионирование

`plan_version: "0.1.0"` в каждом плане (semver-минимум). JSON-Schema-экспорт `SCHEMAS/MEDIA_PLAN.schema.json` (draft-07 — прецедент SCHEMAS/*.schema.json). Контракт эволюционирует отдельно от обоих проектов (ADR_ARKAIM_MEDIA_BOUNDARY Decision 4г): additive → минор, несовместимые → мажор (точка пересмотра MD-4/5).

## Backward compatibility

MD-3.1 не меняет ни одного существующего маршрута/схемы/провайдера: новый модуль + ADR + JSON-Schema + тесты — additive. Legacy-входы (VisualAsset.generation/GenerationParams, dict-сцены) продолжают работать до MD-3.3 deprecation-меток. Внешние response contracts не меняются на всём MD-3.

## Итог

MediaPlan v0 — единственный доменный контракт задания: строится из SceneContext, несёт provenance+lineage, не знает исполнителя. ExecutionDispatch — явный временный мост к legacy-провайдерам (смерть в MD-5). Quality/negative-пробитие — documented gaps, не scope. Все 10 owner decisions зафиксированы и обязательны.
