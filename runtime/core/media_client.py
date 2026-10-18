"""MediaClient — мост Arkaim → Media Project (MD-4 M4.3; TEMPORARY MIGRATION BRIDGE).

Контракт: arkaim-media/docs/MEDIA_CONTRACT.md v1.0 (POST /v1/generate).
DI-подмена: adc_deps._factory_image_provider/_factory_video_provider заменяют
локальную цепь на MediaClient ТОЛЬКО при env MEDIA_BACKEND_URL (единая точка
подмены по MD4_PRE §11 Вариант A; откат = снять env, один коммит).

R2-обязательства моста (M4.2.1 PROVIDER_INVENTORY; роуты НЕ трогаем):
  - выставляет _base_url (URL Media-сервиса — то, что раньше был URL ComfyUI):
    роут /comfyui/status читает providers[0]._base_url;
  - поддерживает health() (GET /health Media-сервиса): роут /providers/status;
  - стоит ПЕРВЫМ в цепи: провайдер providers[0] (роут /comfyui/status);
  - отвечает на _provider_name-механику цепи: name="mediabackend" → kind="real"
    (в chain._provider_kind нет "mediabackend" → не mock/svg/template → real).

Интерфейс тот же, что у локальных провайдеров (MD4_PRE §11: «MediaClient
(тот же интерфейс) generate(prompt,size)/(prompt,duration,size,fps) → bytes»):

  ImageProvider-совместимость:
    generate(prompt, size, preferred_backend=...) -> bytes
      POST /v1/generate {plan: <минимальный MediaPlan из prompt>,
                         execution: {media_kind: image, size, preferred_backend}}
      preferred_backend — kwargs моста (по умолчанию "auto"); "agnes" выбирает
      Agnes-бэкенд arkaim-media (OWNER-GO 2026-10-14), контракт v1 не менялся
      (execution.preferred_backend — свободное слово по схеме M4.1).
      (конверт ExecutionDispatch-семантики → MediaPlan v0.1.0 MinimalMediaPlan:
       prompt/size — единственные живые входы локального интерфейса; план
       строится ТОЛЬКО из них — никаких данных снаружи не протаскивается)
  VideoProvider-совместимость:
    generate(prompt, duration, size, fps) -> bytes  (dispatch.video_kwargs())
  health() -> bool

MediaPlan-минимум: MediaPlan v0.1.0 (SCHEMAS/MEDIA_PLAN.schema.json,
required: 22 поля; pydantic extra=forbid на стороне Arkaim MD-3). Клиент
строит минимально-валидный план (типа MinimalMediaPlanBuilder) — БЕЗ
SceneContext/positive/negative (эти данные живут в реальном плане MediaPlanBuilder;
MediaClient их не знает и не выдумывает — R3-дисциплина: не протаскивать
домен через мост).

Замечание о preferred_provider (ImageProviderChain.generate_with_metadata):
  локальный интерфейс chain.generate(prompt, size) вызывает
  generate_with_metadata(prompt, size) БЕЗ preferred_provider → "auto".
  MediaClient.generate — терминальный вызов (мост сам не цепь);
  preferred_provider к мосту не доходит (семантика "auto" по умолчанию).

Errors: MediaClient пробрасывает наружу исключения — цепь Аркаима
(включая mock-fallback) продолжает работать (M4.3-инвариант: падение
Media не должно ронять маршруты — mock в цепи ниже ловит).

MD-5: мост умирает вместе с ExecutionDispatch (контракт §0: REMOVE IN MD-5).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from typing import NamedTuple, Optional

import httpx

log = logging.getLogger("core.media_client")

DEFAULT_MEDIA_BACKEND_URL = "http://127.0.0.1:8200"

# MediaPlan v0.1.0 — обязательные поля схемы (SCHEMAS/MEDIA_PLAN.schema.json).
# Значения-минимумы: единственный живой вход — prompt (structured_prompt).
# negative_constraints пуст (negative — смысловое поле плана, не моста).
# plan_id: шаблон — валидный hex-placeholder; НА ВЫЗОВ генерируется уникальный
# (схема требует ^plan_[a-f0-9]+$; 'plan_bridge' из M4.3 её нарушал —
# фикс OWNER-GO 2026-10-14, план одноразовый: md5 от промпта+нанотайм).
_PLAN_REQUIRED_TEMPLATE = {
    "plan_id": "plan_0",  # перезаписывается в _minimal_plan (уникальный id)
    "plan_version": "0.1.0",
    "media_kind": "image",  # перезаписывается по вызову
    "intent": "key_frame",
    "structured_prompt": "",  # = prompt
    "prompt": "",
    "negative_constraints": [],
    "characters": [],
    "location": {
        "location_id": "",
        "name": "",
        "type": "",
        "architecture_style": "",
        "landscape_terrain": "",
    },
    "visual_style": "cinematic_fantasy",
    "atmosphere": "neutral",
    "camera": {"shot_type": "wide", "angle": "eye_level", "movement": "static", "composition": ""},
    "constraints": [],
    "source_refs": {
        "scene_id": "",
        "chapter": 0,
        "character_ids": [],
        "location_id": "",
        "entity_refs": [],
        "rag_fallback": False,
    },
    "temporal_context": {
        "epoch_id": "",
        "name_ru": "",
        "confidence": 0.0,
        "bounds_start": "",
        "bounds_end": "",
        "bounds_uncertainty": "",
        "provenance": [],
        "event_count": 0,
        "character_count": 0,
        "technology_count": 0,
    },
    "provenance": [],
    "lineage": {"parent_plan_id": None, "derivation": "initial", "created_from": "bridge"},
}

# Локальный словарь preferred_provider → контрактный preferred_backend.
# ImageProviderChain._normalize_preferred_provider живёт в Arkaim-цепи и
# к мосту не применяется (мост — терминальный провайдер, не цепь).
# Словарь нужен для будущих вызовов (роуты не передают его мосту сегодня).
# Agnes (OWNER-GO 2026-10-14): preferred_backend="agnes" → бэкенд agnes
# в arkaim-media (шаблон workflows/agnes_image.json, AgnesImage → SaveImage).
_PROVIDER_TO_BACKEND = {
    "auto": "auto",
    "comfyui": "comfyui",
    "comfy": "comfyui",
    "mock": "mock",
    "fallback": "mock",
    "agnes": "agnes",
}


class MediaClientError(RuntimeError):
    """Ошибка HTTP-вызова /v1/generate (пробрасывается в цепь → mock-fallback)."""


class MediaResult(NamedTuple):
    """Ответ /v1/generate целиком: байты + provenance media-сервера.

    Раньше мост выбрасывал media_id/backend/workflow_used (возвращал только
    bytes) — производственный контур (Этап 2) сохраняет их в AssetStorage.
    """

    data: bytes
    media_id: str = ""
    backend: str = ""
    workflow_used: str | None = None


class MediaClient:
    """Мост к Media Project (POST /v1/generate, Media Contract v1.0).

    Тот же интерфейс, что локальные провайдеры Аркаима (image/video).
    `_base_url` — URL Media-сервиса (не ComfyUI!): роуты /comfyui/* читают
    его как «текущий backend URL» — после подмены это URL Media-бэкенда.
    """

    name = "mediabackend"  # chain._provider_name: name-атрибут → "mediabackend"

    def __init__(self, base_url: Optional[str] = None, timeout: float = 620.0):
        # URL читается лениво (env MEDIA_BACKEND_URL), дефолт — localhost:8200.
        # Пере-чтение при каждом вызове — как COMFYUI_URL-механика провайдера
        # (Colab-туннель может смениться; поведение наследовано сознательно).
        self._base_url = (base_url or os.getenv("MEDIA_BACKEND_URL", DEFAULT_MEDIA_BACKEND_URL)).rstrip("/")
        self._timeout = timeout  # video ≤ 600с по контракту §4 + 20с запас

    # ── R2: интерфейс локального провайдера ─────────────────────────────

    async def generate(self, prompt: str, size: str = "1024x1024", **kwargs) -> bytes:
        """Универсальный вход цепей (duck-typing мост, R2).

        ImageProviderChain вызывает generate(prompt, size) — без video-kwargs.
        VideoProviderChain вызывает generate(prompt, duration=…, size=…, fps=…)
        — kwargs ловят video-семантику (dispatch.video_kwargs() MD-3).
        Наличие duration/fps в kwargs = video-вызов.
        """
        if "duration" in kwargs or "fps" in kwargs:
            duration = kwargs.get("duration", 8.0)
            fps = kwargs.get("fps", 24)
            return await self._generate_video(
                prompt,
                duration,
                size,
                fps,
                preferred_backend=kwargs.get("preferred_backend", "auto"),
            )
        # Agnes (OWNER-GO): явный выбор бэкенда не меняет контракт —
        # preferred_backend и так часть execution-конверта v1 (свободное слово).
        return await self._generate_image(prompt, size, preferred_backend=kwargs.get("preferred_backend", "auto"))

    async def generate_video(
        self,
        prompt: str,
        duration: float = 8.0,
        size: str = "1024x576",
        fps: int = 24,
        preferred_backend: str = "auto",
    ) -> bytes:
        """VideoProvider-интерфейс (совместимость с VideoProviderChain/pipeline).

        preferred_backend="comfyicu" (OWNER-GO 2026-10-14) — явный выбор
        облачного LTX 2.5 I2V; авто-путь (auto) через цепь НЕ меняется.
        """
        return await self._generate_video(prompt, duration, size, fps, preferred_backend=preferred_backend)

    async def generate_video_with_meta(
        self,
        prompt: str,
        duration: float = 8.0,
        size: str = "1024x576",
        fps: int = 24,
        preferred_backend: str = "auto",
        input_image: bytes | None = None,
        input_image_filename: str = "arkaim_input.png",
    ) -> MediaResult:
        """Видео-запрос с provenance (Этап 2: производственный контур Studio).

        Возвращает байты + media_id/backend/workflow_used из ответа
        /v1/generate — то, что раньше мост выбрасывал.

        input_image (i2v, OWNER-GO): ПОЛНЫЕ байты утверждённого кадра →
        execution.input_image контракта (base64). Локальный путь НЕ передаётся:
        файл живёт в AssetStorage Arkaim, а исполнитель — внешний. None = t2v
        (прежнее тело запроса без изменений).
        """
        return await self._post_generate_with_meta(
            self._video_body(
                prompt,
                duration,
                size,
                fps,
                preferred_backend,
                input_image=input_image,
                input_image_filename=input_image_filename,
            )
        )

    async def generate_image_with_meta(
        self,
        prompt: str,
        size: str = "1024x1024",
        preferred_backend: str = "auto",
    ) -> MediaResult:
        """Изображение-запрос с provenance (Studio: шаг «создать изображение»).

        preferred_backend="agnes" — реальная интеграция ComfyUI-Agnes через
        arkaim-media (бесплатная, отрицательные промпты на стороне Agnes
        не поддерживаются — предупреждение логирует media-сервер).
        """
        return await self._post_generate_with_meta(self._image_body(prompt, size, preferred_backend))

    async def health(self) -> bool:
        """R2: живость для роутов /providers/status и /comfyui/status."""
        try:
            url = self._current_url()
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{url}/health")
                return r.status_code == 200
        except Exception:
            return False

    # ── Внутренняя механика ─────────────────────────────────────────────

    def _current_url(self) -> str:
        """Ленивое пере-чтение env (как COMFYUI_URL-механика; см. класс-docstring)."""
        new_url = os.getenv("MEDIA_BACKEND_URL", self._base_url).rstrip("/")
        if new_url != self._base_url:
            self._base_url = new_url
        return self._base_url

    @staticmethod
    def _minimal_plan(prompt: str, media_kind: str) -> dict:
        """Минимальный валидный MediaPlan v0.1.0 из prompt.

        Только живые входы моста: prompt (+structured_prompt=prompt).
        Никаких доменных данных не протаскивается (R3-дисциплина).
        """
        plan = dict(_PLAN_REQUIRED_TEMPLATE)
        # Схема-паттерн ^plan_[a-f0-9]+$ + «план одноразовый» (MD-3):
        # hex-id на каждый вызов, без доменных данных.
        plan["plan_id"] = "plan_" + hashlib.sha256(f"{prompt}:{time.time_ns()}".encode()).hexdigest()[:16]
        plan["media_kind"] = media_kind
        plan["prompt"] = prompt
        plan["structured_prompt"] = prompt
        return plan

    async def _post_generate(self, body: dict) -> bytes:
        """POST /v1/generate → bytes (MediaResult.bytes_b64)."""
        return (await self._post_generate_with_meta(body)).data

    async def _post_generate_with_meta(self, body: dict) -> MediaResult:
        """POST /v1/generate → MediaResult (bytes + provenance media-сервера)."""
        url = self._current_url()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as c:
                r = await c.post(f"{url}/v1/generate", json=body)
        except httpx.HTTPError as exc:
            raise MediaClientError(f"media_backend_unreachable: {exc.__class__.__name__}") from exc

        if r.status_code != 200:
            # Контракт §5: сообщение без внутренних деталей; наружу — только класс.
            try:
                err = r.json().get("error", {})
                code = err.get("code", "UNKNOWN")
            except Exception:
                code = f"HTTP_{r.status_code}"
            raise MediaClientError(f"media_backend_error: {code}")

        result = r.json()
        return MediaResult(
            data=base64.b64decode(result["bytes_b64"]),
            media_id=str(result.get("media_id", "") or ""),
            backend=str(result.get("backend", "") or ""),
            workflow_used=result.get("workflow_used"),
        )

    @staticmethod
    def _image_body(prompt: str, size: str, preferred_backend: str = "auto") -> dict:
        """Тело POST /v1/generate для изображения (общее для bytes/meta-входов)."""
        return {
            "plan": MediaClient._minimal_plan(prompt, "image"),
            "execution": {
                "media_kind": "image",
                "size": size,
                "preferred_backend": preferred_backend,
            },
        }

    async def _generate_image(self, prompt: str, size: str, preferred_backend: str = "auto") -> bytes:
        return await self._post_generate(self._image_body(prompt, size, preferred_backend))

    @staticmethod
    def _video_body(
        prompt: str,
        duration: float,
        size: str,
        fps: int,
        preferred_backend: str,
        input_image: bytes | None = None,
        input_image_filename: str = "arkaim_input.png",
    ) -> dict:
        """Тело POST /v1/generate для видео (общее для bytes/meta-входов).

        input_image — байты кадра i2v: уходят в execution.input_image
        (base64, filename); при None тело в точности прежнее (t2v).
        """
        plan = MediaClient._minimal_plan(prompt, "video")
        plan["duration_sec"] = duration
        plan["fps"] = fps
        execution: dict = {
            "media_kind": "video",
            "size": size,
            # auto — прежнее поведение (mock в цепи не меняется);
            # явный "comfyicu" — без молчаливого фолбэка (как agnes).
            "preferred_backend": preferred_backend,
            "duration_sec": duration,
            "fps": fps,
        }
        if input_image is not None:
            execution["input_image"] = {
                "bytes_b64": base64.b64encode(input_image).decode("ascii"),
                "filename": input_image_filename,
            }
        return {"plan": plan, "execution": execution}

    async def _generate_video(
        self,
        prompt: str,
        duration: float,
        size: str,
        fps: int,
        preferred_backend: str = "auto",
    ) -> bytes:
        return await self._post_generate(self._video_body(prompt, duration, size, fps, preferred_backend))
