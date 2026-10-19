"""Studio API — endpoints для Studio v2 (Phase 1B).

Эндпоинты Studio: сессии, discussion, версии, reference, финализация, export.

Studio НЕ генерирует описания — получает три результата от Arkaim Description System
(через /visual/studio-describe). Затем позволяет пользователю обсуждать, корректировать,
создавать варианты и финализировать.

RBAC: editor + admin (Studio = инструмент автора).
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from auth.rbac import require_role
from core.dto.requests import ImageJobRequest, VideoJobRequest
from core.dto.responses import SuccessResponse
from core.adc_deps import registry
from studio.session_models import UserModification
from studio.art_direction import FilmArtDirection
from studio.prepared_updates import (
    IMAGE_EXECUTORS,
    PreparedUpdateCreateRequest,
    PreparedUpdatePatchRequest,
)

log = logging.getLogger("hermes.routes.studio")

router = APIRouter(prefix="/studio", tags=["Studio"])


def _get_store():
    from studio.store import StudioStore

    return StudioStore()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _as_int(value) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return 0


# ── 0. Available scenes ─────────────────────────────────────────


@router.get("/scenes", summary="Список доступных сцен для создания Studio-сессии")
async def list_scenes():
    """Возвращает сцены из генома книги, доступные для Studio."""
    from core.routes.book import _get_genome_data

    genome = _get_genome_data()
    if not genome:
        return SuccessResponse(data=[])
    scenes = genome.get("modules", {}).get("scenes", [])
    result = []
    for s in scenes:
        result.append(
            {
                "scene_id": s.get("scene_id", s.get("id", "")),
                "chapter": s.get("chapter", 1),
                "title": s.get("title", ""),
            }
        )
    return SuccessResponse(data=result)


# ── 0.1 Film tree (эпизод → сцена → план) ───────────────────────


@router.get(
    "/film",
    dependencies=[Depends(require_role("reader"))],
    summary="Дерево фильма: эпизоды (главы) → сцены (геном) → планы (шоты)",
)
async def get_film(user: dict = Depends(require_role("reader"))):
    """Read-only проекция фильма для нижнего уровня Studio.

    Канонический список сцен — геном книги (Knowledge Core); Studio
    аннотирует их своим состоянием (сессия, утверждённый кадр, видео).
    Порядок сцен внутри эпизода = порядок массива генома. Эпизод = глава.

    Ничего не создаёт, не генерирует и не удаляет. История экспериментов
    намеренно не загружается (производительность)."""
    from core.routes.book import _get_genome_data
    from visual_assets.schemas import AssetType

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []

    store = _get_store()
    sessions = await store.list_sessions(user_id=user.get("user_id", ""), limit=1000, offset=0)
    sessions_by_scene: dict[str, object] = {}
    for s in sessions:  # список отсортирован по updated_at DESC — берём свежайшую
        if s.scene_id and s.scene_id not in sessions_by_scene:
            sessions_by_scene[s.scene_id] = s

    # Видео-ассеты по (chapter, scene_id) — одним запросом на главу.
    video_by_scene: dict[tuple[int, str], list] = {}
    try:
        asset_store = registry.get("asset_store")
    except Exception as e:  # хранилище не зарегистрировано — дерево всё равно строится
        log.warning("film_asset_store_unavailable: %s", e)
        asset_store = None
    if asset_store is not None:
        for ch in sorted({_as_int(s.get("chapter")) for s in scenes}):
            if not ch:
                continue
            try:
                assets = await asset_store.list_assets(chapter=ch, asset_type=AssetType.VIDEO, limit=500)
            except Exception as e:  # хранилище недоступно — дерево всё равно строится
                log.warning("film_video_assets_failed chapter=%s: %s", ch, e)
                assets = []
            for a in assets:
                video_by_scene.setdefault((a.chapter, a.scene_id), []).append(a)

    episodes_map: dict[int, dict] = {}
    order_global = 0
    for s in scenes:
        chapter = _as_int(s.get("chapter"))
        scene_id = s.get("scene_id", s.get("id", ""))
        session = sessions_by_scene.get(scene_id)
        shots: list[dict] = []
        total_duration = 0.0
        approved_image = None
        session_id = None
        session_status = None
        has_session = session is not None
        if session:
            session_id = session.session_id
            session_status = session.status.value
            approved_image = session.approved_image_asset_id
            version = await store.get_active_version(session.session_id)
            scenario = version.video_scenario if version else None
            if scenario and scenario.shots:
                for idx, sh in enumerate(sorted(scenario.shots, key=lambda x: x.order)):
                    total_duration += float(sh.duration_sec or 0)
                    shots.append(
                        {
                            "shot_id": sh.shot_id,
                            "order": sh.order,
                            "index": idx,
                            "shot_type": sh.shot_type,
                            "duration_sec": sh.duration_sec,
                            "transition_to_next": sh.transition_to_next,
                            "approved_image_asset_id": sh.approved_image_asset_id,
                            "has_video": False,
                            "video_asset_id": None,
                        }
                    )

        videos = video_by_scene.get((chapter, scene_id), [])
        video_count = len(videos)
        if shots:
            by_id = {sh["shot_id"]: sh for sh in shots if sh["shot_id"]}
            for a in videos:
                sid = getattr(a.generation, "shot_id", None)
                if sid and sid in by_id:
                    by_id[sid]["has_video"] = True
                    by_id[sid]["video_asset_id"] = a.asset_id

        if not has_session:
            status = "no_session"
        elif video_count:
            status = "video"
        elif approved_image:
            status = "frame_approved"
        else:
            status = "prompts"

        ep = episodes_map.setdefault(
            chapter,
            {
                "episode_id": f"chapter_{chapter}",
                "chapter": chapter,
                "title": f"Глава {chapter}" if chapter else "Вне эпизода",
                "scene_count": 0,
                "total_duration_sec": 0.0,
                "scenes": [],
            },
        )
        ep["scenes"].append(
            {
                "scene_id": scene_id,
                "chapter": chapter,
                "index_in_episode": len(ep["scenes"]),
                "order_global": order_global,
                "title": s.get("title", ""),
                "location": s.get("location", ""),
                "characters": s.get("characters") or [],
                "emotion": s.get("emotion", ""),
                "visual_style_hint": s.get("visual_style_hint", ""),
                "has_session": has_session,
                "session_id": session_id,
                "session_status": session_status,
                "approved_image_asset_id": approved_image,
                "shot_count": len(shots),
                "total_duration_sec": round(total_duration, 2),
                "video_count": video_count,
                "has_video": video_count > 0,
                "status": status,
                "shots": shots,
            }
        )
        ep["scene_count"] += 1
        ep["total_duration_sec"] = round(ep["total_duration_sec"] + total_duration, 2)
        order_global += 1

    episodes = [episodes_map[ch] for ch in sorted(episodes_map.keys())]
    return SuccessResponse(
        data={
            "film": {
                "book_id": genome.get("book_id", "arkaim"),
                "title": genome.get("title", ""),
                "episode_count": len(episodes),
                "scene_count": len(scenes),
                "total_duration_sec": round(sum(ep["total_duration_sec"] for ep in episodes), 2),
            },
            "episodes": episodes,
        }
    )


# ── 4. Story Reel (Фаза 3: лента «Эпизод → Сцена → План → Кадр → Клип») ──

REEL_SCOPE_SCENE = "scene"  # одна сцена
REEL_SCOPE_SEQUENCE = "sequence"  # последовательность связанных сцен
REEL_SCOPE_EPISODE = "episode"  # весь эпизод (глава)
REEL_SCOPE_FILM = "film"  # весь фильм (все эпизоды, все сцены)


def _reel_link_summary(link) -> dict:
    """Краткая проекция связи continuity для ленты (граница планов/сцен)."""
    return {
        "status": link.status,
        "relation": link.relation,
        "certainty": link.certainty,
        "from_ref": link.from_ref,
        "to_ref": link.to_ref,
        "from_scene_id": link.from_scene_id,
        "to_scene_id": link.to_scene_id,
        "finding_count": len(link.findings),
        "findings": [
            {
                "field": f.field,
                "kind": f.kind,
                "severity": f.severity,
                "message": f.message,
                "subject": f.subject,
                "from_value": f.from_value,
                "to_value": f.to_value,
            }
            for f in link.findings
        ],
        "decision": link.decision.model_dump() if link.decision else None,
        "reason": link.reason,
    }


async def _build_reel_data(
    store,
    scenes,
    scope: str,
    ad,
    sessions_by_scene: dict,
    images_by_scene: dict,
    videos_by_scene: dict,
    ep_index_by_id: dict,
    prev_scene_by_id: dict,
    limitations: list[str],
) -> dict:
    """Собрать ленту: карточки сцен/планов + последовательность + сводка.

    Порядок берётся ТОЛЬКО из канонических данных (геном → порядок сцен,
    сценарий → порядок планов). Ассеты лишь привязываются к планам.
    Ничего не создаёт, не меняет и не удаляет.
    """
    from studio import reel
    from studio.art_direction import resolve_shot
    from studio.continuity import (
        RELATION_ADJACENT,
        RELATION_SCENE_BOUNDARY,
        RELATION_SHOTS,
        apply_decisions,
        build_scene_snapshot,
        compare_scenes,
        compare_shots,
        find_applied_decision,
        make_apply_basis,
        make_basis,
    )
    from visual.VISUAL_KNOWLEDGE import knowledge_base

    ad_revision = int(getattr(ad, "revision", 0) or 0)
    decisions = await store.list_continuity_decisions()
    decisions_by_key: dict[str, object] = {}
    for d in decisions:
        decisions_by_key.setdefault(d.link_key, d)

    scene_cards: list[dict] = []
    snapshots: list = []
    flat: list[tuple[int, dict, object]] = []  # (scene_idx, card, snapshot_shot)

    for order_global, scene in enumerate(scenes):
        sid = scene.get("scene_id", scene.get("id", ""))
        chapter = _as_int(scene.get("chapter"))
        session = sessions_by_scene.get(sid)
        scenario = image_plan = None
        if session:
            version = await store.get_active_version(session.session_id)
            if version:
                scenario = version.video_scenario
                image_plan = version.image_description

        snap = build_scene_snapshot(
            scene,
            order_global=order_global,
            session=session,
            scenario=scenario,
            art_direction=ad,
            visual_context=None,
        )
        snapshots.append(snap)
        snap_by_shot = {s.shot_id: s for s in snap.shots}

        location_name = image_plan.location.name if image_plan and image_plan.location else ""
        char_names = [c.name for c in image_plan.characters] if image_plan else []
        scene_title = scenario.title if scenario else ""
        continuity_ctx, _stale = await _applied_continuity_context(store, sid, ad)
        images = {a.asset_id: a for a in images_by_scene.get(sid, [])}
        videos = videos_by_scene.get(sid, [])

        ordered_shots = sorted(scenario.shots, key=lambda x: x.order) if scenario and scenario.shots else []
        cards: list[dict] = []
        for idx, sh in enumerate(ordered_shots):
            resolved = resolve_shot(
                ad,
                sh,
                location_name,
                char_names,
                knowledge_base.styles,
                knowledge_base.locations,
                scene_title,
                continuity_ctx or None,
            )
            resolved_prompt = resolved["resolved_prompt"]
            frame = reel.frame_state(sh, images.get(sh.approved_image_asset_id), resolved_prompt)
            video_asset = reel.video_for_shot(videos, sh)
            clip = reel.clip_state(
                video_asset,
                shot_frame_id=sh.approved_image_asset_id,
                resolved_prompt=resolved_prompt,
                art_direction_revision=ad_revision,
            )
            if video_asset is not None:
                gen = video_asset.generation
                clip["executor"] = {
                    "provider": getattr(gen, "provider", None),
                    "backend": getattr(gen, "backend", None),
                    "workflow_used": getattr(gen, "workflow_used", None),
                    "model": getattr(gen, "model", None),
                    "media_id": getattr(gen, "media_id", None),
                }
                clip["created_at"] = video_asset.created_at
            card = {
                "shot_id": sh.shot_id,
                "order": sh.order,
                "index": idx,
                "shot_type": sh.shot_type,
                "description": sh.description,
                "duration_sec": sh.duration_sec,
                "transition_to_next": sh.transition_to_next,
                "frame": frame,
                "video": clip,
                "resolved_prompt": resolved_prompt,
                "continuity_next": None,
            }
            cards.append(card)
            flat.append((len(scene_cards), card, snap_by_shot.get(sh.shot_id)))

        scene_cards.append(
            {
                "scene_id": sid,
                "chapter": chapter,
                "index_in_episode": ep_index_by_id.get(sid, -1),
                "order_global": order_global,
                "title": scene.get("title", ""),
                "location": scene.get("location", ""),
                "characters": scene.get("characters") or [],
                "has_session": session is not None,
                "session_id": session.session_id if session else None,
                "session_status": session.status.value if session else None,
                "approved_image_asset_id": session.approved_image_asset_id if session else None,
                "shot_count": len(cards),
                "total_duration_sec": round(sum(float(c["duration_sec"] or 0) for c in cards), 2),
                "continuity_from_prev_scene": None,
                "transfer": None,
                "shots": cards,
                "warnings": [],
            }
        )

    # 1. Границы планов: непрерывный поток (внутри сцены и между сценами).
    for i in range(len(flat) - 1):
        scene_a, card_a, snap_a = flat[i]
        scene_b, _card_b, snap_b = flat[i + 1]
        if snap_a is None or snap_b is None:
            continue
        relation = RELATION_SHOTS if scene_a == scene_b else RELATION_SCENE_BOUNDARY
        from_scene = scene_cards[scene_a]["scene_id"]
        to_scene = scene_cards[scene_b]["scene_id"]
        link = compare_shots(snap_a, snap_b, relation=relation, from_scene_id=from_scene, to_scene_id=to_scene)
        link.basis = make_basis(
            scene_id=to_scene,
            art_direction_revision=ad_revision,
            from_approved=snap_a.approved_image_asset_id,
            to_approved=snap_b.approved_image_asset_id,
        )
        apply_decisions([link], decisions_by_key)
        card_a["continuity_next"] = _reel_link_summary(link)

    # 2. Границы сцен (сравнение сцен как целого) + метка применённого переноса.
    for j, card in enumerate(scene_cards):
        sid = card["scene_id"]
        if j > 0:
            prev_snap, cur_snap = snapshots[j - 1], snapshots[j]
            adjacent = compare_scenes(prev_snap, cur_snap, relation=RELATION_ADJACENT)
            adjacent.basis = make_basis(
                scene_id=sid,
                art_direction_revision=ad_revision,
                from_approved=prev_snap.approved_image_asset_id,
                to_approved=cur_snap.approved_image_asset_id,
            )
            apply_decisions([adjacent], decisions_by_key)
            card["continuity_from_prev_scene"] = _reel_link_summary(adjacent)
        basis = make_apply_basis(scene_id=sid, art_direction_revision=ad_revision)
        decision, stale = find_applied_decision(decisions, sid, basis)
        if decision is not None or stale:
            card["transfer"] = {
                "applied": decision is not None,
                "stale": stale,
                "from_scene_id": prev_scene_by_id.get(sid),
                "note": decision.note if decision else "",
            }

    # 3. Плоская последовательность (для предпросмотра) + сводка.
    sequence: list[dict] = []
    clip_count = frame_count = placeholder_count = mock_count = stale_count = 0
    for card in scene_cards:
        for sh_card in card["shots"]:
            video = sh_card["video"]
            vstatus = video["status"]
            if vstatus in (reel.CLIP_READY, reel.CLIP_MOCK, reel.CLIP_STALE):
                kind = "clip"
                clip_count += 1
                if vstatus == reel.CLIP_MOCK:
                    mock_count += 1
                if vstatus == reel.CLIP_STALE:
                    stale_count += 1
            elif sh_card["frame"]["status"] in (reel.FRAME_APPROVED, reel.FRAME_NEEDS_UPDATE):
                kind = "frame"
                frame_count += 1
            else:
                kind = "placeholder"
                placeholder_count += 1
            sequence.append(
                {
                    "scene_id": card["scene_id"],
                    "chapter": card["chapter"],
                    "index_in_episode": card["index_in_episode"],
                    "shot_id": sh_card["shot_id"],
                    "shot_order": sh_card["order"],
                    "shot_index": sh_card["index"],
                    "kind": kind,
                    "frame_asset_id": sh_card["frame"]["asset_id"],
                    "clip_asset_id": video["asset_id"] if kind == "clip" else None,
                    "clip_status": vstatus,
                    "duration_sec": sh_card["duration_sec"],
                    "transition_to_next": sh_card["transition_to_next"],
                    "description": sh_card["description"],
                }
            )

    total_duration = round(sum(float(s["duration_sec"] or 0) for s in sequence), 2)
    return {
        "scope": scope,
        "scenes": scene_cards,
        "sequence": sequence,
        "summary": {
            "scene_count": len(scene_cards),
            "shot_count": len(sequence),
            "clip_count": clip_count,
            "frame_count": frame_count,
            "placeholder_count": placeholder_count,
            "mock_count": mock_count,
            "stale_count": stale_count,
            "total_duration_sec": total_duration,
        },
        "limitations": limitations,
    }


async def _collect_reel(
    user: dict,
    chapter: int | None,
    scene_id: str | None,
    scene_ids: str | None,
) -> dict:
    """Собрать данные ленты области (общая логика ``/reel`` и ``/sequence``).

    Порядок всегда канонический (геном): лента не переупорядочивает сцены и
    планы. Read-only, без генерации.
    """
    from core.routes.book import _get_genome_data
    from visual_assets.schemas import AssetType

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []
    by_id = {s.get("scene_id", s.get("id", "")): s for s in scenes}
    ordered_ids = [s.get("scene_id", s.get("id", "")) for s in scenes if s.get("scene_id", s.get("id", ""))]

    limitations: list[str] = []
    scope = REEL_SCOPE_FILM
    if scene_id:
        if scene_id not in by_id:
            raise HTTPException(404, "Scene not found")
        chosen_set = {scene_id}
        scope = REEL_SCOPE_SCENE
    elif scene_ids:
        requested = [s.strip() for s in scene_ids.split(",") if s.strip()]
        missing = [s for s in requested if s not in by_id]
        if missing:
            limitations.append(f"Не найдены сцены: {', '.join(missing)} — пропущены.")
        chosen_set = {s for s in requested if s in by_id}
        scope = REEL_SCOPE_SEQUENCE
    elif chapter is not None:
        chosen_set = {sid for sid in ordered_ids if _as_int(by_id[sid].get("chapter")) == chapter}
        scope = REEL_SCOPE_EPISODE
    else:
        # Весь фильм: все сцены генома во всех эпизодах.
        chosen_set = set(ordered_ids)

    # Порядок ВСЕГДА канонический (геном): лента не переупорядочивает сцены/планы.
    chosen = [sid for sid in ordered_ids if sid in chosen_set]
    if not chosen:
        limitations.append("В выбранной области нет сцен.")

    store = _get_store()
    ad = await _load_art_direction()
    sessions = await store.list_sessions(user_id=user.get("user_id", ""), limit=1000, offset=0)
    sessions_by_scene: dict[str, object] = {}
    for s in sessions:
        if s.scene_id and s.scene_id not in sessions_by_scene:
            sessions_by_scene[s.scene_id] = s

    asset_store = registry.get("asset_store")
    images_by_scene: dict[str, list] = {}
    videos_by_scene: dict[str, list] = {}
    for sid in chosen:
        ch = _as_int(by_id[sid].get("chapter"))
        try:
            images_by_scene[sid] = await asset_store.list_assets(chapter=ch, asset_type=AssetType.IMAGE, scene_id=sid, limit=200)
            videos_by_scene[sid] = await asset_store.list_assets(chapter=ch, asset_type=AssetType.VIDEO, scene_id=sid, limit=200)
        except Exception as e:  # хранилище недоступно — лента всё равно строится
            log.warning("reel_assets_failed scene=%s: %s", sid, e)
            images_by_scene[sid] = []
            videos_by_scene[sid] = []
            limitations.append(f"Ассеты сцены «{sid}» недоступны — статусы кадров/клипов неполны.")

    # Канонический индекс сцены внутри эпизода (по всем сценам генома).
    ep_index_by_id: dict[str, int] = {}
    counts: dict[int, int] = {}
    for sid in ordered_ids:
        ch = _as_int(by_id[sid].get("chapter"))
        ep_index_by_id[sid] = counts.get(ch, 0)
        counts[ch] = counts.get(ch, 0) + 1

    prev_scene_by_id = {sid: _prev_scene_id(by_id, ordered_ids, sid) for sid in chosen}

    data = await _build_reel_data(
        store,
        [by_id[sid] for sid in chosen],
        scope,
        ad,
        sessions_by_scene,
        images_by_scene,
        videos_by_scene,
        ep_index_by_id,
        prev_scene_by_id,
        limitations,
    )
    data["chapter"] = chapter
    data["scene_ids"] = chosen
    data["film"] = {
        "book_id": genome.get("book_id", "arkaim"),
        "title": genome.get("title", ""),
        "episode_count": len({_as_int(by_id[sid].get("chapter")) for sid in chosen}),
    }
    return data


@router.get(
    "/reel",
    dependencies=[Depends(require_role("reader"))],
    summary="Лента фильма: Эпизод → Сцена → План → Кадр → Клип",
)
async def get_reel(
    chapter: int | None = Query(None, ge=1),
    scene_id: str | None = Query(None),
    scene_ids: str | None = Query(None),
    user: dict = Depends(require_role("reader")),
):
    """Режиссёрская лента: канонический порядок сцен и планов + состояние
    кадров/клипов, переходы и связность на границах. Read-only, без генерации.

    Область: ``scene_id`` — одна сцена; ``scene_ids`` (через запятую) —
    последовательность связанных сцен; ``chapter`` — весь эпизод (глава);
    без параметров — весь фильм (все эпизоды). Порядок всегда канонический
    (геном), ассеты лишь привязываются.
    """
    data = await _collect_reel(user, chapter, scene_id, scene_ids)
    return SuccessResponse(data=data)


# ── 0.3 План сборки последовательности (Фаза 4: тайминг · разрывы · пере-
#        ходы · исполнители · текст плана; без монтажа) ──────────────


@router.get(
    "/sequence",
    dependencies=[Depends(require_role("reader"))],
    summary="План сборки последовательности фильма (read-only, без монтажа)",
)
async def get_sequence(
    chapter: int | None = Query(None, ge=1),
    scene_id: str | None = Query(None),
    scene_ids: str | None = Query(None),
    user: dict = Depends(require_role("reader")),
):
    """Режиссёрский план сборки: накопительный тайминг отрезков, разрывы (где
    нет готового клипа), переходы на стыках, сводка исполнителей (в т.ч. флаг
    «смешанные исполнители») и текстовый план для внешнего монтажа.

    Read-only проекция уже существующей ленты: ничего не создаёт, не монтирует
    и не запускает генерацию. Область — как у ``/studio/reel``; без параметров —
    весь фильм.
    """
    from studio import sequence as sequence_mod

    data = await _collect_reel(user, chapter, scene_id, scene_ids)
    plan = sequence_mod.build_plan(data["scenes"], limitations=list(data.get("limitations") or []))
    plan["scope"] = data["scope"]
    plan["chapter"] = data["chapter"]
    plan["scene_ids"] = data["scene_ids"]
    plan["film"] = data["film"]
    plan["plan_text"] = sequence_mod.render_plan_text(plan)
    plan["edl_xml"] = sequence_mod.render_edl(plan, book_title=data["film"].get("title", "Наследие Аркаима"))
    return SuccessResponse(data=plan)


# ── 0.2 Continuity (связность планов/сцен/эпизодов, Studio Phase 1) ──


async def _try_build_visual_context(chapter: int, scene_id: str, limitations: list[str]):
    """Визуальный контекст сцены (best-effort): отсутствие не ломает отчёт."""
    try:
        vcb = registry.get("visual_context_builder")
        return await vcb.build_scene_context(chapter, scene_id)
    except Exception as e:
        log.warning("continuity_visual_context_failed scene=%s: %s", scene_id, e)
        limitations.append(f"Визуальный контекст сцены «{scene_id}» недоступен — окружение/свет/палитра не сравнивались.")
        return None


async def _scene_continuity_snapshot(store, scene: dict, order_global: int, ad, with_context: bool, sessions_by_scene: dict, limitations: list[str]):
    """Снимок сцены для связности: переиспользует существующие источники."""
    from studio.continuity import build_scene_snapshot

    sid = scene.get("scene_id", scene.get("id", ""))
    session = sessions_by_scene.get(sid)
    scenario = None
    if session:
        version = await store.get_active_version(session.session_id)
        scenario = version.video_scenario if version else None
    visual_context = None
    if with_context:
        visual_context = await _try_build_visual_context(_as_int(scene.get("chapter")), sid, limitations)
    return build_scene_snapshot(
        scene,
        order_global=order_global,
        session=session,
        scenario=scenario,
        art_direction=ad,
        visual_context=visual_context,
    )


async def _build_continuity(store, scene: dict, by_id: dict, ordered_ids: list, order_by_id: dict, ad, sessions_by_scene: dict, with_context: bool) -> dict:
    """Собрать связи сцены (внутри сцены, граница сцен, соседи, кросс-эпизод).

    Общий код для отчёта сцены и сводки по фильму. Ничего не записывает.
    """
    from studio.continuity import (
        RELATION_ADJACENT,
        RELATION_CROSS_EPISODE,
        RELATION_SCENE_BOUNDARY,
        apply_decisions,
        clip_boundary_for,
        compare_scenes,
        compare_shots,
        cross_episode_candidates,
        make_basis,
        mark_candidate,
        overall_status,
    )

    scene_id = scene.get("scene_id", scene.get("id", ""))
    chapter_val = _as_int(scene.get("chapter"))
    limitations: list[str] = []
    current = await _scene_continuity_snapshot(store, scene, order_by_id.get(scene_id, -1), ad, with_context, sessions_by_scene, limitations)

    ep_ids = [sid for sid in ordered_ids if _as_int(by_id[sid].get("chapter")) == chapter_val]
    idx_in_ep = ep_ids.index(scene_id) if scene_id in ep_ids else -1
    prev_id = ep_ids[idx_in_ep - 1] if idx_in_ep > 0 else None
    next_id = ep_ids[idx_in_ep + 1] if 0 <= idx_in_ep < len(ep_ids) - 1 else None

    links = []

    # 1. Внутри сцены: соседние планы
    for i in range(len(current.shots) - 1):
        a, b = current.shots[i], current.shots[i + 1]
        link = compare_shots(a, b, from_scene_id=scene_id, to_scene_id=scene_id)
        link.basis = make_basis(
            scene_id=scene_id,
            art_direction_revision=current.art_direction_revision,
            from_approved=a.approved_image_asset_id,
            to_approved=b.approved_image_asset_id,
        )
        links.append(link)

    if prev_id:
        prev_snap = await _scene_continuity_snapshot(store, by_id[prev_id], order_by_id.get(prev_id, -1), ad, with_context, sessions_by_scene, limitations)
        # 2. Граница сцен: последний план предыдущей → первый план текущей
        if prev_snap.shots and current.shots:
            boundary = compare_shots(
                prev_snap.shots[-1],
                current.shots[0],
                relation=RELATION_SCENE_BOUNDARY,
                from_scene_id=prev_id,
                to_scene_id=scene_id,
            )
            boundary.basis = make_basis(
                scene_id=scene_id,
                art_direction_revision=current.art_direction_revision,
                from_approved=prev_snap.shots[-1].approved_image_asset_id,
                to_approved=current.shots[0].approved_image_asset_id,
            )
            links.append(boundary)
        # 3. Соседние сцены одного эпизода
        adjacent = compare_scenes(prev_snap, current, relation=RELATION_ADJACENT)
        adjacent.basis = make_basis(
            scene_id=scene_id,
            art_direction_revision=current.art_direction_revision,
            from_approved=prev_snap.approved_image_asset_id,
            to_approved=current.approved_image_asset_id,
        )
        adjacent.clip_boundary = clip_boundary_for(prev_snap, current)
        links.append(adjacent)
    else:
        limitations.append("Предыдущей сцены в этом эпизоде нет — связь между сценами не проверялась.")

    # 4. Смысловые связи разных эпизодов (кандидаты по meaning_tags генома)
    candidates = cross_episode_candidates(scene, [by_id[sid] for sid in ordered_ids], order_by_id)
    if len(candidates) > 20:
        limitations.append("Смысловых связей-кандидатов больше 20 — показаны первые 20.")
        candidates = candidates[:20]
    for other_id, tag in candidates:
        other = by_id.get(other_id)
        if not other:
            continue
        other_snap = await _scene_continuity_snapshot(store, other, order_by_id.get(other_id, -1), ad, with_context, sessions_by_scene, limitations)
        clink = compare_scenes(
            other_snap,
            current,
            relation=RELATION_CROSS_EPISODE,
            certainty="candidate",
            reason=f"Общая сюжетная метка генома: {tag}",
        )
        mark_candidate(clink)
        clink.basis = make_basis(
            scene_id=scene_id,
            art_direction_revision=current.art_direction_revision,
            from_approved=other_snap.approved_image_asset_id,
            to_approved=current.approved_image_asset_id,
        )
        links.append(clink)

    decisions = await store.list_continuity_decisions()
    decisions_by_key: dict[str, object] = {}
    for d in decisions:
        decisions_by_key.setdefault(d.link_key, d)
    apply_decisions(links, decisions_by_key)

    if not current.has_scenario:
        limitations.append("У сцены нет активного сценарного плана — планы и границы сцен не проверялись.")
    if not with_context:
        limitations.append("Визуальный контекст не запрашивался (with_context=false) — окружение/свет/палитра не сравнивались.")

    return {
        "scene": current,
        "links": links,
        "overall_status": overall_status(links),
        "limitations": limitations,
        "neighbors": {"prev_scene_id": prev_id, "next_scene_id": next_id},
        "episode": {"chapter": chapter_val, "index_in_episode": idx_in_ep, "scene_count": len(ep_ids)},
    }


@router.get(
    "/scenes/{scene_id}/continuity",
    dependencies=[Depends(require_role("reader"))],
    summary="Связность сцены: соседние планы, соседние сцены, смысловые связи",
)
async def scene_continuity(
    scene_id: str,
    chapter: int | None = Query(None),
    with_context: bool = Query(True),
    user: dict = Depends(require_role("reader")),
):
    """Проверки связности для сцены (read-only, без генерации).

    Переиспользует геном (canonical сцены), активную версию сессии (планы),
    общие правила фильма (утверждённые образы) и визуальный контекст. Ничего
    не создаёт, не переписывает сценарий/промпты и не удаляет.

    Отсутствующие характеристики НЕ сравниваются — отсутствие данных
    отражается в limitations и в known_fields, а не подменяется догадкой.
    """
    from core.routes.book import _get_genome_data

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []
    by_id = {s.get("scene_id", s.get("id", "")): s for s in scenes}
    scene = by_id.get(scene_id)
    if scene is None:
        raise HTTPException(404, "Scene not found")

    ordered_ids = [s.get("scene_id", s.get("id", "")) for s in scenes if s.get("scene_id", s.get("id", ""))]
    order_by_id = {sid: i for i, sid in enumerate(ordered_ids)}

    store = _get_store()
    ad = await _load_art_direction()
    sessions = await store.list_sessions(user_id=user.get("user_id", ""), limit=1000, offset=0)
    sessions_by_scene: dict[str, object] = {}
    for s in sessions:
        if s.scene_id and s.scene_id not in sessions_by_scene:
            sessions_by_scene[s.scene_id] = s

    result = await _build_continuity(store, scene, by_id, ordered_ids, order_by_id, ad, sessions_by_scene, with_context)
    return SuccessResponse(
        data={
            "scene": result["scene"].model_dump(),
            "links": [link.model_dump() for link in result["links"]],
            "overall_status": result["overall_status"],
            "limitations": result["limitations"],
            "neighbors": result["neighbors"],
            "episode": result["episode"],
        }
    )


@router.get(
    "/continuity/summary",
    dependencies=[Depends(require_role("reader"))],
    summary="Сводка связности по всем сценам фильма (для дерева)",
)
async def continuity_summary(user: dict = Depends(require_role("reader"))):
    """Лёгкая проекция связности по всем сценам (без визуального контекста).

    Позволяет дереву фильма показать метку «есть потенциальное
    несоответствие», не открывая каждую сцену. Ничего не создаёт."""
    from core.routes.book import _get_genome_data

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []
    by_id = {s.get("scene_id", s.get("id", "")): s for s in scenes}
    ordered_ids = [s.get("scene_id", s.get("id", "")) for s in scenes if s.get("scene_id", s.get("id", ""))]
    order_by_id = {sid: i for i, sid in enumerate(ordered_ids)}

    store = _get_store()
    ad = await _load_art_direction()
    sessions = await store.list_sessions(user_id=user.get("user_id", ""), limit=1000, offset=0)
    sessions_by_scene: dict[str, object] = {}
    for s in sessions:
        if s.scene_id and s.scene_id not in sessions_by_scene:
            sessions_by_scene[s.scene_id] = s

    summary: dict[str, dict] = {}
    for s in scenes:
        sid = s.get("scene_id", s.get("id", ""))
        if not sid:
            continue
        result = await _build_continuity(store, s, by_id, ordered_ids, order_by_id, ad, sessions_by_scene, False)
        links = result["links"]
        summary[sid] = {
            "overall_status": result["overall_status"],
            "mismatch_count": sum(1 for link in links if link.status == "mismatch"),
            "waived_count": sum(1 for link in links if link.status == "waived"),
            "pending_count": sum(1 for link in links if link.status == "consistent" and link.findings),
            "link_count": len(links),
        }
    return SuccessResponse(data={"scenes": summary, "with_context": False})


class _ContinuityDecisionRequest(BaseModel):
    link_key: str = Field(..., min_length=1)
    note: str = ""
    basis: dict = Field(default_factory=dict)
    session_id: str | None = None
    decision_id: str | None = None


@router.post(
    "/continuity/decisions",
    dependencies=[Depends(require_role("editor"))],
    summary="Разрешить отличие связности (решение режиссёра)",
)
async def create_continuity_decision(
    req: _ContinuityDecisionRequest,
    user: dict = Depends(require_role("editor")),
):
    """Зафиксировать осознанное отличие по связи.

    Решение сохраняется в studio.db и переживает перезагрузку. basis —
    отпечаток контекста (утверждённые кадры + revision общих правил),
    полученный из GET .../continuity; при изменении контекста решение
    помечается устаревшим и связь снова требует просмотра.
    """
    from studio.continuity import ContinuityDecision

    store = _get_store()
    existing = None
    if req.decision_id:
        existing = await store.get_continuity_decision(req.decision_id)
    if existing is None:
        for d in await store.list_continuity_decisions():
            if d.link_key == req.link_key:
                existing = d
                break
    decision = existing or ContinuityDecision(decision_id=_new_id("cont"), link_key=req.link_key)
    decision.link_key = req.link_key
    decision.session_id = req.session_id or decision.session_id or ""
    decision.note = req.note
    decision.by = user.get("user_id", "")
    if req.basis:
        decision.basis = req.basis
    decision.stale = False
    await store.save_continuity_decision(decision)
    log.info("continuity_decision_saved link=%s by=%s", decision.link_key, decision.by)
    return SuccessResponse(data=decision.model_dump())


@router.delete(
    "/continuity/decisions/{decision_id}",
    dependencies=[Depends(require_role("editor"))],
    summary="Снять решение по связности",
)
async def delete_continuity_decision_route(decision_id: str):
    store = _get_store()
    if not await store.delete_continuity_decision(decision_id):
        raise HTTPException(404, "Decision not found")
    return SuccessResponse(data={"deleted": decision_id})


def _prev_scene_id(by_id: dict, ordered_ids: list[str], scene_id: str) -> str | None:
    """Предыдущая сцена в пределах того же эпизода (главы), иначе None."""
    scene = by_id.get(scene_id)
    if scene is None:
        return None
    chapter_val = _as_int(scene.get("chapter"))
    ep_ids = [sid for sid in ordered_ids if _as_int(by_id[sid].get("chapter")) == chapter_val]
    if scene_id in ep_ids:
        i = ep_ids.index(scene_id)
        if i > 0:
            return ep_ids[i - 1]
    return None


async def _continuity_transfer(store, session, by_id, ordered_ids, order_by_id, ad, limitations) -> dict | None:
    """Собрать переносимые ограничения из предыдущей связанной сцены.

    Общий код предпросмотра «Согласовать со сценой» и применения переноса.
    Возвращает None, если предыдущей связанной сцены нет.
    """
    from studio.continuity import make_apply_basis, transfer_constraints

    scene = by_id.get(session.scene_id)
    if scene is None:
        return None
    prev_id = _prev_scene_id(by_id, ordered_ids, session.scene_id)
    if not prev_id:
        return None

    sessions_by_scene = {session.scene_id: session}
    prev_snap = await _scene_continuity_snapshot(store, by_id[prev_id], order_by_id.get(prev_id, -1), ad, True, sessions_by_scene, limitations)
    current_snap = await _scene_continuity_snapshot(store, scene, order_by_id.get(session.scene_id, -1), ad, False, sessions_by_scene, limitations)
    constraints, sources = transfer_constraints(prev_snap)
    basis = make_apply_basis(
        scene_id=session.scene_id,
        art_direction_revision=current_snap.art_direction_revision,
    )
    return {
        "from_scene_id": prev_id,
        "to_scene_id": session.scene_id,
        "constraints": constraints,
        "sources": sources,
        "basis": basis,
        "prev_snap": prev_snap,
        "current_snap": current_snap,
    }


async def _applied_continuity_context(store, scene_id: str, ad) -> tuple[dict, bool]:
    """Действующий перенос ограничений для сцены (Фаза 2).

    Возвращает ({constraints}, stale). Пустой словарь, если перенос не применён
    или решение устарело (устаревшее НЕ применяется молча).
    """
    from studio.continuity import find_applied_decision, make_apply_basis

    decisions = await store.list_continuity_decisions()
    basis = make_apply_basis(
        scene_id=scene_id,
        art_direction_revision=int(getattr(ad, "revision", 0) or 0),
    )
    decision, stale = find_applied_decision(decisions, scene_id, basis)
    if decision is None:
        return {}, stale
    return dict(decision.constraints or {}), stale


class _ContinuityApplyRequest(BaseModel):
    note: str = ""


@router.post(
    "/{session_id}/continuity/apply",
    dependencies=[Depends(require_role("editor"))],
    summary="Применить перенос ограничений из связанной сцены",
)
async def continuity_apply(
    session_id: str,
    req: _ContinuityApplyRequest,
    user: dict = Depends(require_role("editor")),
):
    """Явное решение режиссёра: разрешение промптов сцены начинает учитывать
    ограничения предыдущей связанной сцены (локация/время/свет/палитра/персонажи).

    Промпты НЕ переписываются: применение влияет только на последующее
    разрешение (подготовка обновления кадра, отчёт правил). Уже утверждённые
    кадры и версии НЕ изменяются. Хранится как решение в studio.db
    (action=applied, один на сцену).
    """
    from core.routes.book import _get_genome_data
    from studio.continuity import ACTION_APPLIED, ContinuityDecision, applied_link_key

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Сессия финализирована — применение переноса недоступно.")

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []
    by_id = {s.get("scene_id", s.get("id", "")): s for s in scenes}
    ordered_ids = [s.get("scene_id", s.get("id", "")) for s in scenes if s.get("scene_id", s.get("id", ""))]
    order_by_id = {sid: i for i, sid in enumerate(ordered_ids)}

    limitations: list[str] = []
    ad = await _load_art_direction()
    transfer = await _continuity_transfer(store, session, by_id, ordered_ids, order_by_id, ad, limitations)
    if transfer is None:
        raise HTTPException(409, "Нет предыдущей связанной сцены — перенос невозможен.")
    if not transfer["constraints"]:
        raise HTTPException(409, "Нет известных характеристик для переноса.")

    link_key = applied_link_key(session.scene_id)
    existing = None
    for d in await store.list_continuity_decisions():
        if d.link_key == link_key and d.action == ACTION_APPLIED:
            existing = d
    decision = existing or ContinuityDecision(decision_id=_new_id("cont"), link_key=link_key)
    decision.link_key = link_key
    decision.action = ACTION_APPLIED
    decision.session_id = session_id
    decision.note = req.note
    decision.by = user.get("user_id", "")
    decision.basis = transfer["basis"]
    decision.constraints = transfer["constraints"]
    decision.stale = False
    await store.save_continuity_decision(decision)
    log.info("continuity_apply_saved scene=%s by=%s", session.scene_id, decision.by)
    return SuccessResponse(
        data={
            "applied": True,
            "decision": decision.model_dump(),
            "constraints": transfer["constraints"],
            "from_scene_id": transfer["from_scene_id"],
            "note": "Перенос применён. Итоговые промпты планов (подготовка кадра, отчёт правил) учитывают ограничения связанной сцены.",
        }
    )


@router.delete(
    "/{session_id}/continuity/apply",
    dependencies=[Depends(require_role("editor"))],
    summary="Отменить применение переноса ограничений",
)
async def continuity_apply_revoke(session_id: str):
    """Снять применённый перенос ограничений для сцены."""
    from studio.continuity import ACTION_APPLIED, applied_link_key

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    link_key = applied_link_key(session.scene_id)
    removed = 0
    for d in await store.list_continuity_decisions():
        if d.link_key == link_key and d.action == ACTION_APPLIED:
            if await store.delete_continuity_decision(d.decision_id):
                removed += 1
    log.info("continuity_apply_revoked scene=%s removed=%s", session.scene_id, removed)
    return SuccessResponse(data={"revoked": removed > 0, "removed": removed})


@router.get(
    "/{session_id}/continuity/match-context",
    dependencies=[Depends(require_role("reader"))],
    summary="«Согласовать со сценой»: предпросмотр переносимых ограничений",
)
async def continuity_match_context(session_id: str):
    """Показать, что можно перенести из предыдущей связанной сцены, откуда,
    как изменится итоговый промпт и какие отличия останутся.

    НИЧЕГО не записывает и не переписывает: исходный сценарий и промпты
    остаются прежними. Перенос ограничений применяется только отдельным
    решением режиссёра (POST .../continuity/apply).
    """
    from core.routes.book import _get_genome_data
    from studio.art_direction import resolve_shot
    from studio.continuity import compare_scenes, find_applied_decision
    from visual.VISUAL_KNOWLEDGE import knowledge_base

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    genome = _get_genome_data() or {}
    scenes = genome.get("modules", {}).get("scenes", []) or []
    by_id = {s.get("scene_id", s.get("id", "")): s for s in scenes}
    ordered_ids = [s.get("scene_id", s.get("id", "")) for s in scenes if s.get("scene_id", s.get("id", ""))]
    order_by_id = {sid: i for i, sid in enumerate(ordered_ids)}

    limitations: list[str] = []
    ad = await _load_art_direction()
    transfer = await _continuity_transfer(store, session, by_id, ordered_ids, order_by_id, ad, limitations)
    if transfer is None:
        return SuccessResponse(
            data={
                "available": False,
                "reason": "Нет предыдущей связанной сцены в этом эпизоде.",
                "limitations": limitations,
            }
        )

    constraints = transfer["constraints"]
    sources = transfer["sources"]
    remaining = compare_scenes(transfer["prev_snap"], transfer["current_snap"]).findings

    decisions = await store.list_continuity_decisions()
    applied_decision, applied_stale = find_applied_decision(decisions, session.scene_id, transfer["basis"])
    applied = applied_decision is not None

    version = await store.get_active_version(session_id)
    scenario = version.video_scenario if version else None
    prompt_changes: list[dict] = []
    if scenario and scenario.shots:
        image_plan = version.image_description
        loc_name = image_plan.location.name if image_plan and image_plan.location else ""
        char_names_current = [c.name for c in image_plan.characters] if image_plan else []
        style_lib = knowledge_base.styles
        vk_locations = knowledge_base.locations
        title = scenario.title
        for shot in sorted(scenario.shots, key=lambda s: s.order):
            before = resolve_shot(ad, shot, loc_name, char_names_current, style_lib, vk_locations, title)
            after = resolve_shot(ad, shot, loc_name, char_names_current, style_lib, vk_locations, title, constraints)
            changed = before["resolved_prompt"] != after["resolved_prompt"]
            prompt_changes.append(
                {
                    "shot_id": shot.shot_id,
                    "changed": changed,
                    "before": before["resolved_prompt"],
                    "after": after["resolved_prompt"],
                }
            )
    else:
        limitations.append("У сессии нет активного сценария — предпросмотр промптов недоступен.")

    if applied:
        note = (
            "Перенос применён: разрешение промптов планов (подготовка кадра, отчёт правил) учитывает ограничения связанной сцены. Исходный сценарий не изменён."
        )
    elif applied_stale:
        note = "Ранее применённый перенос устарел (изменились общие правила) и больше не действует. Подтвердите перенос заново."
    else:
        note = "Предпросмотр. Исходный сценарий и промпты НЕ изменены — перенос применяется отдельным решением режиссёра."

    return SuccessResponse(
        data={
            "available": True,
            "from_scene_id": transfer["from_scene_id"],
            "to_scene_id": transfer["to_scene_id"],
            "constraints": constraints,
            "sources": sources,
            "remaining_differences": [f.model_dump() for f in remaining],
            "prompt_changes": prompt_changes,
            "applied": applied,
            "applied_stale": applied_stale,
            "applied_decision": applied_decision.model_dump() if applied_decision else None,
            "note": note,
            "limitations": limitations,
        }
    )


# ── 0.0 Film Art Direction (общие визуальные правила фильма) ────


def _default_ad():
    from studio.art_direction import default_art_direction

    return default_art_direction()


async def _load_art_direction():
    """Сохранённые правила или дефолт (revision=0 — ещё не сохранялись)."""
    store = _get_store()
    ad = await store.get_art_direction()
    return ad if ad is not None else _default_ad()


@router.get(
    "/art-direction",
    dependencies=[Depends(require_role("reader"))],
    summary="Общие визуальные правила фильма",
)
async def get_art_direction_route():
    """Единый редактируемый источник film-wide правил (стиль, палитра,
    персонажи/локации со ссылками на Visual Knowledge, правила композиции
    и освещения). Хранится в существующей studio.db, дублей не создаётся."""
    return SuccessResponse(data=(await _load_art_direction()).model_dump())


@router.put(
    "/art-direction",
    dependencies=[Depends(require_role("editor"))],
    summary="Сохранить общие визуальные правила фильма",
)
async def put_art_direction_route(req: "FilmArtDirection"):
    """Сохраняет правила целиком. revision растёт ТОЛЬКО при фактическом
    изменении (diff по секциям), last_change_sections запоминает, что
    изменилось — это причина «затронутости» ранее подготовленных артефактов.
    Ручные правки шотов и утверждённые результаты НЕ трогаются."""
    from studio.art_direction import diff_art_direction

    store = _get_store()
    current = await store.get_art_direction()
    if current is None:
        current = _default_ad()
    changed = diff_art_direction(current, req)
    saved = req.model_copy(deep=True)
    if changed:
        saved.revision = current.revision + 1
        saved.last_change_sections = changed
    else:
        saved.revision = current.revision
        saved.last_change_sections = list(current.last_change_sections)
    saved.updated_at = _now()
    await store.save_art_direction(saved)
    return SuccessResponse(data={"art_direction": saved.model_dump(), "changed_sections": changed})


@router.get(
    "/art-direction/library",
    dependencies=[Depends(require_role("reader"))],
    summary="Библиотеки Visual Knowledge для правил фильма",
)
async def art_direction_library():
    """Справочники Visual Knowledge (read-only) для заполнения правил:
    стили (STYLE_LIBRARY), персонажи (CHARACTER_VISUALS), локации
    (LOCATION_VISUALS). Правила фильма лишь ссылаются на эти ключи —
    данные не копируются и не дублируются."""
    from visual.VISUAL_KNOWLEDGE import knowledge_base

    def _char_summary(name: str, data: dict) -> dict:
        return {
            "name": name,
            "build": data.get("build", ""),
            "face": data.get("face", ""),
            "style_constants": data.get("style_constants", []),
        }

    def _loc_summary(name: str, data: dict) -> dict:
        return {
            "name": name,
            "type": data.get("type", ""),
            "palette": data.get("palette", []),
            "atmosphere": (data.get("atmosphere") or {}).get("default", ""),
        }

    styles = {
        k: {
            "prefix": v.get("prefix", ""),
            "aspect_ratio": v.get("aspect_ratio", ""),
            "description": v.get("description", ""),
            "negative_additions": v.get("negative_additions", []),
        }
        for k, v in knowledge_base.styles.items()
        if isinstance(v, dict)
    }
    characters = {k: _char_summary(k, v) for k, v in knowledge_base.characters.items() if isinstance(v, dict)}
    locations = {k: _loc_summary(k, v) for k, v in knowledge_base.locations.items() if isinstance(v, dict)}
    return SuccessResponse(data={"styles": styles, "characters": characters, "locations": locations})


@router.get(
    "/{session_id}/art-direction/apply",
    dependencies=[Depends(require_role("reader"))],
    summary="Применение общих правил к планам сцены",
)
async def apply_art_direction(session_id: str):
    """Полный отчёт для режиссёра: какие общие правила применяются к каждому
    плану, что задано локально, какой итоговый промпт, и какие ранее
    подготовленные артефакты затронуты изменениями правил.

    Ничего не пересоздаёт и не удаляет — только вычисляет и показывает."""
    from studio.art_direction import resolve_shot
    from visual.VISUAL_KNOWLEDGE import knowledge_base
    from visual_assets.schemas import AssetStatus, AssetType

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    version = await store.get_active_version(session_id)
    if not version:
        raise HTTPException(400, "Session has no active version")
    ad = await _load_art_direction()

    image_plan = version.image_description
    scenario = version.video_scenario
    location_name = image_plan.location.name if image_plan and image_plan.location else ""
    char_names = [c.name for c in image_plan.characters] if image_plan else []
    scene_title = scenario.title if scenario else ""
    style_lib = knowledge_base.styles
    vk_locations = knowledge_base.locations
    continuity_ctx, continuity_stale = await _applied_continuity_context(store, session.scene_id, ad)

    shots_report: list[dict] = []
    total_duration = 0.0
    if scenario:
        ordered = sorted(scenario.shots, key=lambda s: s.order)
        for idx, shot in enumerate(ordered):
            resolved = resolve_shot(ad, shot, location_name, char_names, style_lib, vk_locations, scene_title, continuity_ctx or None)
            total_duration += float(shot.duration_sec or 0)
            shots_report.append(
                {
                    "shot_index": idx,
                    "shot_id": shot.shot_id,
                    "order": shot.order,
                    "shot_type": shot.shot_type,
                    "duration_sec": shot.duration_sec,
                    "approved_image_asset_id": shot.approved_image_asset_id,
                    **resolved,
                }
            )

    # ── Затронутые изменениями правил артефакты (без пересоздания) ──
    affected: list[dict] = []
    stale_videos: list[dict] = []
    assets = await registry.get("asset_store").list_assets(chapter=session.chapter, scene_id=session.scene_id, limit=300)
    prepared_list = await store.list_prepared_updates(session_id)
    prepared_by_source = {p.source_asset_id: p for p in prepared_list if p.source_asset_id}
    prepared_by_new = {p.new_asset_id: p for p in prepared_list if p.new_asset_id}
    shot_ctx_by_id = {s["shot_id"]: s for s in shots_report}
    shot_approved_ids = {s["approved_image_asset_id"] for s in shots_report if s.get("approved_image_asset_id")}
    approved = session.approved_image_asset_id
    img_prompt = image_plan.prompt if image_plan else ""

    if ad.revision > 0:
        for a in assets:
            if a.status != AssetStatus.COMPLETED:
                continue
            reasons: list[str] = []
            gen_rev = a.generation.art_direction_revision if a.generation else None
            if gen_rev is None:
                reasons.append(f"создано до введения общих правил (сейчас rev {ad.revision})")
            elif gen_rev < ad.revision:
                reasons.append(f"общие правила обновлялись после генерации (rev {gen_rev} → {ad.revision})")
            if a.asset_type == AssetType.IMAGE and img_prompt:
                used = " ".join((a.prompt_used or "").split())
                current = " ".join(img_prompt.split())
                if used and current and used != current:
                    reasons.append("промпт изображения сцены изменился")
            if a.asset_type == AssetType.VIDEO and approved:
                ref = a.generation.reference_image_id if a.generation else None
                if ref != approved:
                    reasons.append("кадр-основа не совпадает с утверждённым кадром сцены")
            if not reasons:
                continue
            gen_shot_id = a.generation.shot_id if a.generation else None
            shot_ctx = shot_ctx_by_id.get(gen_shot_id) if gen_shot_id else None
            prepared_src = prepared_by_source.get(a.asset_id)
            prepared_new = prepared_by_new.get(a.asset_id)
            if a.asset_id == approved or a.asset_id in shot_approved_ids:
                frame_status = "approved"
            elif prepared_new and prepared_new.status in ("done", "approved"):
                frame_status = "new_variant"
            elif prepared_src and prepared_src.status in ("prepared", "generating"):
                frame_status = "prepared_for_update"
            else:
                frame_status = "needs_update"
            affected.append(
                {
                    "asset_id": a.asset_id,
                    "asset_type": a.asset_type.value,
                    "title": a.title,
                    "status": a.status.value,
                    "reasons": reasons,
                    "created_at": a.created_at,
                    "prompt_used": a.prompt_used or "",
                    "shot_id": gen_shot_id,
                    "shot": shot_ctx,
                    "frame_status": frame_status,
                    "prepared": (
                        {
                            "prepared_id": prepared_src.prepared_id,
                            "status": prepared_src.status,
                            "new_asset_id": prepared_src.new_asset_id,
                        }
                        if prepared_src
                        else (
                            {
                                "prepared_id": prepared_new.prepared_id,
                                "status": prepared_new.status,
                                "new_asset_id": prepared_new.new_asset_id,
                            }
                            if prepared_new
                            else None
                        )
                    ),
                }
            )

    # ── Видео, снятые со старого кадра (после утверждения нового) ──
    if approved:
        for a in assets:
            if a.asset_type != AssetType.VIDEO or a.status != AssetStatus.COMPLETED:
                continue
            ref = a.generation.reference_image_id if a.generation else None
            if ref and ref != approved:
                stale_videos.append(
                    {
                        "asset_id": a.asset_id,
                        "title": a.title,
                        "reference_image_id": ref,
                        "current_approved": approved,
                        "reason": "видео основано на предыдущем кадре (требует обновления)",
                    }
                )

    return SuccessResponse(
        data={
            "art_direction": ad.model_dump(),
            "scene": {
                "scene_id": session.scene_id,
                "chapter": session.chapter,
                "title": scene_title,
                "location": location_name,
                "characters": char_names,
                "approved_image_asset_id": session.approved_image_asset_id,
            },
            "episode": {
                "shot_count": len(shots_report),
                "total_duration_sec": total_duration,
                "style_label": ad.style_preset,
                "revision": ad.revision,
                "last_change_sections": list(ad.last_change_sections),
            },
            "shots": shots_report,
            "affected_artifacts": affected,
            "prepared_updates": [p.model_dump() for p in prepared_list],
            "stale_videos": stale_videos,
            "continuity": {
                "applied": bool(continuity_ctx),
                "stale": continuity_stale,
                "constraints": continuity_ctx,
            },
        }
    )


# ── 0.1.1 Managed frame update (подготовленные обновления кадров) ─────────


async def _collect_prepared_references(ad, resolved: dict) -> list[str]:
    """Референсы задания: общие правила + утверждённые образы персонажей/локации."""
    refs: list[str] = [r for r in (ad.reference_asset_ids or []) if r]
    applied = resolved.get("applied") or {}
    for ch in applied.get("characters") or []:
        img = ch.get("approved_image_asset_id") if isinstance(ch, dict) else None
        if img and img not in refs:
            refs.append(img)
    loc = applied.get("location")
    if isinstance(loc, dict):
        loc_ref = loc.get("reference_asset_id")
        if loc_ref and loc_ref not in refs:
            refs.append(loc_ref)
    return refs


@router.post(
    "/{session_id}/prepared-updates",
    dependencies=[Depends(require_role("editor"))],
    summary="Подготовить обновление кадра (без генерации)",
)
async def create_prepared_update(session_id: str, req: PreparedUpdateCreateRequest):
    """Черновик производственного пакета для шота: итоговый промпт/негатив
    (resolve_shot с текущими общими правилами + локальными переопределениями),
    снимок применённых правил, референсы, выбранный исполнитель.

    Генерация НЕ запускается: запуск — штатный POST /studio/image-jobs
    (кнопка «Сгенерировать» на клиенте), затем PATCH статуса этого задания.
    Новый механизм генерации не создаётся.
    """
    from studio.art_direction import resolve_shot
    from studio.prepared_updates import (
        PREPARED_STATUS_PREPARED,
        IMAGE_EXECUTORS,
        PreparedUpdate,
    )
    from visual.VISUAL_KNOWLEDGE import knowledge_base

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")
    version = await store.get_active_version(session_id)
    if not version:
        raise HTTPException(409, "No active version")
    scenario = version.video_scenario
    if not scenario:
        raise HTTPException(409, "Session has no video scenario")
    if req.backend not in IMAGE_EXECUTORS:
        raise HTTPException(400, f"Unknown backend: {req.backend} (available: {', '.join(IMAGE_EXECUTORS)})")

    ordered = sorted(scenario.shots, key=lambda s: s.order)
    shot = next((s for s in ordered if s.shot_id == req.shot_id), None)
    if not shot:
        raise HTTPException(404, "Shot not found")

    if req.source_asset_id:
        source = await registry.get("asset_store").get(req.source_asset_id)
        if not source:
            raise HTTPException(404, "source_asset_id: asset not found")
        if source.asset_type.value != "image":
            raise HTTPException(400, "source_asset_id: not an image asset")

    ad = await _load_art_direction()
    image_plan = version.image_description
    location_name = image_plan.location.name if image_plan and image_plan.location else ""
    char_names = [c.name for c in image_plan.characters] if image_plan else []
    scene_title = scenario.title if scenario else ""
    continuity_ctx, _continuity_stale = await _applied_continuity_context(store, session.scene_id, ad)
    resolved = resolve_shot(
        ad,
        shot,
        location_name,
        char_names,
        knowledge_base.styles,
        knowledge_base.locations,
        scene_title,
        continuity_ctx or None,
    )

    prepared = PreparedUpdate(
        prepared_id=_new_id("prep"),
        session_id=session_id,
        shot_id=req.shot_id,
        source_asset_id=req.source_asset_id,
        new_prompt=resolved["resolved_prompt"],
        negative_prompt=list(resolved["resolved_negative"]),
        applied_rules=resolved["applied"],
        reference_asset_ids=await _collect_prepared_references(ad, resolved),
        backend=req.backend,
        workflow=IMAGE_EXECUTORS[req.backend]["workflow"],
        expected_result_type="image",
        status=PREPARED_STATUS_PREPARED,
    )
    await store.save_prepared_update(prepared)
    log.info(
        "studio_prepared_created session=%s prep=%s shot=%s backend=%s",
        session_id,
        prepared.prepared_id,
        req.shot_id,
        req.backend,
    )
    return SuccessResponse(
        data={
            "prepared": prepared.model_dump(),
            "executor": IMAGE_EXECUTORS[req.backend],
            "resolved": resolved,
            "continuity": {"applied": bool(continuity_ctx), "constraints": continuity_ctx},
        }
    )


@router.get(
    "/{session_id}/prepared-updates",
    dependencies=[Depends(require_role("reader"))],
    summary="Список подготовленных обновлений кадров",
)
async def list_prepared_updates_route(session_id: str, shot_id: str | None = None):
    """Все подготовленные задания сессии (+ справочник исполнителей для UI)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    items = await store.list_prepared_updates(session_id, shot_id=shot_id)
    return SuccessResponse(
        data={
            "prepared_updates": [p.model_dump() for p in items],
            "executors": IMAGE_EXECUTORS,
        }
    )


