# Image Description — Factual Analysis

## Простыми словами

**Что было целью?** Проследить точный путь данных от сцены книги до финального промпта для генерации изображений.

**Что реально сделано?** Полный разбор всей цепочки: VisualContextBuilder → VisualContext → PromptComposer → MediaPlan.

**Что получилось?** PARTIAL — система производит РЕАЛЬНЫЙ контент, но с существенными пробелами.

**Есть ли проблемы?** Да, критические:
1. Большинство полей VisualContext остаются пустыми или содержат значения по умолчанию
2. Нет автоматического обогащения сцен описательным текстом
3. Промпты получаются "каркасными" — без детализации
4. Персонажи и локации загружаются только если они есть в VISUAL_KNOWLEDGE

**Что предлагается дальше?** Добавить автоматическое обогащение сцен через RAG и LLM-генерацию описательного текста.

---

## Техническая часть

## Investigation Chain — Полный разбор

### Step 1: VisualContextBuilder — что реально produce build_scene_context?

**Входные данные:**
```python
async def build_scene_context(
    self, 
    chapter: int,           # номер главы
    scene_id: str,          # ID сцены из genome
    time_of_day: str = "dawn",  # время дня
    epoch_id: str | None = None  # опциональная эпоха
) -> VisualContext
```

**Что загружается:**
1. **Genome** (`core/GENOME/GENOME_v1.0.0.json`) — основной источник данных
   - Сцены: `genome["modules"]["scenes"]` — ищет сцену по chapter + scene_id
   - Персонажи: `genome["modules"]["character_visuals"]` — fallback если нет в VISUAL_KNOWLEDGE
   - Места: `genome["world_entities"]` — fallback для локаций

2. **VISUAL_KNOWLEDGE** (`core/CORE/visual/VISUAL_KNOWLEDGE/*.json`) — основной источник визуальных данных
   - LOCATION_VISUALS.json — архитектура, ландшафт, атмосфера локаций
   - CHARACTER_VISUALS.json — внешность персонажей
   - ATMOSPHERES.json — типы атмосфер (sacred, pre_dawn, military, ritual, catastrophic, festive, anxious, neutral)
   - VISUAL_SYMBOLS.json — символы с визуальными описаниями
   - CAMERA_LIBRARY.json — типы камер и линз
   - STYLE_LIBRARY.json — стили генерации

**КРИТИЧЕСКИЙ ВЫВОД:** Система загружает ВСЕ данные из VISUAL_KNOWLEDGE при инициализации (строки 140-155), но использует их только если они СУЩЕСТВУЮТ в конкретных JSON-файлах.

---

### Step 2: VisualContext — 15 измерений с типами и значениями по умолчанию

| # | Поле | Тип | Значение по умолчанию | Примечание |
|---|------|-----|----------------------|------------|
| 1 | scene | SceneContext | SceneContext() | chapter=0, scene_id="", title="", description="", emotion="neutral", emotion_intensity=0.5 |
| 2 | location | LocationContext | LocationContext() | location_id="", name="", type="", architecture=ArchitectureContext(), landscape=LandscapeContext() |
| 3 | architecture | ArchitectureContext | ArchitectureContext() | style="", materials="", features=[], age="", condition="" |
| 4 | landscape | LandscapeContext | LandscapeContext() | terrain="", vegetation="", water="", sky="" |
| 5 | environment | EnvironmentContext | EnvironmentContext() | weather="clear", season="late summer", time_of_day="dawn", temperature="cool", wind="still" |
| 6 | lighting | LightingContext | LightingContext() | source="natural", direction="east, low", color="golden", intensity="soft", contrast="medium", description="" |
| 7 | palette | PaletteContext | PaletteContext() | primary=[], accents=[], contrast="warm", description="" |
| 8 | atmosphere | AtmosphereContext | AtmosphereContext() | name="neutral", light="", fog="", wind="", particles="", sound="", color_temperature="", contrast="", camera_dynamics="" |
| 9 | symbols | list[SymbolContext] | [] | Список символов с name, literal, metaphorical, spiritual, archetypal, colors, visual_elements |
| 10 | historical | HistoricalContext | HistoricalContext() | era="Bronze Age", civilization="Hyperborean", year_approx="3500 BC", cultural_notes="" |
| 11 | camera | CameraContext | CameraContext() | shot_type="wide", angle="eye_level", movement="static", lens="50mm", composition="", depth_of_field="deep", cinematic_style="" |
| 12 | style | StyleContext | StyleContext() | name="cinematic_fantasy", prefix="cinematic fantasy, epic film still, dramatic lighting", references=[], quality_suffixes=[] |
| 13 | emotion | EmotionContext | EmotionContext() | name="neutral", visual="balanced natural lighting, clear visibility", suffix="peaceful and clear", intensity=0.5 |
| 14 | characters | list[CharacterVisualContext] | [] | character_id, name, age_range, face, hair, eyes, build, clothing, accessories, mannerisms, movement, appearance_summary |
| 15 | negative_prompt | NegativePromptContext | NegativePromptContext() | base=["blurry", "low quality", ...], extra=[] |

