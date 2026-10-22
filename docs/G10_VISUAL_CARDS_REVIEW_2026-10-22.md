# Г10: Компактный список 8 визуальных карточек

**Дата:** 2026-10-22
**Статус:** `requires_author_review=True`, `is_canon=False`, `category=ARTISTIC_MODEL`
**Реестр:** `core/CORE/narrative_engine/provenance/knowledge_classification.py` — все 8 записей классифицированы как `ARTISTIC_MODEL`, `source_path` указан.
**Происхождение:** ИИ-агент (план Visual Intelligence от 19.07.2026). Ни один скрипт не генерирует эти файлы. `_provenance_metadata` на уровне файлов и записей отсутствует полностью.

---

| № | Файл | Содержимое (ключи) | Источник / происхождение | Что требует подтверждения |
|---|---|---|---|---|
| 1 | `LOCATION_VISUALS.json` | Аркаим, Гиперборея, Океания, Подземный город, Святилище (по 7 полей на каждое) | ИИ-агент, план Visual Intelligence; не выведены из книги | each location: соответствует ли визуальная интерпретация канону? (см. также G10-атлантида-океания конфликт) |
| 2 | `CHARACTER_VISUALS.json` | Велик, Учитель, Световит (по 11 полей: возраст, одежда, палитра, аксессуары…) | ИИ-агент; антураж придуман, не из книги | каждый персонаж: возраст, одежда, палитра — согласуются ли с каноническими описаниями? |
| 3 | `ATMOSPHERES.json` | sacred, pre_dawn, military, ritual, catastrophic, festive, anxious, neutral (по 8 полей: lighting, color, mood…) | ИИ-агент; атмосферные модели — художественные допущения | каждая атмосфера: уместна ли для сценария? не противоречит ли тону книги? |
| 4 | `VISUAL_SYMBOLS.json` | stone_circle, fire_pit, celestial_alignment, runic_inscription, sacred_geometry, water_and_depth (по 6 полей) | ИИ-агент; символы придуманы | каждый символ: есть ли опора в книге или это свободная интерпретация? |
| 5 | `CAMERA_LIBRARY.json` | shot_types (7), movements (8), transitions (6), compositions (6) | ИИ-агент; технический словарь режиссёра | каждый тип съёмки: уместен ли для стиля книги? не избыточен ли? |
| 6 | `STYLE_LIBRARY.json` | cinematic_fantasy, realistic, ethereal, dark_gothic, watercolor, oil_painting (по 6 полей: prompt-фрагменты) | ИИ-агент; стилистические пресеты | каждый стиль: соответствует ли визуальному тону книги? не конфликтует ли с другими? |
| 7 | `SHOT_LIBRARY.json` | establishing_dawn, character_approach, ritual_circle, emotional_closeup, epic_reveal, tension_build, panoramic_landscape, firelight_intimate (по 8 полей) | ИИ-агент; библиотеки shots — художественные шаблоны | каждый shot: уместен ли в контексте сценария? не дублирует ли другие? |
| 8 | `VIDEO_RULES.json` | rhythm, continuity_rules, transition_rules, motion_rules, quality_rules | ИИ-агент; правила видеопроизводства | каждое правило: практично ли? не конфликтует ли с production-ограничениями? |

---

**Общее:** все 8 файлов — `ARTISTIC_MODEL`, ни один не имеет `_provenance_metadata`, ни один не связан с каноническим источником. Все 8 требуют авторского подтверждения перед использованием в медиа-пайплайне.

**Конкретный конфликт (отдельно):** `LOCATION_VISUALS.json` содержит две карточки на одно место — «Атлантида» и «Океания» — после решения G6 (`PRESERVE_UNCHANGED`) и alias-решения они дублируют друг друга. См. `docs/VISUAL_CARDS_ATLANTIDA_OCEANIA_2026-10-21.md`.

**Что сделаю после ответа:** обновлю `_provenance_metadata` на каждом файле (добавлю `category`, `source_level`, `notes`, `enriched_at`), сниму/оставлю `requires_author_review` по вашему слову, обновлю guard-тест в `test_provenance_registry_consistency.py`.