@router.patch(
    "/{session_id}/prepared-updates/{prepared_id}",
    dependencies=[Depends(require_role("editor"))],
    summary="Обновить статус подготовленного задания",
)
async def patch_prepared_update(session_id: str, prepared_id: str, req: PreparedUpdatePatchRequest):
    """Статусное продвижение после запуска существующего image-jobs:
    generating (задание запущено) → done (вариант готов, сравниваем/утверждаем)."""
    from studio.prepared_updates import PREPARED_STATUSES

    store = _get_store()
    prepared = await store.get_prepared_update(prepared_id)
    if not prepared or prepared.session_id != session_id:
        raise HTTPException(404, "Prepared update not found")
    if req.status is not None:
        if req.status not in PREPARED_STATUSES:
            raise HTTPException(400, f"Unknown status: {req.status}")
        prepared.status = req.status
    if req.new_asset_id is not None:
        prepared.new_asset_id = req.new_asset_id
        asset_store = registry.get("asset_store")
        new_asset = await asset_store.get(req.new_asset_id)
        if new_asset:
            new_asset.experiment_status = "candidate"
            await asset_store.save(new_asset)
    if req.backend is not None:
        prepared.backend = req.backend
    if req.workflow is not None:
        prepared.workflow = req.workflow
    await store.save_prepared_update(prepared)
    return SuccessResponse(data=prepared.model_dump())


