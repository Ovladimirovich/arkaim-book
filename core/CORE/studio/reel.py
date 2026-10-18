"""Story Reel (Фаза 3): режиссёрская лента фильма.

Проекция существующих канонических данных (геном + активный сценарий Studio)
и уже созданных артефактов (кадры, видеоклипы) в последовательность
**Эпизод → Сцена → План → Кадр → Клип**. Ничего не создаёт, не удаляет и не
меняет: только сопоставляет и вычисляет статусы.

Ключевые правила (OWNER-GO):
  - порядок берётся ТОЛЬКО из канонических данных (эпизод → сцена → порядок
    планов сценария); ассеты лишь привязываются к планам, но не задают порядок;
  - статусы устаревания вычисляются сравнением (без хранения), как в
    ``staleness.ts`` фронтенда: кадр «требует обновления», если его prompt_used
    отличается от текущего промпта; клип «устарел», если изменён исходный кадр,
    промпт движения или общие правила фильма (art_direction_revision);
  - mock-клип (provider/backend == 'mock') остаётся клипом, но помечается:
    реального видео нет;
  - привязка клипа к плану: по ``generation.shot_id`` (точно) либо, для старых
    записей, по ``generation.reference_image_id == shot.approved_image_asset_id``.

Модуль чистый (без I/O) — покрыт unit-тестами; сборка ленты выполняется
в роуте ``GET /studio/reel`` из ``runtime/core/routes/studio.py``.
"""

from __future__ import annotations

from typing import Any

# ── Статусы кадра (frame) ────────────────────────────────────────────────
FRAME_APPROVED = "approved"  # утверждён
FRAME_NONE = "none"  # отсутствует
FRAME_NEEDS_UPDATE = "needs_update"  # требует обновления (промпт изменился)

# ── Статусы клипа (clip) ─────────────────────────────────────────────────
CLIP_NONE = "none"  # отсутствует
CLIP_GENERATING = "generating"  # ещё создаётся
CLIP_FAILED = "failed"  # ошибка
CLIP_MOCK = "mock"  # mock-запись (без реального видео)
CLIP_READY = "ready"  # реальный готовый клип
CLIP_STALE = "stale"  # устарел

FRAME_STATUSES = (FRAME_APPROVED, FRAME_NONE, FRAME_NEEDS_UPDATE)
CLIP_STATUSES = (
    CLIP_NONE,
    CLIP_GENERATING,
    CLIP_FAILED,
    CLIP_MOCK,
    CLIP_READY,
    CLIP_STALE,
)


def _norm(value: str | None) -> str:
    """Нормализация текста для сравнения (как norm в staleness.ts)."""
    return " ".join((value or "").split()).strip()


def _enum_value(value: Any) -> str:
    """Значение enum/строки в виде строки (AssetStatus/AssetType и пр.)."""
    return value.value if hasattr(value, "value") else str(value)


def _gen(asset: Any) -> Any:
    return getattr(asset, "generation", None)


def is_mock(asset: Any) -> bool:
    """mock-запись (без реального видео) vs реальный клип."""
    gen = _gen(asset)
    if gen is None:
        return False
    provider = getattr(gen, "provider", None)
    backend = getattr(gen, "backend", None)
    return provider == "mock" or backend == "mock"


def frame_state(shot: Any, image_asset: Any | None, resolved_prompt: str) -> dict:
    """Состояние кадра плана: утверждён / отсутствует / требует обновления.

    ``resolved_prompt`` — текущий собранный промпт кадра (image_description).
    Если промпт неизвестен (пусто) — не объявляем устаревшим (как staleness.ts).
    """
    approved_id = getattr(shot, "approved_image_asset_id", None)
    if not approved_id:
        return {"status": FRAME_NONE, "asset_id": None}
    state = {"status": FRAME_APPROVED, "asset_id": approved_id}
    if image_asset is not None:
        status = _enum_value(getattr(image_asset, "status", ""))
        used = _norm(getattr(image_asset, "prompt_used", ""))
        current = _norm(resolved_prompt)
        if status == "completed" and used and current and used != current:
            state["status"] = FRAME_NEEDS_UPDATE
    return state


def video_for_shot(videos: list[Any], shot: Any) -> Any | None:
    """Лучший клип для плана: по shot_id (точно), иначе по утверждённому кадру.

    При нескольких кандидатах предпочитается совпадение по shot_id и более
    свежая запись (created_at лексикографически).
    """
    shot_id = getattr(shot, "shot_id", "") or ""
    frame_id = getattr(shot, "approved_image_asset_id", None)
    best: tuple[int, str, Any] | None = None
    for asset in videos:
        gen = _gen(asset)
        if gen is None:
            continue
        priority = 0
        gen_shot = getattr(gen, "shot_id", None)
        if shot_id and gen_shot and gen_shot == shot_id:
            priority = 2
        elif frame_id and getattr(gen, "reference_image_id", None) == frame_id:
            priority = 1
        if priority == 0:
            continue
        created = str(getattr(asset, "created_at", "") or "")
        candidate = (priority, created, asset)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else None


def clip_state(
    asset: Any | None,
    *,
    shot_frame_id: str | None,
    resolved_prompt: str,
    art_direction_revision: int | None,
) -> dict:
    """Состояние клипа плана: none / generating / failed / mock / ready / stale.

    Причины устаревания (если клип готов):
      - исходный кадр не совпадает с утверждённым;
      - промпт движения изменился после генерации;
      - общие правила фильма (art_direction_revision) изменились после генерации.
    """
    if asset is None:
        return {
            "status": CLIP_NONE,
            "asset_id": None,
            "mock": False,
            "stale_reasons": [],
        }

    status = _enum_value(getattr(asset, "status", ""))
    base = {
        "asset_id": getattr(asset, "asset_id", None),
        "mock": is_mock(asset),
        "stale_reasons": [],
    }
    if status in ("pending", "generating"):
        return {**base, "status": CLIP_GENERATING}
    if status == "failed":
        return {**base, "status": CLIP_FAILED, "error": getattr(asset, "error", None)}

    # completed — вычисляем устаревание
    reasons: list[str] = []
    gen = _gen(asset)
    ref = getattr(gen, "reference_image_id", None) if gen else None
    if shot_frame_id:
        if ref != shot_frame_id:
            reasons.append(
                f"исходный кадр ({ref}) не совпадает с утверждённым ({shot_frame_id})"
                if ref
                else "создано без утверждённого кадра-основы"
            )
    used = _norm(getattr(asset, "prompt_used", ""))
    current = _norm(resolved_prompt)
    if used and current and used != current:
        reasons.append("промпт движения изменился после генерации")
    gen_rev = getattr(gen, "art_direction_revision", None) if gen else None
    if (
        gen_rev is not None
        and art_direction_revision is not None
        and gen_rev < art_direction_revision
    ):
        reasons.append(
            f"общие правила фильма изменились (ревизия {gen_rev} < {art_direction_revision})"
        )

    if base["mock"]:
        clip_status = CLIP_MOCK
    elif reasons:
        clip_status = CLIP_STALE
    else:
        clip_status = CLIP_READY
    return {**base, "status": clip_status, "stale_reasons": reasons}
