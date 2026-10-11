# Работа с ComfyUI в проекте «Наследие Аркаима»

> Руководство по установке, подключению, настройке и эксплуатации ComfyUI
> для генерации изображений из Visual Genome.

---

## 1. Что такое ComfyUI и зачем он нужен

**ComfyUI** — node-based интерфейс для Stable Diffusion. В отличие от Automatic1111, где всё завязано на одну форму с полями, ComfyUI позволяет собирать **визуальный пайплайн** из нод:

- Загрузка модели (Checkpoint, LoRA, ControlNet)
- Формирование промпта (CLIPTextEncode)
- Управление размером, seed, сэмплером
- Постобработка (VAE, upscale, masking)
- Сохранение результата

В проекте `ComfyUIProvider` — основной ImageProvider. Он передаёт промпт от `PromptBuilder` в ComfyUI, ждёт результат и возвращает его как `bytes`.

**Почему ComfyUI, а не Automatic1111:**
- Воркфлоу — JSON, можно хранить и версионировать в `GENOME/workflows/`
- Легко переключать стили / модели простой сменой воркфлоу
- Асинхронный API — не блокирует сервер
- ControlNet, IP-Adapter, LoRA — всё подключается через ноды в воркфлоу, без доработки кода

---

## 2. Установка ComfyUI

### 2.1 Базовая установка

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Установка модели

Скачай модель (например, SDXL или любую другую) в папку `models/checkpoints/`:

- `sd_xl_base_1.0.safetensors` — базовая SDXL (рекомендуется)
- `sd_xl_refiner_1.0.safetensors` — рефайнер для SDXL
- Любая другая: `dreamshaperXL.safetensors`, `juggernautXL.safetensors` и т.д.

**Где брать:** CivitAI (рекомендуется) или Google Drive.

### 2.3 Запуск

```bash
python main.py
```

По умолчанию ComfyUI встаёт на `http://127.0.0.1:8188`.

Открой браузер — должен быть пустой холст для создания воркфлоу.

### 2.4 Проверка, что ComfyUI доступен проекту

```bash
curl http://127.0.0.1:8188/system_stats
```

Если вернулся JSON — ComfyUI работает. Наш сервер сам найдёт его при запуске.

---

## 3. Архитектура подключения

```
Книга / Visual Genome
        │
        ▼
  PromptBuilder.build_full_prompt_pair()
        │
        ▼
  (positive_prompt, negative_prompt)  ← строка до 1500 символов
        │
        ▼
  ComfyUIProvider.generate()
        │
        ├── Загрузить воркфлоу (JSON из GENOME/workflows/)
        ├── Инжектировать промпты в CLIPTextEncode ноды
        ├── Инжектировать размер в EmptyLatentImage
        ├── Инжектировать seed в KSampler
        │
        ├── POST /prompt  →  {"prompt": {...workflow...}}
        │         │
        │         ▼
        │   Ответ: {"prompt_id": "abc-123"}
        │
        ├── poll /history/abc-123  ← каждую секунду
        │         │
        │         ▼
        │   Ответ: {"abc-123": {"outputs": {"9": {"images": [...]}}}}
        │
        ├── GET /view?filename=...  →  загрузить PNG
        │
        ▼
  bytes (PNG) → пользователю / в файл
```

### Цепочка провайдеров

В `runtime/core/adc_deps.py`:

```python
ImageProviderChain([ComfyUIProvider(), MockImageProvider()])
```

- **ComfyUIProvider** — первый в цепочке. Если ComfyUI запущен — генерирует изображение.
- **MockImageProvider** — fallback. Если ComfyUI недоступен — возвращает SVG-заглушку с текстом "Mock Visualization". Сервер не падает.

---

## 4. Воркфлоу (управление стилями и моделями)

### 4.1 Дефолтный воркфлоу