@router.post(
    "/{session_id}/prepared-updates/{prepared_id}/approve",
    dependencies=[Depends(require_role("editor"))],
    summary="Утвердить новый кадр шота",
)
async def approve_prepared_update(session_id: str, prepared_id: str):
    """«Утвердить новый кадр»: новый вариант становится утверждённым кадром
    ШОТА (shots.N.approved_image_asset_id — новая версия сценария) и кадром-
    основой СЦЕНЫ (session.approved_image_asset_id для i2v).

    Старый кадр НЕ удаляется: предыдущее утверждение шота сохраняется в
    старых версиях сценария, ассеты не удаляются. Видео на старом кадре не
    пересоздаётся — связь video → input image (generation.reference_image_id)
    сохраняется, статус «требует обновления» вычисляется в /apply (stale_videos).
    """
    from studio.prepared_updates import (
        PREPARED_STATUS_APPROVED,
        PREPARED_STATUS_DONE,
    )
    from visual_assets.schemas import AssetStatus, GenerationParams

    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")
    prepared = await store.get_prepared_update(prepared_id)
    if not prepared or prepared.session_id != session_id:
        raise HTTPException(404, "Prepared update not found")
    if prepared.status not in (PREPARED_STATUS_DONE, PREPARED_STATUS_APPROVED):
        raise HTTPException(409, f"Prepared update is not ready (status={prepared.status})")
    if not prepared.new_asset_id:
        raise HTTPException(409, "Prepared update has no generated asset")

    asset_store = registry.get("asset_store")
    asset = await asset_store.get(prepared.new_asset_id)
    if not asset:
        raise HTTPException(404, "Generated asset not found")
    if asset.asset_type.value != "image":
        raise HTTPException(400, "Only image assets can be approved as a frame")
    if asset.status != AssetStatus.COMPLETED:
        raise HTTPException(409, f"Asset is not ready (status={asset.status.value})")

    version = await store.get_active_version(session_id)
    if not version or not version.video_scenario:
        raise HTTPException(409, "Session has no active video scenario")
    scenario = version.video_scenario
    ordered = sorted(scenario.shots, key=lambda s: s.order)
    shot_idx = next((i for i, s in enumerate(ordered) if s.shot_id == prepared.shot_id), None)
    if shot_idx is None:
        raise HTTPException(404, "Shot not found in active scenario")

    previous_shot_approved = ordered[shot_idx].approved_image_asset_id
    previous_scene_approved = session.approved_image_asset_id
    scenario = _apply_to_scenario(scenario, f"shots.{shot_idx}.approved_image_asset_id", prepared.new_asset_id)
    versions = await store.get_versions(session_id)
    new_version = await store.create_version(
        session_id=session_id,
        version_number=len(versions) + 1,
        image_description=version.image_description,
        video_description=version.video_description,
        video_scenario=scenario,
        parent_version_id=version.version_id,
        derivation="adaptation",
        created_by="user",
        note=f"Утверждён новый кадр шота {prepared.shot_id} ({prepared.new_asset_id})",
    )
    # Кадр-основа сцены: новый утверждённый кадр — основа для будущего i2v.
    # Старое approved-видео НЕ трогается: связь video → input image сохраняется.
    await store.set_approved_image(session_id, prepared.new_asset_id)
    prepared.status = PREPARED_STATUS_APPROVED
    await store.save_prepared_update(prepared)
    asset.experiment_status = "approved"
    await asset_store.save(asset)
    if asset.generation is None:
        asset.generation = GenerationParams()
    log.info(
        "studio_prepared_approved session=%s prep=%s shot=%s new=%s prev_shot=%s prev_scene=%s",
        session_id,
        prepared.prepared_id,
        prepared.shot_id,
        prepared.new_asset_id,
        previous_shot_approved,
        previous_scene_approved,
    )
    return SuccessResponse(
        data={
            "prepared": prepared.model_dump(),
            "shot_id": prepared.shot_id,
            "shot_index": shot_idx,
            "approved_image_asset_id": prepared.new_asset_id,
            "previous_shot_approved_image_asset_id": previous_shot_approved,
            "previous_scene_approved_image_asset_id": previous_scene_approved,
            "version_id": new_version.version_id,
            "version_number": new_version.version_number,
        }
    )


