"""Film Sequence (Фаза 4): план сборки последовательности фильма.

Read-only проекция **уже существующей** ленты (``studio.reel`` / ``GET /studio/reel``)
в **режиссёрский план сборки**: непрерывный тайминг отрезков, разрывы (где нет
готового клипа), переходы на стыках, сводка по исполнителям (в т.ч. флаг
«смешанные исполнители») и текстовый план для последующего монтажа.

Это НЕ монтаж и НЕ финальный cut. Модуль ничего не создаёт, не генерирует и не
удаляет: он только упорядочивает и считает. Финальный монтаж выполняется вне
системы (например, в DaVinci Resolve) — плану отдаётся текстовая «раскадровка».

Порядок отрезков берётся ТОЛЬКО из канонических данных (геном → сцены,
сценарий → планы), уже собранных в ленте; модуль не переупорядочивает сцены и
планы. Клип «готов» к сборке, если его статус — реальный клип (``ready``);
кадр, placeholder, mock и устаревший клип считаются разрывом (нет готового
видеофайла).

Модуль чистый (без I/O) — покрыт unit-тестами; данные готовит роут
``GET /studio/sequence`` из ``runtime/core/routes/studio.py``.
"""

from __future__ import annotations

from typing import Any

# ── Типы отрезка последовательности ──────────────────────────────────────
SEG_KIND_CLIP = "clip"  # есть клип (реальный/mock/устаревший)
SEG_KIND_FRAME = "frame"  # есть только утверждённый кадр
SEG_KIND_PLACEHOLDER = "placeholder"  # нет материала

# Статусы клипа, при которых отрезок собран (реальное видео). mock и stale —
# НЕ готовое видео: mock — заглушка, stale — устарел (нужно переснять).
CLIP_STATUSES = ("ready", "mock", "stale")
READY_STATUSES = ("ready",)
FRAME_READY_STATUSES = ("approved", "needs_update")


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _round(value: float) -> float:
    return round(value, 2)


def segment_kind(
    clip_status: str, frame_status: str, frame_asset_id: str | None
) -> str:
    """Тип отрезка по статусу клипа и кадра (как в ленте film/story reel)."""
    if clip_status in CLIP_STATUSES:
        return SEG_KIND_CLIP
    if frame_status in FRAME_READY_STATUSES or frame_asset_id:
        return SEG_KIND_FRAME
    return SEG_KIND_PLACEHOLDER


def executor_label(executor: dict | None) -> str | None:
    """Человекочитаемая метка исполнителя: провайдер/бэкенд (+ модель)."""
    if not executor:
        return None
    base = executor.get("provider") or executor.get("backend")
    model = executor.get("model")
    if not base and not model:
        return None
    label = str(base) if base else ""
    if model:
        label = f"{label} · {model}" if label else str(model)
    return label


def executor_key(executor: dict | None) -> str | None:
    """Стабильный ключ группировки исполнителей (для сводки)."""
    if not executor:
        return None
    parts = [
        executor.get("provider"),
        executor.get("backend"),
        executor.get("model"),
        executor.get("workflow_used"),
    ]
    joined = " / ".join(str(p) for p in parts if p)
    return joined or None