**КРИТИЧЕСКИЙ ВЫВОД:** Все 15 измерений имеют значения по умолчанию, которые являются пустыми строками или списками. Система НЕ автоматически заполняет поля.

---

### Step 3: PromptComposer — что реально produce?

**ComfyUITemplate.render(ctx) — АКТУАЛЬНЫЙ ШАБЛОН:**

```python
def render(self, ctx) -> str:
    parts = []
    
    # 1. Style prefix (ВСЕГДА есть по умолчанию)
    if ctx.style.prefix:  # "cinematic fantasy, epic film still, dramatic lighting"
        parts.append(ctx.style.prefix)
    
    # 2. Scene title (ТОЛЬКО если есть в genome)
    if ctx.scene.title:
        parts.append(ctx.scene.title)
    
    # 3. Location architecture (ТОЛЬКО если есть в VISUAL_KNOWLEDGE)
    if ctx.architecture.style:
        parts.append(ctx.architecture.style)
    elif ctx.location.name:
        parts.append(f"ancient {ctx.location.name}")
    
    # 4. Landscape (ТОЛЬКО если есть в VISUAL_KNOWLEDGE)
    if ctx.landscape.terrain:
        parts.append(ctx.landscape.terrain)
    if ctx.landscape.vegetation:
        parts.append(ctx.landscape.vegetation)
    
    # 5. Atmosphere (ТОЛЬКО если есть в VISUAL_KNOWLEDGE)
    if ctx.atmosphere.light:
        parts.append(ctx.atmosphere.light)
    elif ctx.lighting.description:
        parts.append(ctx.lighting.description)
    
    # 6. Fog and particles (ТОЛЬКО если есть)
    if ctx.atmosphere.fog:
        parts.append(ctx.atmosphere.fog)
    if ctx.atmosphere.particles:
        parts.append(ctx.atmosphere.particles)
    
    # 7. Emotion (ВСЕГДА есть по умолчанию)
    if ctx.emotion.visual:  # "balanced natural lighting, clear visibility"
        parts.append(ctx.emotion.visual)
    
    # 8. Characters (ТОЛЬКО если есть appearance_summary)
    for char in ctx.characters:
        if char.appearance_summary:
            parts.append(char.appearance_summary)
    
    # 9. Palette (ТОЛЬКО если есть description)
    if ctx.palette.description:
        parts.append(ctx.palette.description)
    
    # 10. Camera (composition ТОЛЬКО если есть)
    if ctx.camera.composition:
        parts.append(ctx.camera.composition)
    if ctx.camera.shot_type:  # "wide" → "wide"
        parts.append(ctx.camera.shot_type.replace("_", " "))
    
    # 11. Symbols (ТОЛЬКО literal, макс 3)
    for sym in ctx.symbols[:3]:
        if sym.literal:
            parts.append(sym.literal)
    
    # 12. Quality suffixes (пустой список по умолчанию)
    for q in ctx.style.quality_suffixes:
        if q not in parts:
            parts.append(q)
    
    # Deduplicate and join
    seen = set()
    deduped = []
    for p in parts:
        key = p.lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    
    return ", ".join(deduped)
```

**ПРИМЕРЫ ВЫВОДА:**

1. **Для сцены "test_meeting" (chapter=1, scene_id="test_meeting"):**
   - Genome: title="Встреча у костра", location="Аркаим", emotion="ceremonial_warm", characters=["Велик", "Учитель"]
   - VISUAL_KNOWLEDGE: Аркаим есть в LOCATION_VISUALS, Велик и Учитель есть в CHARACTER_VISUALS
   
   **Результат:**
   ```
   cinematic fantasy, epic film still, dramatic lighting, 
   Встреча у костра, 
   circular fortified settlement, Bronze Age, concentric walls, 
   rolling Ural steppe hills, river valley, elevated plateau, 
   wild steppe grass, scattered birch groves, medicinal herb gardens, ancient oak trees, 
   warm golden, divine rays filtering through ancient stones, halo effects on sacred objects, 
   thin ethereal mist rising slowly from ground, clinging to stone surfaces, 
   floating dust motes in light beams, golden sparks of spiritual energy, 
   warm firelight, intimate atmosphere, soft golden glow, 
   Велик, tall, lean, athletic — warrior-philosopher physique, dark brown, shoulder-length, often tied back with leather cord, 
   Учитель, tall, thin but dignified, upright posture despite age, long silver-white, flowing freely, 
   palette of Аркаим, 
   wide
   ```