# ── История экспериментов ────────────────────────────────────────


from pydantic import BaseModel, Field


class _ExperimentBatchRequest(BaseModel):
    asset_ids: list[str] = Field(..., min_length=1, max_length=500)


class _ExperimentCleanupRequest(BaseModel):
    older_than_days: int = Field(..., ge=1, le=365)
    dry_run: bool = True


async def _is_asset_protected(asset_id: str, session_id: str) -> tuple[bool, str]:
    """Проверить, защищён ли ассет от удаления через очистку экспериментов.

    Возщает True + причину, если ассет:
    - утверждённый кадр сцены или шота;
    - референс сессии;
    - источник видео (generation.reference_image_id);
    - референс арт-дирекшна (общий/персонаж/локация).
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        return False, ""

    if session.approved_image_asset_id == asset_id:
        return True, "утверждённый кадр сцены"

    version = await store.get_active_version(session_id)
    if version and version.video_scenario:
        for shot in version.video_scenario.shots:
            if shot.approved_image_asset_id == asset_id:
                return True, f"утверждённый кадр шота {shot.shot_id}"

    refs = await store.get_references(session_id)
    if any(r.asset_id == asset_id for r in refs):
        return True, "референс сессии"

    asset_store = registry.get("asset_store")
    from visual_assets.schemas import AssetType

    videos = await asset_store.list_assets(
        chapter=session.chapter,
        scene_id=session.scene_id,
        asset_type=AssetType.VIDEO,
        limit=1000,
    )
    for v in videos:
        if v.generation and v.generation.reference_image_id == asset_id:
            return True, f"источник видео {v.asset_id}"

    ad = await _load_art_direction()
    if asset_id in (ad.reference_asset_ids or []):
        return True, "референс арт-дирекшна"
    for ch in ad.characters or []:
        if ch.approved_image_asset_id == asset_id:
            return True, "утверждённый образ персонажа"
    for loc in ad.locations or []:
        if loc.reference_asset_id == asset_id:
            return True, "референс локации"

    return False, ""


@router.get(
    "/{session_id}/experiments",
    dependencies=[Depends(require_role("reader"))],
    summary="История экспериментов сессии",
)
async def list_experiments(
    session_id: str,
    status: str | None = Query(None),
    shot_id: str | None = Query(None),
    backend: str | None = Query(None),
    older_than_days: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Список экспериментов с пагинацией, фильтрами и группировкой по шотам."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    items = await asset_store.list_experiments(
        chapter=session.chapter,
        scene_id=session.scene_id,
        status=status,
        shot_id=shot_id,
        backend=backend,
        older_than_days=older_than_days,
        limit=limit,
        offset=offset,
    )
    total = await asset_store.count_experiments(
        chapter=session.chapter,
        scene_id=session.scene_id,
        status=status,
        shot_id=shot_id,
        backend=backend,
        older_than_days=older_than_days,
    )
    groups = await asset_store.list_experiment_groups(
        chapter=session.chapter,
        scene_id=session.scene_id,
    )

    return SuccessResponse(
        data={
            "experiments": [a.model_dump(mode="json") for a in items],
            "total": total,
            "limit": limit,
            "offset": offset,
            "groups": groups,
        }
    )


@router.delete(
    "/{session_id}/experiments/{asset_id}",
    dependencies=[Depends(require_role("editor"))],
    summary="Удалить один эксперимент",
)
async def delete_experiment(session_id: str, asset_id: str):
    """Удалить эксперимент (с проверкой безопасности)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    is_protected, reason = await _is_asset_protected(asset_id, session_id)
    if is_protected:
        raise HTTPException(409, f"Защищённый ассет: {reason}")

    asset_store = registry.get("asset_store")
    if not await asset_store.delete(asset_id):
        raise HTTPException(404, "Asset not found")

    return SuccessResponse(data={"deleted": asset_id})