def build_plan(scenes: list[dict], *, limitations: list[str] | None = None) -> dict:
    """Построить план сборки из карточек сцен ленты (``data["scenes"]``).

    Каждая карточка сцены: ``scene_id, chapter, index_in_episode, shots[]``.
    Каждый шот: ``shot_id, order, index, duration_sec, transition_to_next,
    frame{status,asset_id}, video{status,asset_id,mock,executor}, description``.

    Возвращает план с накопительным таймингом (``start_sec``/``end_sec``),
    разрывами, переходами, сводкой исполнителей и общей сводкой.
    """
    segments: list[dict] = []
    scene_ids_seen: list[str] = []
    chapters_seen: set[int] = set()
    start = 0.0
    index = 0

    # Плоский проход в каноническом порядке: сцены → их планы по порядку.
    for scene in scenes:
        sid = scene.get("scene_id", "")
        chapter = scene.get("chapter")
        if sid and sid not in scene_ids_seen:
            scene_ids_seen.append(sid)
        if chapter is not None:
            chapters_seen.add(chapter)
        shots = scene.get("shots") or []
        for shot_idx, shot in enumerate(shots):
            frame = shot.get("frame") or {}
            video = shot.get("video") or {}
            clip_status = video.get("status") or "none"
            frame_status = frame.get("status") or "none"
            frame_asset_id = frame.get("asset_id")
            kind = segment_kind(clip_status, frame_status, frame_asset_id)
            ready = clip_status in READY_STATUSES
            executor = video.get("executor") if kind == SEG_KIND_CLIP else None
            duration = _as_float(shot.get("duration_sec"))
            is_last_in_scene = shot_idx == len(shots) - 1
            segment = {
                "index": index,
                "scene_id": sid,
                "chapter": chapter if chapter is not None else 0,
                "index_in_episode": scene.get("index_in_episode", -1),
                "shot_id": shot.get("shot_id", ""),
                "shot_order": shot.get("order", 0),
                "shot_index": shot.get("index", shot_idx),
                "kind": kind,
                "clip_status": clip_status,
                "frame_status": frame_status,
                "mock": bool(video.get("mock")),
                "ready": ready,
                "duration_sec": _round(duration),
                "start_sec": _round(start),
                "end_sec": _round(start + duration),
                "transition_to_next": shot.get("transition_to_next") or "",
                "scene_boundary_after": is_last_in_scene,
                "clip_asset_id": video.get("asset_id")
                if kind == SEG_KIND_CLIP
                else None,
                "frame_asset_id": frame_asset_id,
                "executor": executor,
                "executor_key": executor_key(executor),
                "executor_label": executor_label(executor),
                "description": shot.get("description", ""),
            }
            segments.append(segment)
            start += duration
            index += 1

    # Последний отрезок фильма не имеет границы — сбрасываем флаг.
    if segments:
        segments[-1]["scene_boundary_after"] = False

    # Разрывы: максимальные группы подряд идущих не-готовых отрезков.
    gaps: list[dict] = []
    current: list[dict] = []
    for seg in segments:
        if seg["ready"]:
            if current:
                gaps.append(_make_gap(current))
                current = []
        else:
            current.append(seg)
    if current:
        gaps.append(_make_gap(current))

    # Готовые отрезки (для сборки), сводка исполнителей.
    assembled = [seg for seg in segments if seg["ready"]]
    executors = _rollup_executors(assembled)

    # Переходы: между всеми соседними отрезками (включая разрыв материала).
    transitions: list[dict] = []
    for i in range(len(segments) - 1):
        a, b = segments[i], segments[i + 1]
        transitions.append(
            {
                "index": i,
                "from_shot_id": a["shot_id"],
                "to_shot_id": b["shot_id"],
                "transition": a["transition_to_next"],
                "scene_boundary": a["scene_id"] != b["scene_id"],
                "from_ready": a["ready"],
                "to_ready": b["ready"],
            }
        )

    total_duration = _round(sum(s["duration_sec"] for s in segments))
    assembled_duration = _round(sum(s["duration_sec"] for s in assembled))
    gap_duration = _round(sum(g["duration_sec"] for g in gaps))
    kind_counts = {
        SEG_KIND_CLIP: 0,
        SEG_KIND_FRAME: 0,
        SEG_KIND_PLACEHOLDER: 0,
    }
    for seg in segments:
        kind_counts[seg["kind"]] = kind_counts.get(seg["kind"], 0) + 1

    plan = {
        "segments": segments,
        "assembled": [
            {
                "index": s["index"],
                "scene_id": s["scene_id"],
                "chapter": s["chapter"],
                "shot_id": s["shot_id"],
                "start_sec": s["start_sec"],
                "end_sec": s["end_sec"],
                "duration_sec": s["duration_sec"],
                "clip_asset_id": s["clip_asset_id"],
                "executor_label": s["executor_label"],
                "transition_to_next": s["transition_to_next"],
            }
            for s in assembled
        ],
        "gaps": gaps,
        "transitions": transitions,
        "executors": executors,
        "executor_mixed": len(executors) > 1,
        "summary": {
            "segment_count": len(segments),
            "scene_count": len(scene_ids_seen),
            "episode_count": len(chapters_seen),
            "clip_count": kind_counts.get(SEG_KIND_CLIP, 0),
            "ready_count": len(assembled),
            "frame_count": kind_counts.get(SEG_KIND_FRAME, 0),
            "placeholder_count": kind_counts.get(SEG_KIND_PLACEHOLDER, 0),
            "mock_count": sum(1 for s in segments if s["mock"]),
            "stale_count": sum(1 for s in segments if s["clip_status"] == "stale"),
            "assembled_count": len(assembled),
            "gap_count": len(gaps),
            "executor_count": len(executors),
            "total_duration_sec": total_duration,
            "assembled_duration_sec": assembled_duration,
            "gap_duration_sec": gap_duration,
        },
        "limitations": list(limitations or []),
    }
    return plan