2. **Для сцены "conflict_гиперборея_материальный_путь_атлантиды" (chapter=1):**
   - Genome: title="Конфликт: Гиперборея vs Материальный путь Атлантиды", location="граница миров", emotion="конфликт", characters=[]
   - VISUAL_KNOWLEDGE: "граница миров" НЕТ в LOCATION_VISUALS, персонажей нет
   
   **Результат:**
   ```
   cinematic fantasy, epic film still, dramatic lighting, 
   Конфликт: Гиперборея vs Материальный путь Атлантиды, 
   balanced natural lighting, clear visibility, 
   wide
   ```
   
   **КРИТИЧЕСКИЙ ПРОБЕМ:** Почти пустой промпт! Нет описания локации, атмосферы, символов.

---

### Step 4: MediaPlanBuilder.build_image_plan — маппинг полей

**Маппинг VisualContext → MediaPlan:**

| MediaPlan поле | Источник | Значение по умолчанию |
|----------------|----------|----------------------|
| plan_id | uuid4 | "plan_" + random |
| media_kind | параметр | "image" |
| intent | параметр | "key_frame" |
| structured_prompt | PromptComposer.compose(ctx) | Весь текст выше |
| prompt | structured_prompt или custom_prompt | Текст промпта |
| negative_constraints | PromptComposer.compose_negative(ctx) | ["blurry", "low quality", ...] |
| characters | ctx.characters[].appearance_summary | [] если нет персонажей |
| location | ctx.location.location_id, name, type, architecture.style, landscape.terrain | Все пустые если нет в VISUAL_KNOWLEDGE |
| visual_style | style_override или ctx.style.name | "cinematic_fantasy" |
| atmosphere | ctx.atmosphere.name | "neutral" |
| camera | ctx.camera.shot_type, angle, movement, composition | shot_type="wide", angle="eye_level", movement="static", composition="" |
| constraints | ctx.scene.meaning_tags | [] если нет тегов |
| source_refs | scene_extras.source_refs | scene_id, chapter, character_ids, location_id |
| temporal_context | scene_extras.temporal | None если нет эпохи |
| provenance | scene_extras.temporal.provenance | [] |
| lineage | параметры | parent_plan_id=None, derivation="initial", created_from="scene_context" |

---

### Step 5: Анализ реальных данных — что реально rich vs thin?

**Проверка сцены "test_meeting" (chapter=1, scene_id="test_meeting"):**

| Поле | Значение в genome | Richness |
|------|-------------------|----------|
| scene.title | "Встреча у костра" | ✅ Rich |
| scene.emotion | "ceremonial_warm" | ✅ Rich |
| scene.meaning_tags | ["знание", "передача", "мудрость", "предназначение"] | ✅ Rich |
| scene.characters | ["Велик", "Учитель"] | ✅ Rich |
| scene.location | "Аркаим" | ✅ Rich |

**Проверка VISUAL_KNOWLEDGE для этой сцены:**

| Поле | Значение | Richness |
|------|----------|----------|
| LOCATION_VISUALS["Аркаим"] | 29 строк описания | ✅ Rich |
| CHARACTER_VISUALS["Велик"] | 18 строк описания | ✅ Rich |
| CHARACTER_VISUALS["Учитель"] | 16 строк описания | ✅ Rich |
| ATMOSPHERES["sacred"] | 10 строк описания | ✅ Rich |
| VISUAL_SYMBOLS | 6 символов с описаниями | ✅ Rich |

**Проверка сцены "conflict_гиперборея_материальный_путь_атлантиды":**

| Поле | Значение в genome | Richness |
|------|-------------------|----------|
| scene.title | "Конфликт: Гиперборея vs Материальный путь Атлантиды" | ✅ Rich |
| scene.emotion | "конфликт" | ✅ Rich |
| scene.meaning_tags | ["конфликт:гиперборея", "конфликт:материальный_путь_атлантиды"] | ✅ Rich |
| scene.characters | [] | ❌ Empty |
| scene.location | "граница миров" | ⚠️ Thin (нет в VISUAL_KNOWLEDGE) |

**КРИТИЧЕСКИЙ ВЫВОД:** Система имеет ПОЛНЫЕ данные в VISUAL_KNOWLEDGE для ключевых локаций и персонажей, но:
1. Автоматически НЕ обогащает сцены без явных привязок
2. Не использует RAG для поиска релевантных описаний
3. Не генерирует описательный текст через LLM

---

## Финальный вывод

### Is Image Description fully formed by existing system?

**PARTIALLY — система производит РЕАЛЬНЫЙ контент, но с существенными пробелами.**

**Fields that ARE populated with real descriptive content:**