@router.post(
    "/{session_id}/experiments/delete-batch",
    dependencies=[Depends(require_role("editor"))],
    summary="Удалить несколько экспериментов",
)
async def delete_experiments_batch(session_id: str, req: _ExperimentBatchRequest):
    """Массовое удаление экспериментов (с проверкой безопасности)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    deleted = []
    protected = []
    for asset_id in req.asset_ids:
        is_protected, reason = await _is_asset_protected(asset_id, session_id)
        if is_protected:
            protected.append({"asset_id": asset_id, "reason": reason})
            continue
        if await asset_store.delete(asset_id):
            deleted.append(asset_id)

    return SuccessResponse(
        data={
            "deleted": deleted,
            "deleted_count": len(deleted),
            "protected": protected,
        }
    )


@router.post(
    "/{session_id}/experiments/cleanup",
    dependencies=[Depends(require_role("editor"))],
    summary="Очистить старые экспериментальные результаты",
)
async def cleanup_experiments(session_id: str, req: _ExperimentCleanupRequest):
    """Очистить эксперименты старше N дней (dry-run по умолчанию)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    experiments = await asset_store.list_experiments(
        chapter=session.chapter,
        scene_id=session.scene_id,
        status="experimental",
        older_than_days=req.older_than_days,
        limit=10000,
    )

    protected = []
    deletable = []
    for exp in experiments:
        is_protected, reason = await _is_asset_protected(exp.asset_id, session_id)
        if is_protected:
            protected.append({"asset_id": exp.asset_id, "reason": reason})
        else:
            deletable.append(exp)

    if req.dry_run:
        return SuccessResponse(
            data={
                "would_delete": len(deletable),
                "protected": protected,
                "deletable_ids": [e.asset_id for e in deletable],
            }
        )

    deleted = []
    for exp in deletable:
        await asset_store.delete(exp.asset_id)
        deleted.append(exp.asset_id)

    return SuccessResponse(
        data={
            "deleted": deleted,
            "deleted_count": len(deleted),
            "protected": protected,
        }
    )