def _make_gap(segments: list[dict]) -> dict:
    """Один разрыв: непрерывная группа не-готовых отрезков."""
    kinds: list[str] = []
    for seg in segments:
        if seg["kind"] not in kinds:
            kinds.append(seg["kind"])
    scene_ids: list[str] = []
    for seg in segments:
        if seg["scene_id"] not in scene_ids:
            scene_ids.append(seg["scene_id"])
    return {
        "start_index": segments[0]["index"],
        "end_index": segments[-1]["index"],
        "segment_count": len(segments),
        "start_sec": segments[0]["start_sec"],
        "end_sec": segments[-1]["end_sec"],
        "duration_sec": _round(sum(s["duration_sec"] for s in segments)),
        "kinds": kinds,
        "scene_ids": scene_ids,
        "shot_ids": [s["shot_id"] for s in segments],
    }


def _rollup_executors(assembled: list[dict]) -> list[dict]:
    """Сводка исполнителей по готовым отрезкам (кто что снял и сколько)."""
    order: list[str] = []
    by_key: dict[str, dict] = {}
    for seg in assembled:
        key = seg["executor_key"] or "неизвестный исполнитель"
        entry = by_key.get(key)
        if entry is None:
            entry = {
                "key": key,
                "label": seg["executor_label"] or key,
                "count": 0,
                "duration_sec": 0.0,
                "shot_ids": [],
            }
            by_key[key] = entry
            order.append(key)
        entry["count"] += 1
        entry["duration_sec"] += seg["duration_sec"]
        entry["shot_ids"].append(seg["shot_id"])
    result = []
    for key in order:
        entry = by_key[key]
        entry["duration_sec"] = _round(entry["duration_sec"])
        result.append(entry)
    return result


def fmt_timecode(sec: float) -> str:
    """Таймкод ``ЧЧ:ММ:СС`` (для текстового плана)."""
    total = max(0, int(round(_as_float(sec))))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def render_plan_text(plan: dict) -> str:
    """Текстовый план сборки (раскадровка) для внешнего монтажа.

    Формат построчный: таймкод начала/конца, тип, сцена → план, исполнитель,
    переход. Разрывы вынесены отдельным блоком. Это НЕ EDL и НЕ XML: текст
    человекочитаемый, для ручного переноса в монтажную программу.
    """
    lines: list[str] = ["План сборки последовательности фильма", ""]
    summary = plan.get("summary", {})
    lines.append(
        f"Отрезков: {summary.get('segment_count', 0)} · "
        f"готовых клипов: {summary.get('ready_count', 0)} · "
        f"разрывов: {summary.get('gap_count', 0)}"
    )
    lines.append(
        f"Длительность: всего {fmt_timecode(summary.get('total_duration_sec', 0))} · "
        f"собрано {fmt_timecode(summary.get('assembled_duration_sec', 0))} · "
        f"разрывы {fmt_timecode(summary.get('gap_duration_sec', 0))}"
    )
    if plan.get("executor_mixed"):
        execs = ", ".join(e["label"] for e in plan.get("executors", []))
        lines.append(
            f"Смешанные исполнители ({summary.get('executor_count', 0)}): {execs}"
        )
    lines.append("")

    lines.append("Последовательность:")
    for seg in plan.get("segments", []):
        ready = "готово" if seg["ready"] else "—"
        executor = seg.get("executor_label") or ""
        transition = seg.get("transition_to_next") or "-"
        lines.append(
            f"{seg['index'] + 1:03d}  "
            f"{fmt_timecode(seg['start_sec'])} → {fmt_timecode(seg['end_sec'])}  "
            f"{seg['kind']:<11}  "
            f"эп.{seg['chapter']} сцена {seg['scene_id']} → план {seg['shot_id']}  "
            f"[{ready}]{(' ' + executor) if executor else ''}  "
            f"переход: {transition}"
        )

    gaps = plan.get("gaps", [])
    if gaps:
        lines.append("")
        lines.append("Разрывы (нет готового клипа):")
        for gap in gaps:
            lines.append(
                f"  отрезки {gap['start_index'] + 1}–{gap['end_index'] + 1} "
                f"({fmt_timecode(gap['start_sec'])} → {fmt_timecode(gap['end_sec'])}, "
                f"{fmt_timecode(gap['duration_sec'])}): "
                f"{', '.join(gap['shot_ids'])}"
            )

    limitations = plan.get("limitations") or []
    if limitations:
        lines.append("")
        lines.append("Ограничения:")
        for lim in limitations:
            lines.append(f"  - {lim}")

    return "\n".join(lines)