При первом запуске проекта создаётся `GENOME/workflows/default.json`:

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": 42, "steps": 30, "cfg": 7.0,
      "sampler_name": "euler", "scheduler": "normal",
      "denoise": 1.0, "model": ["4", 0],
      "positive": ["6", 0], "negative": ["7", 0],
      "latent_image": ["5", 0]
    }
  },
  "4": { "class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"} },
  "5": { "class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1} },
  "6": { "class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]} },
  "7": { "class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality", "clip": ["4", 1]} },
  "8": { "class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]} },
  "9": { "class_type": "SaveImage", "inputs": {"filename_prefix": "arkaim", "images": ["8", 0]} }
}
```

Он содержит минимально необходимый набор нод:
- `CheckpointLoaderSimple` — модель
- `CLIPTextEncode` ×2 — позитивный и негативный промпт
- `EmptyLatentImage` — размер
- `KSampler` — сэмплер
- `VAEDecode` — декодирование
- `SaveImage` — сохранение

### 4.2 Создание своего воркфлоу

Хочешь другую модель, LoRA, ControlNet или просто другой сэмплер — делаешь воркфлоу визуально в ComfyUI:

1. Открой `http://127.0.0.1:8188` в браузере
2. Собери нужный пайплайн через ноды (Drag & Drop)
3. Настрой модель, сэмплер, LoRA, ControlNet, стиль — что угодно
4. В меню ComfyUI: **Save → Save (API Format)**
5. Сохрани JSON-файл в `GENOME/workflows/` с осмысленным именем

Примеры имён:
- `cinematic.json` — кинематографичный стиль
- `watercolor.json` — акварельный стиль
- `sdxl_realistic.json` — реализм на SDXL
- `sketch.json` — карандашный рисунок

### 4.3 Переключение между воркфлоу

В коде:

```python
provider = ComfyUIProvider(base_url="http://127.0.0.1:8188", workflow_name="cinematic.json")
# или динамически:
provider.set_workflow("watercolor.json")
```

Из Web UI — будет выпадающий список со всеми файлами из `GENOME/workflows/`.

### 4.4 Важные правила для воркфлоу

Чтобы `ComfyUIProvider` правильно инжектил промпты, в воркфлоу **должны быть**:

| Нода | class_type | Назначение |
|------|-----------|-----------|
| CLIPTextEncode | `CLIPTextEncode` | Первая = positive, вторая = negative |
| EmptyLatantImage | `EmptyLatentImage` | Устанавливается ширина/высота |
| KSampler | `KSampler` | Устанавливается seed |

Если в воркфлоу нет CLIPTextEncode — промпт не инжектится.  
Если в воркфлоу несколько KSampler — seed ставится во все.

Всё остальное (LoRA, ControlNet, IP-Adapter, upscale, тайлинг) — любые дополнительные ноды. Они **не трогаются**.

### 4.5 Примеры воркфлоу

**SDXL с рефайнером:**

```
CheckpointLoader (SDXL base) → CLIPTextEncode (pos/neg)
                                    ↓
CheckpointLoader (Refiner)  → К-Sampler  → VAE Decode → Save
                                    ↓
                             EmptyLatantImage
```

**Cinematic LoRA:**

Всё как в дефолтном, но добавлена нода `LoRALoader` между `CheckpointLoaderSimple` и `KSampler`.

---

## 5. PromptBuilder → ComfyUI: что уходит в промпт

### 5.1 Формат промпта

`PromptBuilder.build_full_prompt_pair()` возвращает **кортеж** `(positive, negative)`:

**Positive prompt** (пример, 1447 символов):
```
epic fantasy scene, Встреча у костра, warm torchlight, ceremonial glow, amber tones, ritual atmosphere, Велик. 30-35. атлетичное. короткие русые. зелёные. wearing кожаный доспех с бронзовыми накладками, тёмно-зелёный шерстяной плащ, кожаные штаны, высокие сапоги. with серебряный амулет-оберег с руной, поясной нож, кожаная сумка с картой. color palette of dark brown, #2F4F4F, golden amber and #6B8E23. cinematic lighting, heroic pose, natural outdoor, Учитель. 70+. худощавое. длинные седые. светло-голубые. wearing белые льняные одежды до пола, коричневый шерстяной плащ с капюшоном, деревянный посох. with резной посох из корня, кожаная книга в переплёте, мешочек с травами. color palette of white and dark brown. soft light, wise expression, ethereal glow, ancient stone temple, weathered pillars, sacred geometry, moss-covered stones, каменные круги с бронзовыми символами, мистическая, священная, предрассветный туман, золотой час, первые лучи солнца пробиваются сквозь каменный круг, длинные тени, color palette of golden amber, dark brown, #708090 and warm beige, symbolic themes: знание, передача, мудрость, предназначение, golden hour, sacred and ritualistic, reverent atmosphere, cinematic lighting, highly detailed, intricate details, epic composition, atmospheric
```

**Negative prompt** (по умолчанию):
```
blurry, low quality, cartoon, anime, oversaturated, ugly, deformed, distorted, bad anatomy, watermark, text, extra limbs, fused fingers, too many fingers, worst quality, low resolution, grainy, jpeg artifacts
```

### 5.2 Что откуда берётся

| Часть промпта | Источник в геноме | Пример |
|--------------|-------------------|--------|
| `epic fantasy scene, {title}` | `scene.title` | `Встреча у костра` |
| `{emotion_visual}` | `scene.emotion` → `EMOTION_TO_VISUAL` маппинг | `warm torchlight, ceremonial glow, amber tones, ritual atmosphere` |
| `{char_id}. {age}. {build}. {hair}. {eyes}. wearing {clothing}. with {accessories}. {palette}. {style}` | `character_visuals[char_id]` | `Велик. 30-35. атлетичное. короткие русые. зелёные. wearing кожаный доспех...` |
| `{location_type_visual}, {architecture}, {atmosphere}, {lighting}, {palette}` | `location_visuals[location_id]` | `ancient stone temple, weathered pillars, каменные круги с бронзовыми символами...` |
| `symbolic themes: {tags}` | `scene.meaning_tags` | `знание, передача, мудрость, предназначение` |
| `{visual_style_hint}` | `scene.visual_style_hint` | `golden hour` |
| `{emotion_suffix}` | `scene.emotion` → `EMOTION_SUFFIX` | `sacred and ritualistic, reverent atmosphere` |
| `cinematic lighting, highly detailed, epic composition...` | Константы `QUALITY_SUFFIXES` | 6 кинематографических тегов |
| Negative prompt | Константа | `blurry, low quality, cartoon, anime...` |

---

## 6. Управление генерацией

### 6.1 Параметры генерации

```python
async def generate(
    self,
    prompt: str | tuple[str, str],  # positive или (positive, negative)
    size: str = "1024x1024"          # "widthxheight"
) -> bytes
```

### 6.2 Seed

Seed вычисляется детерминированно: `hash(промпт) & 0x7FFFFFFF`.  
Одинаковый промпт → одинаковый seed → одинаковое изображение.

Для вариаций нужно менять промпт (добавлять вариативный суффикс в стилевом пресете).

### 6.3 Таймауты

- Обычная генерация: 30-60 секунд (на SDXL)
- Таймаут в провайдере: 180 секунд (3 минуты)
- Poll: каждую секунду проверяется `/history/{prompt_id}`

### 6.4 Если что-то пошло не так

Ошибка → `ImageProviderChain` пробует следующий провайдер в цепочке.  
Если все провайдеры отказали — исключение `RuntimeError("All image providers failed")`.

ComfyUI может вернуть ошибку:
- Нет модели — `CheckpointLoaderSimple` не нашёл файл
- Нет памяти — CUDA Out of Memory
- Неверный воркфлоу — сломанный JSON

Все логируются с префиксом `hermes.visualization.comfyui`.

---

## 7. Смена модели

В дефолтном воркфлоу указана `sd_xl_base_1.0.safetensors`. Чтобы сменить модель:

1. Положи файл `.safetensors` в `models/checkpoints/` ComfyUI
2. Открой `GENOME/workflows/default.json`
3. Найди ноду `CheckpointLoaderSimple`
4. Поменяй `ckpt_name` на имя твоего файла

Или создай отдельный воркфлоу для каждой модели.

---

## 8. Советы по качеству

- **Промпт на русском** — Stable Diffusion понимает русский, но для сложных описаний лучше использовать английские теги: `cinematic lighting, epic composition, highly detailed`
- **Negative prompt** — чем длиннее, тем чище результат. В проекте уже ~20 тегов
- **CFG Scale** — `7.0` хорошо для реализма, `4.0-5.0` для более творческих результатов
- **Steps** — `30` для SDXL, `20` для SD 1.5
- **Размер** — `1024x1024` для SDXL, `512x512` или `512x768` для SD 1.5
- **Несколько генераций** — варьируй promt, добавляя случайный суффикс из `style_presets`

---

## 9. Проверка работы

```bash
# 1. Проверить, что ComfyUI запущен
curl http://127.0.0.1:8188/system_stats

# 2. Проверить, что наш сервер видит ComfyUI
curl http://127.0.0.1:8642/health

# 3. Запустить генерацию тестовой сцены
python scripts/visualize_scene.py --chapter 1 --scene scene_001 --output output/test.png
```

Если ComfyUI не запущен — `visualize_scene.py` вернёт SVG-заглушку вместо ошибки.

---

## 10. Запуск на Google Colab (бесплатный GPU)

### 10.1 Зачем

ComfyUI требует GPU для генерации изображений. На бесплатном Colab доступен T4 GPU (16GB VRAM) — достаточно для SDXL и SVD-XT.

### 10.2 Запуск

1. Откройте 
otebooks/comfyui_colab.ipynb в Google Colab
2. Выберите Runtime > Change runtime type > **T4 GPU**
3. Запускайте ячейки последовательно

### 10.3 Модели

| Модель | Источник | Назначение |
|--------|----------|-----------|
| SDXL base 1.0 | CivitAI (автозагрузка) | Изображения из текста |
| svd_xt | Google Drive | Видео из изображений |

**Google Drive**: модель svd_xt должна лежать в G:\Мой диск\comfyui\models\checkpoint\svd_xt.safetensors

### 10.4 Cloudflare Tunnel

Colab notebook автоматически запускает cloudflared tunnel для проброски порта 8188 наружу.

**Quick Tunnel** (без аккаунта):
- URL меняется при перезапуске tunnel
- Скопируйте URL в .env бэкенда

**Cloudflare Account Tunnel** (стабильный URL):
1. Зарегистрируйтесь на cloudflare.com (бесплатно)
2. cloudflared tunnel login
3. cloudflared tunnel create arkaim-comfyui
4. URL не меняется при перезапуске

### 10.5 Подключение к бэкенду

`ash
# 1. Запустите Colab notebook
# 2. Скопируйте URL туннеля
# 3. Добавьте в runtime/.env:
COMFYUI_URL=https://xxx.trycloudflare.com

# 4. Перезапустите бэкенд
cd runtime && python -m uvicorn core.main:app --port 8642

# 5. Проверьте:
curl http://localhost:8642/book/comfyui/status
`

### 10.6 Ограничения

- Colab free: T4 GPU, ~12ч/день, автоотключение через 90мин бездействия
- Google Drive: нужна авторизация при каждом запуске
- SDXL генерация: ~15-30 секунд
- SVD-XT видео: ~60-120 секунд

---

## 11. Устранение неполадок

| Проблема | Решение |
|----------|---------|
| ComfyUI не запускается | Проверьте GPU: Runtime > Change runtime type > T4 |
| Tunnel не даёт URL | Подождите 30 сек, перезапустите ячейку |
| Бэкенд не видит ComfyUI | Проверьте COMFYUI_URL в .env |
| Ошибка CUDA OOM | Уменьшите размер изображения или используйте SD 1.5 |
| ComfyUI недоступен | Проверьте tunnel / запущен ли ComfyUI |