@router.post(
    "/{session_id}/experiments/archive-batch",
    dependencies=[Depends(require_role("editor"))],
    summary="Архивировать эксперименты",
)
async def archive_experiments(session_id: str, req: _ExperimentBatchRequest):
    """Архивировать эксперименты (пометить как archived, не удалять)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    archived = []
    protected = []
    for asset_id in req.asset_ids:
        is_protected, reason = await _is_asset_protected(asset_id, session_id)
        if is_protected:
            protected.append({"asset_id": asset_id, "reason": reason})
            continue
        if await asset_store.set_experiment_status(asset_id, "archived"):
            archived.append(asset_id)

    return SuccessResponse(
        data={
            "archived": archived,
            "protected": protected,
        }
    )


@router.post(
    "/{session_id}/experiments/archive-cleanup",
    dependencies=[Depends(require_role("editor"))],
    summary="Архивировать старые эксперименты массово",
)
async def archive_cleanup_experiments(session_id: str, req: _ExperimentCleanupRequest):
    """Архивировать все experimental ассеты старше N дней (dry_run → отчёт, без dry_run → архив).

    Безопасность: protected ассеты (утверждённые, референсы, источники видео) не архивируются.
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    experiments = await asset_store.list_experiments(
        chapter=session.chapter,
        scene_id=session.scene_id,
        status="experimental",
        older_than_days=req.older_than_days,
        limit=10000,
    )

    archived = []
    protected = []
    for exp in experiments:
        is_protected, reason = await _is_asset_protected(exp.asset_id, session_id)
        if is_protected:
            protected.append({"asset_id": exp.asset_id, "reason": reason})
            continue
        if await asset_store.set_experiment_status(exp.asset_id, "archived"):
            archived.append(exp.asset_id)

    return SuccessResponse(
        data={
            "archived": archived,
            "archived_count": len(archived),
            "protected": protected,
            "dry_run": req.dry_run,
        }
    )