def render_edl(
    plan: dict, *, fps: int = 25, book_title: str = "Наследие Аркаима"
) -> str:
    """Экспорт плана сборки в упрощённый EDL-формат для DaVinci Resolve.

    Формат — XML с таймингами готовых отрезков (assembled). Каждый отрезок —
    запись ``<cut>`` с исходным таймкодом (в секундах), длительностью,
    ссылкой на ассет клипа и переходом. Разрывы и не-готовые отрезки не
    попадают в EDL. Это НЕ финальный монтаж: файл только описывает, какие
    клипы и в каком порядке нужно перенести в DaVinci Resolve вручную.
    """
    from datetime import datetime, timezone

    assembled = plan.get("assembled") or []
    summary = plan.get("summary", {})
    film = plan.get("film") or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fps_str = str(fps)

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<edit_decision_list>",
        f"  <title>{book_title}</title>",
        f"  <generated_at>{now}</generated_at>",
        f"  <fps>{fps_str}</fps>",
        f"  <total_segments>{summary.get('segment_count', 0)}</total_segments>",
        f"  <ready_clips>{summary.get('ready_count', 0)}</ready_clips>",
        f"  <total_duration_sec>{summary.get('total_duration_sec', 0)}</total_duration_sec>",
        f"  <assembled_duration_sec>{summary.get('assembled_duration_sec', 0)}</assembled_duration_sec>",
        "",
        "  <clips>",
    ]

    for seg in assembled:
        asset_id = seg.get("clip_asset_id") or ""
        source_name = f"clip_{asset_id}" if asset_id else "no_asset"
        start_sec = seg.get("start_sec", 0)
        end_sec = seg.get("end_sec", 0)
        duration_sec = seg.get("duration_sec", 0)
        shot_id = seg.get("shot_id", "")
        scene_id = seg.get("scene_id", "")
        executor = seg.get("executor_label") or ""
        transition = seg.get("transition_to_next", "")

        lines.append("    <clip>")
        lines.append(f"      <index>{seg.get('index', 0) + 1}</index>")
        lines.append(f"      <shot_id>{shot_id}</shot_id>")
        lines.append(f"      <scene_id>{scene_id}</scene_id>")
        lines.append(f"      <source>{source_name}</source>")
        lines.append(f"      <start_sec>{start_sec}</start_sec>")
        lines.append(f"      <end_sec>{end_sec}</end_sec>")
        lines.append(f"      <duration_sec>{duration_sec}</duration_sec>")
        if executor:
            lines.append(f"      <executor>{executor}</executor>")
        if transition:
            lines.append(f"      <transition>{transition}</transition>")
        lines.append("    </clip>")

    lines.extend(["", "  </clips>", "</edit_decision_list>"])
    return "\n".join(lines)