| Field | Source | Example value | Richness |
|-------|--------|---------------|----------|
| scene.title | Genome scenes | "Встреча у костра" | Rich |
| scene.emotion | Genome scenes | "ceremonial_warm" | Rich |
| scene.meaning_tags | Genome scenes | ["знание", "передача", "мудрость"] | Rich |
| style.prefix | StyleContext default | "cinematic fantasy, epic film still, dramatic lighting" | Rich |
| emotion.visual | EMOTION_TO_VISUAL mapping | "warm firelight, intimate atmosphere, soft golden glow" | Rich |
| location.architecture.style | LOCATION_VISUALS.json | "circular fortified settlement, Bronze Age, concentric walls" | Rich |
| location.landscape.terrain | LOCATION_VISUALS.json | "rolling Ural steppe hills, river valley, elevated plateau" | Rich |
| location.landscape.vegetation | LOCATION_VISUALS.json | "wild steppe grass, scattered birch groves, medicinal herb gardens" | Rich |
| atmosphere.light | ATMOSPHERES.json | "warm golden, divine rays filtering through ancient stones" | Rich |
| atmosphere.fog | ATMOSPHERES.json | "thin ethereal mist rising slowly from ground" | Rich |
| characters[].appearance_summary | CHARACTER_VISUALS.json | "Велик, tall, lean, athletic — warrior-philosopher physique" | Rich |

**Fields that are NOT populated or use defaults:**

| Field | Default value | Why empty |
|-------|---------------|-----------|
| architecture.style | "" | Если локации нет в LOCATION_VISUALS |
| architecture.materials | "" | Если локации нет в LOCATION_VISUALS |
| landscape.terrain | "" | Если локации нет в LOCATION_VISUALS |
| landscape.vegetation | "" | Если локации нет в LOCATION_VISUALS |
| atmosphere.light | "" | Если атмосфера не определена в ATMOSPHERES |
| atmosphere.fog | "" | Если атмосфера не определена в ATMOSPHERES |
| camera.composition | "" | Всегда пустой по умолчанию |
| palette.description | "" | Всегда пустой по умолчанию |
| historical.cultural_notes | "" | Если нет в world_entities |
| symbols[].literal | "" | Если символ не в VISUAL_SYMBOLS |

**PromptComposer output example for real scene:**

Для сцены "test_meeting" (chapter=1):
```
cinematic fantasy, epic film still, dramatic lighting, 
Встреча у костра, 
circular fortified settlement, Bronze Age, concentric walls, 
rolling Ural steppe hills, river valley, elevated plateau, 
wild steppe grass, scattered birch groves, medicinal herb gardens, ancient oak trees, 
warm golden, divine rays filtering through ancient stones, halo effects on sacred objects, 
thin ethereal mist rising slowly from ground, clinging to stone surfaces, 
floating dust motes in light beams, golden sparks of spiritual energy, 
warm firelight, intimate atmosphere, soft golden glow, 
Велик, tall, lean, athletic — warrior-philosopher physique, dark brown, shoulder-length, often tied back with leather cord, 
Учитель, tall, thin but dignified, upright posture despite age, long silver-white, flowing freely, 
palette of Аркаим, 
wide
```

**КРИТИЧЕСКИЙ ПРОБЕМ:** Для сцен без явных привязок к локациям/персонажам в VISUAL_KNOWLEDGE промпт получается почти пустым:
```
cinematic fantasy, epic film still, dramatic lighting, 
Конфликт: Гиперборея vs Материальный путь Атлантиды, 
balanced natural lighting, clear visibility, 
wide
```

---

## Specific gaps:

1. **Нет автоматического обогащения сцен** — если сцена ссылается на локацию/персонажа, которых нет в VISUAL_KNOWLEDGE, поля остаются пустыми
2. **Нет RAG-поиска** — система не ищет релевантные описания в knowledge base
3. **Нет LLM-генерации** — не генерирует описательный текст для отсутствующих элементов
4. **Нет валидации полноты** — VisualValidator проверяет только наличие title, но не полноту описания
5. **Нет fallback-стратегий** — если LOCATION_VISUALS не содержит локации, нет попытки найти похожую
6. **camera.composition всегда пустой** — не генерируется автоматически
7. **palette.description всегда пустой** — не генерируется автоматически
8. **historical.cultural_notes пустой** — если нет в world_entities

---

## Рекомендации:

1. **Добавить RAG-обогащение** — искать релевантные описания в knowledge base для отсутствующих элементов
2. **Добавить LLM-генерацию** — генерировать описательный текст для отсутствующих полей
3. **Добавить валидацию полноты** — проверять заполненность ключевых полей перед генерацией
4. **Добавить fallback-стратегии** — искать похожие локации/персонажей если точных нет
5. **Генерировать camera.composition** — на основе shot_type и эмоции
6. **Генерировать palette.description** — на основе location и scene
7. **Генерировать historical.cultural_notes** — на основе location и world_entities