@router.post(
    "/{session_id}/experiments/migrate",
    dependencies=[Depends(require_role("editor"))],
    summary="Пометить все ассеты сцены как эксперименты",
)
async def migrate_experiments(session_id: str):
    """Пометить все ассеты сцены без experiment_status как experimental.

    Для старых ассетов, созданных до появления истории экспериментов.
    Утверждённые кадры и референсы помечаются соответственно.
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    asset_store = registry.get("asset_store")
    assets = await asset_store.list_assets(
        chapter=session.chapter,
        scene_id=session.scene_id,
        limit=10000,
    )

    protected_ids: set[str] = set()
    if session.approved_image_asset_id:
        protected_ids.add(session.approved_image_asset_id)
    version = await store.get_active_version(session_id)
    if version and version.video_scenario:
        for shot in version.video_scenario.shots:
            if shot.approved_image_asset_id:
                protected_ids.add(shot.approved_image_asset_id)
    refs = await store.get_references(session_id)
    for r in refs:
        protected_ids.add(r.asset_id)

    ad = await _load_art_direction()
    if ad.reference_asset_ids:
        protected_ids.update(ad.reference_asset_ids)
    for ch in ad.characters or []:
        if ch.approved_image_asset_id:
            protected_ids.add(ch.approved_image_asset_id)
    for loc in ad.locations or []:
        if loc.reference_asset_id:
            protected_ids.add(loc.reference_asset_id)

    from visual_assets.schemas import AssetType

    videos = await asset_store.list_assets(
        chapter=session.chapter,
        scene_id=session.scene_id,
        asset_type=AssetType.VIDEO,
        limit=1000,
    )
    for v in videos:
        if v.generation and v.generation.reference_image_id:
            protected_ids.add(v.generation.reference_image_id)

    experimental = 0
    approved = 0
    used = 0
    skipped = 0
    for a in assets:
        if a.experiment_status is not None:
            skipped += 1
            continue
        if a.asset_id in protected_ids:
            if a.asset_id == session.approved_image_asset_id:
                a.experiment_status = "approved"
                approved += 1
            elif any(v.generation and v.generation.reference_image_id == a.asset_id for v in videos):
                a.experiment_status = "used"
                used += 1
            else:
                a.experiment_status = "approved"
                approved += 1
            await asset_store.save(a)
        else:
            a.experiment_status = "experimental"
            await asset_store.save(a)
            experimental += 1

    return SuccessResponse(
        data={
            "experimental": experimental,
            "approved": approved,
            "used": used,
            "skipped": skipped,
            "total": len(assets),
        }
    )


# ── 0.1 Video job (Этап 2: производственный контур Studio) ────────


async def _execute_video_job(
    asset_id: str,
    prompt: str,
    preferred_backend: str,
    duration_sec: float,
    size: str,
    fps: int,
    image_asset_id: str | None = None,
) -> None:
    """Исполнение видеозадания: MediaClient → AssetStorage (фон, вне запроса).

    i2v (OWNER-GO): image_asset_id → байты кадра читаются из AssetStorage и
    передаются в arkaim-media (execution.input_image). Локальный путь НЕ
    передаётся (исполнитель внешний). Если файл кадра не читается — задание
    ПАДАЕТ (failed, input_image_read_failed), провайдер НЕ вызывается:
    молчаливый запуск без утверждённого кадра исключён.

    reference_image_id / input_image_sha256 фиксируются в generation ТОЛЬКО
    после успешного ответа исполнителя — «фактически передано», а не «выбрано».

    Управление статусом штатное: generating → completed | failed (+ error).
    Статус, ошибка и результат читаются существующим GET /book/assets/{asset_id}
    и GET /book/assets/{asset_id}/file — параллельного механизма статусов нет.
    """
    import hashlib
    from pathlib import Path

    from visual_assets.schemas import AssetStatus

    store = registry.get("asset_store")
    asset = await store.get(asset_id)
    if not asset:
        log.error("video_job_missing asset=%s", asset_id)
        return

    input_image: bytes | None = None
    frame_sha256: str | None = None
    if image_asset_id:
        # Шаг «кадр → байты»: источник только AssetStorage (безопасно для внешнего исполнителя).
        ref_asset = await store.get(image_asset_id)
        file_path = store.get_file_path(ref_asset) if ref_asset else None
        if not ref_asset or not file_path:
            asset.status = AssetStatus.FAILED
            asset.error = f"input_image_read_failed: image asset {image_asset_id} has no readable file"
            log.warning("video_job_input_image_unreadable asset=%s ref=%s", asset_id, image_asset_id)
            await store.save(asset)
            return
        try:
            input_image = Path(file_path).read_bytes()
        except OSError as exc:
            asset.status = AssetStatus.FAILED
            asset.error = f"input_image_read_failed: {str(exc)[:200]}"
            log.warning("video_job_input_image_unreadable asset=%s ref=%s err=%s", asset_id, image_asset_id, exc)
            await store.save(asset)
            return
        frame_sha256 = hashlib.sha256(input_image).hexdigest()

    try:
        result = await registry.get("media_client").generate_video_with_meta(
            prompt,
            duration=duration_sec,
            size=size,
            fps=fps,
            preferred_backend=preferred_backend,
            input_image=input_image,
            input_image_filename=f"scene_frame_{image_asset_id}.png" if image_asset_id else "arkaim_input.png",
        )
        asset.file_path = store.save_file(asset.asset_id, asset.asset_type, result.data)
        asset.status = AssetStatus.COMPLETED
        asset.error = None
        asset.generation.backend = result.backend or None
        asset.generation.media_id = result.media_id or None
        asset.generation.workflow_used = result.workflow_used
        if input_image is not None and image_asset_id:
            # Связь результата с исходным кадром: id + хеш реально переданных байтов.
            asset.generation.reference_image_id = image_asset_id
            asset.generation.input_image_sha256 = frame_sha256
            # Исходный кадр использован в производстве — помечаем как used.
            ref_asset = await store.get(image_asset_id)
            if ref_asset:
                ref_asset.experiment_status = "used"
                await store.save(ref_asset)
        log.info(
            "video_job_completed asset=%s backend=%s workflow=%s ref_image=%s",
            asset_id,
            result.backend,
            result.workflow_used,
            image_asset_id,
        )
    except Exception as exc:  # любая ошибка задания → статус failed (не глушим)
        asset.status = AssetStatus.FAILED
        asset.error = str(exc)[:500] or exc.__class__.__name__
        log.warning("video_job_failed asset=%s err=%s", asset_id, exc)
    await store.save(asset)


async def _execute_image_job(
    asset_id: str,
    prompt: str,
    preferred_backend: str,
    size: str,
) -> None:
    """Исполнение изображение-задания: MediaClient → AssetStorage (фон).

    Образец _execute_video_job. Реальная интеграция изображений —
    arkaim-media (preferred_backend="agnes" — ComfyUI-Agnes; "mock" —
    тестовые ответы). Статус читается существующим GET /book/assets/{id}.
    """
    from visual_assets.schemas import AssetStatus

    store = registry.get("asset_store")
    asset = await store.get(asset_id)
    if not asset:
        log.error("image_job_missing asset=%s", asset_id)
        return
    try:
        result = await registry.get("media_client").generate_image_with_meta(
            prompt,
            size=size,
            preferred_backend=preferred_backend,
        )
        asset.file_path = store.save_file(asset.asset_id, asset.asset_type, result.data)
        asset.status = AssetStatus.COMPLETED
        asset.error = None
        asset.generation.backend = result.backend or None
        asset.generation.media_id = result.media_id or None
        asset.generation.workflow_used = result.workflow_used
        log.info("image_job_completed asset=%s backend=%s workflow=%s", asset_id, result.backend, result.workflow_used)
    except Exception as exc:  # любая ошибка задания → статус failed (не глушим)
        asset.status = AssetStatus.FAILED
        asset.error = str(exc)[:500] or exc.__class__.__name__
        log.warning("image_job_failed asset=%s err=%s", asset_id, exc)
    await store.save(asset)


@router.post(
    "/video-jobs",
    dependencies=[Depends(require_role("editor"))],
    summary="Запустить видеозадание по производственному плану",
)
async def create_video_job(req: VideoJobRequest, background_tasks: BackgroundTasks):
    """Производственный контур видео: план → выбор исполнителя → запуск.

    Вход — video_description из /book/studio-describe (prompt + plan_id) и
    выбор исполнителя (preferred_backend: auto | mock | comfyicu | ...).
    Создаёт ассет со статусом generating и запускает исполнение фоном:
    ответ возвращается сразу с asset_id, состояние задания читается через
    существующий GET /book/assets/{asset_id} (status/error), готовый файл —
    через GET /book/assets/{asset_id}/file. Связь сцен/плана/workflow
    сохраняется в ассете (scene_id, generation.plan_id/workflow_used/media_id).

    Arkaim по-прежнему НЕ исполняет генерацию локально — исполнение уходит
    в arkaim-media через существующий MediaClient (Media Boundary не нарушен).

    i2v (OWNER-GO): image_asset_id → в фоне байты кадра читаются из
    AssetStorage и передаются в execution.input_image arkaim-media (внешнему
    исполнителю локальный путь недоступен); без image_asset_id — прежний t2v.
    """
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    scene_engine = registry.get("scene_engine")
    if not scene_engine.get_scene(req.chapter, req.scene_id):
        raise HTTPException(404, "Scene not found")

    if req.image_asset_id:
        ref_asset = await registry.get("asset_store").get(req.image_asset_id)
        if not ref_asset or ref_asset.asset_type.value != "image":
            raise HTTPException(400, "image_asset_id: not an image asset")
        # i2v: файл кадра должен читаться ДО запуска — иначе задание упало бы
        # в фоне; отказ 409 заметен клиенту сразу (без тихого запуска без кадра).
        if not registry.get("asset_store").get_file_path(ref_asset):
            raise HTTPException(409, "image asset has no readable file")

    store = registry.get("asset_store")
    ad = await _load_art_direction()
    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=req.chapter,
        scene_id=req.scene_id,
        title=req.title or req.plan_id or f"видео {req.scene_id}",
        status=AssetStatus.GENERATING,
        duration_sec=req.duration_sec,
        fps=req.fps,
        prompt_used=req.prompt,
        experiment_status="experimental",
        generation=GenerationParams(
            provider=req.preferred_backend,
            model=req.model,
            size=req.size,
            art_direction_revision=ad.revision,
        ),
    )
    asset.generation.plan_id = req.plan_id
    # shot_id — привязка клипа к плану сценария (лента фильма). Необязательна:
    # старые клипы без неё сопоставляются по reference_image_id (см. studio/reel.py).
    asset.generation.shot_id = req.shot_id or None
    # reference_image_id НЕ ставим «по факту выбора»: в generation он попадает
    # в _execute_video_job ТОЛЬКО когда кадр реально передан исполнителю.
    await store.save(asset)

    background_tasks.add_task(
        _execute_video_job,
        asset.asset_id,
        req.prompt,
        req.preferred_backend,
        req.duration_sec,
        req.size,
        req.fps,
        req.image_asset_id,
    )
    return SuccessResponse(
        data={
            "asset_id": asset.asset_id,
            "status": asset.status.value,
            "scene_id": asset.scene_id,
            "plan_id": req.plan_id,
        }
    )


# ── 0.2 Image job (производственная модель Studio: промпт → изображение) ──


@router.post(
    "/image-jobs",
    dependencies=[Depends(require_role("editor"))],
    summary="Запустить изображение-задание по промпту сцены",
)
async def create_image_job(req: ImageJobRequest, background_tasks: BackgroundTasks):
    """Шаг «создать изображение»: промпт из image_description → вариант кадра.

    prompt/plan_id приходят из image_description активной версии Studio-сессии;
    preferred_backend — реальный исполнитель (agnes через arkaim-media) или
    mock для тестов. Несколько запусков с одним plan_id = варианты одного
    промпта (сравнение и утверждение — на клиенте по generation.plan_id).

    Ответ сразу с asset_id; статус — существующий GET /book/assets/{asset_id},
    файл — GET /book/assets/{asset_id}/file. Параллельного механизма статусов нет.
    """
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    scene_engine = registry.get("scene_engine")
    if not scene_engine.get_scene(req.chapter, req.scene_id):
        raise HTTPException(404, "Scene not found")

    store = registry.get("asset_store")
    ad = await _load_art_direction()
    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.IMAGE,
        chapter=req.chapter,
        scene_id=req.scene_id,
        title=req.title or req.plan_id or f"кадр {req.scene_id}",
        status=AssetStatus.GENERATING,
        prompt_used=req.prompt,
        experiment_status="experimental",
        generation=GenerationParams(
            provider=req.preferred_backend,
            size=req.size,
            art_direction_revision=ad.revision,
        ),
    )
    asset.generation.plan_id = req.plan_id
    asset.generation.shot_id = req.shot_id  # привязка кадра к плану сценария
    await store.save(asset)

    background_tasks.add_task(
        _execute_image_job,
        asset.asset_id,
        req.prompt,
        req.preferred_backend,
        req.size,
    )
    return SuccessResponse(
        data={
            "asset_id": asset.asset_id,
            "status": asset.status.value,
            "scene_id": asset.scene_id,
            "plan_id": req.plan_id,
        }
    )


# ── 0.3 Approve image (производственная модель: утверждение кадра) ──────


@router.post("/{session_id}/approve-image", summary="Утвердить изображение кадром сцены")
async def approve_image(
    session_id: str,
    asset_id: str,
    user: dict = Depends(require_role("editor")),
):
    """Шаг «утвердить изображение»: asset_id → session.approved_image_asset_id.

    Кадр-основа для запуска видео. Требования к ассету: IMAGE, status=completed
    (утверждать можно только готовое изображение). asset_id пустой ("" или
    «null» на клиенте) — снятие утверждения.
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    if not asset_id or asset_id in ("", "null", "none"):
        await store.set_approved_image(session_id, None)
        return SuccessResponse(data={"session_id": session_id, "approved_image_asset_id": None})

    asset = await registry.get("asset_store").get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.asset_type.value != "image":
        raise HTTPException(400, "Only image assets can be approved as a frame")
    if asset.status.value != "completed":
        raise HTTPException(409, f"Asset is not ready (status={asset.status.value})")

    await store.set_approved_image(session_id, asset_id)
    log.info("studio_image_approved session=%s asset=%s", session_id, asset_id)
    return SuccessResponse(data={"session_id": session_id, "approved_image_asset_id": asset_id})


# ── 1. Create session ────────────────────────────────────────────


@router.post("/create", summary="Создать Studio-сессию из сцены")
async def create_session(
    chapter: int,
    scene_id: str,
    user: dict = Depends(require_role("editor")),
):
    """Создать Studio-сессию. Получает три описания от Arkaim Description System.

    Вызывает /visual/studio-describe pipeline для получения:
    - Image Description (MediaPlan, media_kind="image")
    - Video Description (MediaPlan, media_kind="video")
    - Full Video Scenario (VideoScenario)

    Studio НЕ генерирует эти описания — они приходят из существующей системы.
    """
    from studio.store import StudioStore

    store = StudioStore()
    scene_engine = registry.get("scene_engine")
    scene = scene_engine.get_scene(chapter, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    title = scene.get("title", f"Scene {scene_id}")

    session = await store.create_session(
        user_id=user.get("user_id", ""),
        title=title,
        chapter=chapter,
        scene_id=scene_id,
    )

    # Build initial descriptions from Arkaim Description System
    from media_plan import MediaPlanBuilder
    from studio.scenario_builder import VideoScenarioBuilder
    from visual.video_intelligence import VideoIntelligence

    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context(chapter, scene_id)

    # A. Image Description — existing pipeline
    image_plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx,
        intent="key_frame",
        created_from="scene_context",
    )

    # B. Video Description — existing VideoIntelligence
    vi = VideoIntelligence()
    video_ctx = vi.create_video_context(ctx)
    video_plan = MediaPlanBuilder(generator="comfyui").build_video_plan(
        video_ctx,
        intent="video_clip",
        duration_sec=video_ctx.duration_sec,
        fps=video_ctx.fps,
    )

    # C. Full Video Scenario — VideoScenarioBuilder
    scenario_builder = VideoScenarioBuilder(video_intelligence=vi)
    scenario = scenario_builder.build(ctx, duration_sec=30.0)

    # Create initial version
    version = await store.create_version(
        session_id=session.session_id,
        version_number=1,
        image_description=image_plan,
        video_description=video_plan,
        video_scenario=scenario,
        created_by="system",
        note="Initial description from Arkaim Description System",
    )

    # System message
    await store.add_message(
        session_id=session.session_id,
        role="system",
        content=f"Studio session created for scene '{title}'. Three descriptions prepared.",
        created_version_id=version.version_id,
    )

    return SuccessResponse(
        data={
            "session": session.model_dump(mode="json"),
            "version": version.model_dump(mode="json"),
        }
    )


# ── 2. List sessions ────────────────────────────────────────────


@router.get("/list", summary="Список Studio-сессий пользователя")
async def list_sessions(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_role("reader")),
):
    store = _get_store()
    sessions = await store.list_sessions(
        user_id=user.get("user_id", ""),
        status=status,
        limit=limit,
        offset=offset,
    )
    return SuccessResponse(data=[s.model_dump(mode="json") for s in sessions])


# ── 3. Get session ──────────────────────────────────────────────


@router.get("/{session_id}", summary="Получить Studio-сессию с версиями и сообщениями")
async def get_session(
    session_id: str,
    user: dict = Depends(require_role("reader")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    versions = await store.get_versions(session_id)
    messages = await store.get_messages(session_id)
    references = await store.get_references(session_id)

    return SuccessResponse(
        data={
            "session": session.model_dump(mode="json"),
            "versions": [v.model_dump(mode="json") for v in versions],
            "messages": [m.model_dump(mode="json") for m in messages],
            "references": [r.model_dump(mode="json") for r in references],
        }
    )


# ── 3b. Delete session ───────────────────────────────────────────


@router.delete("/{session_id}", summary="Удалить Studio-сессию")
async def delete_session(
    session_id: str,
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    deleted = await store.delete_session(session_id)
    if not deleted:
        raise HTTPException(500, "Failed to delete session")
    return SuccessResponse(data={"deleted": session_id})


# ── 4. Discussion ───────────────────────────────────────────────


@router.post("/{session_id}/discuss", summary="Отправить сообщение в discussion")
async def discuss(
    session_id: str,
    message: str,
    user: dict = Depends(require_role("editor")),
):
    """Discussion с Arkaim. LLM отвечает текстом — НЕ меняет описания.

    Контракт:
      - LLM получает контекст трёх описаний + историю discussion
      - LLM возвращает текстовый ответ (proposal / explanation / question)
      - LLM НЕ создаёт новую StudioVersion
      - LLM НЕ изменяет существующие описания
      - LLM НЕ модифицирует World Model / SceneContext

    Чтобы применить изменение — пользователь вызывает /modify (explicit confirmation).
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    # Save user message
    user_msg = await store.add_message(session_id, "user", message)

    # Get current version for LLM context
    active_version = await store.get_active_version(session_id)
    if not active_version:
        raise HTTPException(409, "No active version")

    # LLM discussion: applies user correction to existing descriptions
    # Context: current three descriptions + last 10 messages
    messages = await store.get_messages(session_id, limit=10)

    from core.adc_deps import registry as _reg

    voice = _reg.get("voice")

    # Build LLM context from existing descriptions
    context_parts = []
    if active_version.image_description:
        context_parts.append(f"Image prompt: {active_version.image_description.prompt}")
    if active_version.video_description:
        context_parts.append(f"Video prompt: {active_version.video_description.prompt}")
    if active_version.video_scenario:
        context_parts.append(f"Scenario synopsis: {active_version.video_scenario.synopsis}")

    history = [{"role": m.role.value, "content": m.content} for m in messages]

    utterance = await voice.speak(
        query=message,
        reader_id=user.get("user_id", ""),
        reader_name=user.get("display_name", "") or user.get("username", ""),
        messages=history,
    )

    answer = utterance.text if hasattr(utterance, "text") else str(utterance)

    # Save assistant message
    assistant_msg = await store.add_message(session_id, "assistant", answer)

    # Update status
    await store.update_session_status(session_id, "discussing")

    return SuccessResponse(
        data={
            "user_message": user_msg.model_dump(mode="json"),
            "assistant_message": assistant_msg.model_dump(mode="json"),
        }
    )


# ── 5. Manual modify ────────────────────────────────────────────


@router.post("/{session_id}/modify", summary="Ручное изменение описания")
async def modify(
    session_id: str,
    target: str,  # "image_description" | "video_description" | "video_scenario"
    field_path: str,  # "atmosphere", "camera.shot_type", etc.
    new_value: str,
    note: str = "",
    user: dict = Depends(require_role("editor")),
):
    """Ручное редактирование поля описания. Создаёт новую версию (immutable)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    active = await store.get_active_version(session_id)
    if not active:
        raise HTTPException(409, "No active version")

    # Apply modification to the target description
    modification = UserModification(
        target=target,
        field_path=field_path,
        old_value="",
        new_value=new_value,
        reason=note or "Manual edit by user",
        timestamp=_now(),
    )

    # Copy current descriptions and apply change
    img = active.image_description
    vid = active.video_description
    scenario = active.video_scenario

    # Apply to image description
    if target == "image_description" and img:
        old_val = _get_nested_field(img, field_path)
        modification.old_value = str(old_val) if old_val else ""
        img = _apply_to_mediaplan(img, field_path, new_value)

    # Apply to video description
    elif target == "video_description" and vid:
        old_val = _get_nested_field(vid, field_path)
        modification.old_value = str(old_val) if old_val else ""
        vid = _apply_to_mediaplan(vid, field_path, new_value)

    # Apply to video scenario
    elif target == "video_scenario" and scenario:
        old_val = _get_nested_field(scenario, field_path)
        modification.old_value = str(old_val) if old_val else ""
        scenario = _apply_to_scenario(scenario, field_path, new_value)

    versions = await store.get_versions(session_id)
    new_version = await store.create_version(
        session_id=session_id,
        version_number=len(versions) + 1,
        image_description=img,
        video_description=vid,
        video_scenario=scenario,
        parent_version_id=active.version_id,
        derivation="adaptation",
        user_modifications=[modification],
        created_by="user",
        note=note or f"Manual edit: {field_path}",
    )

    # System message
    await store.add_message(
        session_id,
        "system",
        f"Manual edit applied: {target}.{field_path} = {new_value[:100]}",
        created_version_id=new_version.version_id,
    )

    return SuccessResponse(data=new_version.model_dump(mode="json"))


# ── 6. Create variant ───────────────────────────────────────────


@router.post("/{session_id}/variant", summary="Создать варианты (до 5)")
async def create_variants(
    session_id: str,
    count: int = 2,
    notes: str = "",
    user: dict = Depends(require_role("editor")),
):
    """Создать варианты текущего описания. Каждый вариант — независимая версия."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    count = min(max(count, 1), 5)  # O6: max 5

    active = await store.get_active_version(session_id)
    if not active:
        raise HTTPException(409, "No active version")

    versions = await store.get_versions(session_id)
    variants = []

    for i in range(count):
        v = await store.create_version(
            session_id=session_id,
            version_number=len(versions) + i + 1,
            image_description=active.image_description,
            video_description=active.video_description,
            video_scenario=active.video_scenario,
            parent_version_id=active.version_id,
            derivation="variation",
            created_by="user",
            note=notes or f"Variant {i + 1}",
        )
        variants.append(v)

    await store.add_message(
        session_id,
        "system",
        f"Created {count} variant(s) from version {active.version_number}",
    )

    return SuccessResponse(data=[v.model_dump(mode="json") for v in variants])


# ── 7. Activate version ─────────────────────────────────────────


@router.post("/{session_id}/activate-version", summary="Активировать версию")
async def activate_version(
    session_id: str,
    version_id: str,
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    version = await store.get_version(version_id)
    if not version or version.session_id != session_id:
        raise HTTPException(404, "Version not found")

    conn = await store._get_conn()
    await conn.execute("UPDATE studio_versions SET is_active = 0 WHERE session_id = ?", (session_id,))
    await conn.execute("UPDATE studio_versions SET is_active = 1 WHERE version_id = ?", (version_id,))
    now = _now()
    await conn.execute("UPDATE studio_sessions SET active_version_id = ?, updated_at = ? WHERE session_id = ?", (version_id, now, session_id))
    await conn.commit()

    return SuccessResponse(data={"activated": version_id})


# ── 8. Upload reference ─────────────────────────────────────────


@router.post("/{session_id}/upload-reference", summary="Загрузить reference-изображение")
async def upload_reference(
    session_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    user: dict = Depends(require_role("editor")),
):
    """Загрузить reference-изображение. Сохраняется в AssetStorage с source_type="user_reference"."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Файл + метаданные в существующем AssetStorage: без записи VisualAsset
    # GET /book/assets/{id}/file отвечает 404 (референс неоткрываем).
    from visual_assets.schemas import AssetStatus, AssetType, VisualAsset

    asset_storage = registry.get("asset_store")

    asset_id = f"ref_{uuid.uuid4().hex[:12]}"
    file_data = await file.read()
    if not file_data:
        raise HTTPException(400, "Empty file")
    rel_path = asset_storage.save_file(asset_id, AssetType.IMAGE, file_data)
    await asset_storage.save(
        VisualAsset(
            asset_id=asset_id,
            asset_type=AssetType.IMAGE,
            chapter=session.chapter,
            scene_id=session.scene_id,
            title=f"reference: {description or file.filename or asset_id}"[:200],
            status=AssetStatus.COMPLETED,
            file_path=rel_path,
        )
    )

    # Create reference record
    reference = await store.add_reference(session_id, asset_id, description)

    await store.add_message(
        session_id,
        "system",
        f"Reference image uploaded: {description or 'no description'}",
    )

    return SuccessResponse(data=reference.model_dump(mode="json"))


# ── 9. Approve ──────────────────────────────────────────────────


@router.post("/{session_id}/approve", summary="Финализировать (утвердить)")
async def approve(
    session_id: str,
    version_id: str | None = None,
    user: dict = Depends(require_role("editor")),
):
    """Финализировать сессию. Помечает активную (или указанную) версию как final."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "sent"):
        raise HTTPException(409, "Already finalized")

    target_id = version_id or session.active_version_id
    if not target_id:
        raise HTTPException(409, "No version to finalize")

    version = await store.get_version(target_id)
    if not version or version.session_id != session_id:
        raise HTTPException(404, "Version not found")

    await store.finalize_version(target_id)
    await store.update_session_status(session_id, "approved")

    await store.add_message(
        session_id,
        "system",
        f"Version {version.version_number} finalized as approved",
    )

    return SuccessResponse(
        data={
            "status": "approved",
            "version_id": target_id,
        }
    )


# ── 10. Reject ──────────────────────────────────────────────────


@router.post("/{session_id}/reject", summary="Отклонить")
async def reject(
    session_id: str,
    reason: str = "",
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    await store.update_session_status(session_id, "rejected")
    await store.add_message(session_id, "system", f"Session rejected: {reason}")

    return SuccessResponse(data={"status": "rejected", "reason": reason})


# ── 11. Export ───────────────────────────────────────────────────


@router.get("/{session_id}/export", summary="Экспорт финального StudioExport")
async def export_session(
    session_id: str,
    user: dict = Depends(require_role("editor")),
):
    """Экспорт финального результата: три описания + references + lineage.

    MediaPlan v0 не расширяется. References — внешние asset references.
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != "approved":
        raise HTTPException(409, "Session not approved")

    # Find final version
    versions = await store.get_versions(session_id)
    final_version = None
    for v in versions:
        if v.is_final:
            final_version = v
            break
    if not final_version:
        raise HTTPException(409, "No finalized version")

    # Build lineage
    lineage = []
    current = final_version
    while current:
        lineage.insert(0, current.version_id)
        if current.parent_version_id:
            current = await store.get_version(current.parent_version_id)
        else:
            break

    # Build references
    references = []
    for ref in await store.get_references(session_id):
        references.append(
            {
                "asset_id": ref.asset_id,
                "description": ref.description,
                "file_url": f"/book/assets/{ref.asset_id}/file",
            }
        )

    export = {
        "session_id": session_id,
        "export_id": _new_id("export"),
        "image_description": final_version.image_description.model_dump(mode="json") if final_version.image_description else None,
        "video_description": final_version.video_description.model_dump(mode="json") if final_version.video_description else None,
        "video_scenario": final_version.video_scenario.to_dict() if final_version.video_scenario else None,
        "references": references,
        "version_lineage": lineage,
        "exported_at": _now(),
    }

    return export  # direct return (not enveloped) for export


# ── Helpers ──────────────────────────────────────────────────────


def _get_nested_field(obj, field_path: str):
    """Get nested field from object by dot-notation path."""
    parts = field_path.split(".")
    current = obj
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def _resolve_container(data, parts: list[str]):
    """Спуск по dot-путю в model_dump(): dict-ключи и числовые индексы списков.

    Поддержка списков нужна для пошотовых правок («shots.0.description»):
    без неё путь молча не применялся. None — путь невалиден.
    """
    current = data
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                return None
            current = current[int(part)]
        else:
            return None
    return current


def _coerce_to_existing(current, new_value: str):
    """Привести строку к типу существующего значения при правке.

    Списковые поля шотов (palette_override) приходят строкой из query —
    без коэрции model_validate отвергал бы правку (тихий no-op).
    Пустая строка → очистка; JSON-массив → разбор; иначе → split по запятой.
    """
    if not isinstance(current, list) or not isinstance(new_value, str):
        return new_value
    s = new_value.strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return parsed
        except ValueError:
            log.warning("modify_list_json_failed path=%s value=%s", s[:40], new_value[:80])
    return [part.strip() for part in s.split(",") if part.strip()]


def _apply_path_value(data, field_path: str, new_value: str) -> bool:
    """Применить new_value по dotted-пути к dict из model_dump(). False — путь не найден."""
    parts = field_path.split(".")
    parent = _resolve_container(data, parts[:-1])
    if parent is None:
        return False
    last = parts[-1]
    if isinstance(parent, dict) and last in parent:
        parent[last] = _coerce_to_existing(parent[last], new_value)
        return True
    if isinstance(parent, list) and last.isdigit() and int(last) < len(parent):
        parent[int(last)] = _coerce_to_existing(parent[int(last)], new_value)
        return True
    return False


def _apply_to_mediaplan(plan, field_path: str, new_value: str):
    """Apply modification to MediaPlan. Returns new MediaPlan (immutable)."""

    data = plan.model_dump()
    if not _apply_path_value(data, field_path, new_value):
        return plan
    try:
        return plan.__class__.model_validate(data)
    except Exception:
        return plan


def _apply_to_scenario(scenario, field_path: str, new_value: str):
    """Apply modification to VideoScenario. Returns new VideoScenario (immutable)."""

    data = scenario.model_dump()
    if not _apply_path_value(data, field_path, new_value):
        return scenario
    try:
        return scenario.__class__.model_validate(data)
    except Exception:
        return scenario
