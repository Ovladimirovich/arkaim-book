"""Book Intelligence вЂ” РѕСЃРЅРѕРІРЅС‹Рµ СЌРЅРґРїРѕРёРЅС‚С‹ (/book/*)."""
import json
import logging
import re
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query

from auth.rbac import require_role
from core.dto.requests import BookAskRequest, BookGenerateRequest
from core.dto.responses import (
    HealthResponse, BookAskResponse, BookGenomeResponse,
    BookLayersResponse, SuccessResponse,
)
from core.cache import genome_cache, chunks_cache
from core.adc_deps import (
    get_config, get_pulse, get_keeper, get_herald,
    get_event_logger, get_drafts,
)

log = logging.getLogger("hermes.routes.book")


@lru_cache(maxsize=1)
def _get_expansion_loader():
    """Cached ExpansionLoader - loads once."""
    try:
        from knowledge_expansion.expansion_loader import ExpansionLoader
        loader = ExpansionLoader()
        loader.load()
        return loader
    except Exception as e:
        log.warning("expansion_loader_init_failed: %s", e)
        return None


@lru_cache(maxsize=1)
def _get_genome_data():
    """Cached genome data - loads once."""
    try:
        from genome.extractor import load_json, GENOME_DIR
        return load_json(GENOME_DIR / "GENOME_v1.0.0.json")
    except Exception as e:
        log.warning("genome_load_failed: %s", e)
        return {}

router = APIRouter(tags=["Book Intelligence"])


@lru_cache(maxsize=1)
def _load_genome_raw() -> bytes | None:
    """Р§РёС‚Р°РµРј genome JSON РѕРґРёРЅ СЂР°Р·, РєСЌС€РёСЂСѓРµРј СЃС‹СЂРѕР№ Р±Р°Р№С‚."""
    config = get_config()
    path = config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
    if path.exists():
        return path.read_bytes()
    return None


def _load_genome(config_obj=None) -> dict | None:
    data = _load_genome_raw()
    if data is None:
        return None
    return json.loads(data)


def _load_genome_full(config_obj=None) -> dict:
    return _load_genome(config_obj) or {}


def _save_genome(genome: dict, config_obj):
    path = config_obj.GENOME_DIR / f"GENOME_v{config_obj.GENOME_VERSION}.json"
    path.write_text(json.dumps(genome, ensure_ascii=False, indent=2), encoding="utf-8")


# Shared with /v1/stream so JSON and SSE answers expose the same World links.
from core.services.related_entities import resolve_related_entities as _resolve_related_entities


@router.get("/health", response_model=HealthResponse)
async def health(config=Depends(get_config)):
    return HealthResponse(status="ok", version=config.APP_VERSION)


@router.get("/", dependencies=[Depends(require_role("reader"))])
async def root(config=Depends(get_config)):
    return {
        "name": "Book Intelligence",
        "version": config.APP_VERSION,
        "endpoints": {
            "health": "GET /book/health",
            "genome": "GET /book/genome",
            "layers": "GET /book/layers",
            "ask": "POST /book/ask",
            "generate": "POST /book/generate",
            "drafts": "GET /book/drafts",
            "draft_approve": "POST /book/drafts/{draft_id}/approve",
            "memory_stats": "GET /book/memory/stats",
        },
    }


@router.get("/genome", response_model=BookGenomeResponse, dependencies=[Depends(require_role("reader"))])
async def get_genome(config=Depends(get_config)):
    genome = _load_genome(config)
    if genome is None:
        raise HTTPException(404, "Р“РµРЅРѕРј РЅРµ РЅР°Р№РґРµРЅ")
    return BookGenomeResponse(
        themes=genome["modules"].get("themes", []),
        characters=genome["modules"].get("characters", []),
        values=genome["modules"].get("values", []),
        world_entities=genome.get("world_entities", []),
        author_intent=genome.get("author_intent", {}),
        modules=genome.get("modules", {}),
    )


@router.get("/layers", response_model=BookLayersResponse, dependencies=[Depends(require_role("reader"))])
async def get_layers_endpoint(pulse=Depends(get_pulse)):
    if not pulse or not pulse.is_loaded:
        raise HTTPException(503, "Pulse РЅРµ Р·Р°РіСЂСѓР¶РµРЅ")
    k = pulse.layers.get("knowledge")
    m = pulse.layers.get("meaning")
    i = pulse.layers.get("identity")
    ms = pulse.layers.get("mission")
    w = pulse.layers.get("world_engine")
    return BookLayersResponse(
        knowledge_layer=k.summary if k else "",
        meaning_layer=m.summary if m else "",
        identity_layer=i.summary if i else "",
        mission_layer=ms.summary if ms else "",
        world_engine_layer=w.summary if w else "",
    )


@router.post("/ask", response_model=SuccessResponse, summary="Р—Р°РґР°С‚СЊ РІРѕРїСЂРѕСЃ РєРЅРёРіРµ")
async def ask(
    req: BookAskRequest,
    user: dict = Depends(require_role("reader")),
    keeper=Depends(get_keeper),
    event_logger=Depends(get_event_logger),
):
    from core.presence_manager import register_question
    result = await keeper.act({
        "question": req.question,
        "context": req.context,
        "messages": [{"role": m.role, "content": m.content} for m in (req.messages or [])],
        "reader_id": user.get("user_id", ""),
        "reader_name": user.get("display_name", "") or user.get("username", ""),
    })
    result["related_entities"] = _resolve_related_entities(result)
    event_logger.log_event({
        "event_type": "api_ask", "topic": req.question[:100],
        "user_sentiment": "neutral", "system_action": "keeper_response", "outcome": "ok",
    })
    register_question(req.question[:60], req.question, result.get("answer", ""))

    # Persist one immutable turn. A missing session id starts a new logical
    # conversation; client-supplied ids are never used to bypass user ownership.
    session_id = req.session_id or uuid.uuid4().hex
    from memory.store import get_memory_store
    answer = str(result.get("answer", ""))
    metadata = {key: value for key, value in result.items() if key != "answer"}
    try:
        await get_memory_store().store_exchange(
            session_id=session_id,
            user_id=user["user_id"],
            question=req.question,
            answer=answer,
            metadata=metadata,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Диалог принадлежит другому читателю") from exc
    persisted_result = {**result, "answer": answer, "session_id": session_id}

    # WebSocket СѓРІРµРґРѕРјР»РµРЅРёРµ
    from core.websocket import notify_new_question
    await notify_new_question(req.question, req.question[:60], user.get("user_id", ""))

    return SuccessResponse(data=persisted_result)


@router.post("/generate", response_model=SuccessResponse, summary="Р“РµРЅРµСЂР°С†РёСЏ РєРѕРЅС‚РµРЅС‚Р°", dependencies=[Depends(require_role("editor"))])
async def generate(
    req: BookGenerateRequest,
    herald=Depends(get_herald),
    drafts=Depends(get_drafts),
):
    draft = await herald.act({"content_type": req.type, "topic": req.topic})
    from community.telegram import Draft as DraftModel
    d = DraftModel(id=draft["id"], content=draft["draft"], target="", source="herald", status="pending")
    drafts.save_draft(d)
    return SuccessResponse(data=draft)


@router.get("/drafts", response_model=SuccessResponse, summary="РџРѕР»СѓС‡РёС‚СЊ С‡РµСЂРЅРѕРІРёРєРё", dependencies=[Depends(require_role("reader"))])
async def get_drafts_endpoint(status: str | None = None, drafts=Depends(get_drafts)):
    if status == "pending":
        return SuccessResponse(data=drafts.get_pending_drafts())
    return SuccessResponse(data=drafts.get_all_drafts())


@router.post("/drafts/{draft_id}/approve", response_model=SuccessResponse, summary="РћРґРѕР±СЂРёС‚СЊ С‡РµСЂРЅРѕРІРёРє", dependencies=[Depends(require_role("editor"))])
async def approve_draft(draft_id: str, drafts=Depends(get_drafts)):
    if drafts.approve_draft(draft_id):
        return SuccessResponse(data={"status": "approved", "draft_id": draft_id})
    raise HTTPException(404, "Р§РµСЂРЅРѕРІРёРє РЅРµ РЅР°Р№РґРµРЅ")


@router.get("/memory/stats", response_model=SuccessResponse, summary="РЎС‚Р°С‚РёСЃС‚РёРєР° РїР°РјСЏС‚Рё", dependencies=[Depends(require_role("admin"))])
async def get_memory_stats(event_logger=Depends(get_event_logger)):
    if hasattr(event_logger, "get_statistics"):
        return SuccessResponse(data=event_logger.get_statistics())
    return SuccessResponse(data={"total_events": 0, "status": "ok"})


# в”Ђв”Ђ Chapters: С‡С‚РµРЅРёРµ С‚РµРєСЃС‚Р° РєРЅРёРіРё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


@lru_cache(maxsize=1)
def _load_enriched_chunks(config_obj=None) -> list[dict]:
    """Р—Р°РіСЂСѓР·РёС‚СЊ enriched_chunks.json (СЂР°Р·Р±РёС‚С‹Рµ РЅР° РіР»Р°РІС‹ С‡Р°РЅРєРё)."""
    if config_obj is None:
        config_obj = get_config()
    path = config_obj.KNOWLEDGE_DIR / "enriched_chunks.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    # enriched_chunks.json may be a dict with "chunks" key or a plain list
    if isinstance(data, dict):
        return data.get("chunks", [])
    return data


def _build_chapters_from_chunks(chunks: list[dict]) -> list[dict]:
    """РЎРіСЂСѓРїРїРёСЂРѕРІР°С‚СЊ С‡Р°РЅРєРё РїРѕ chapter_title РІ РіР»Р°РІС‹."""
    if not chunks:
        return []

    from collections import OrderedDict
    chapter_map: dict[str, list[dict]] = OrderedDict()

    for ch in chunks:
        title = ch.get("chapter_title", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
        if title not in chapter_map:
            chapter_map[title] = []
        chapter_map[title].append(ch)

    chapters = []
    for i, (title, parts) in enumerate(chapter_map.items()):
        # If there's a large chunk (full chapter text), use only it to avoid duplication
        large_parts = [p for p in parts if len(p.get("text", "")) > 1000]
        if large_parts:
            content = large_parts[0].get("text", "")
        else:
            content = "\n\n".join(p.get("text", "") for p in parts)
        chapters.append({
            "id": f"ch_{i:02d}",
            "title": title,
            "content": content,
            "char_count": len(content),
            "index": i,
        })

    return chapters


@lru_cache(maxsize=1)
def _load_chapters(config_obj=None) -> list[dict]:
    chunks = _load_enriched_chunks(config_obj)
    return _build_chapters_from_chunks(chunks)


@router.get("/chapters", dependencies=[Depends(require_role("reader"))])
async def get_chapters(config=Depends(get_config)):
    """РЎРїРёСЃРѕРє РіР»Р°РІ РєРЅРёРіРё (Р±РµР· РєРѕРЅС‚РµРЅС‚Р°)."""
    chapters = _load_chapters(config)
    return {
        "ok": True,
        "data": [
            {"id": ch["id"], "title": ch["title"], "char_count": ch["char_count"], "index": ch["index"]}
            for ch in chapters
        ],
        "total": len(chapters),
    }


@router.get("/chapters/{chapter_id}", dependencies=[Depends(require_role("reader"))])
async def get_chapter(chapter_id: str, config=Depends(get_config)):
    """РўРµРєСЃС‚ РєРѕРЅРєСЂРµС‚РЅРѕР№ РіР»Р°РІС‹."""
    chapters = _load_chapters(config)
    for ch in chapters:
        if ch["id"] == chapter_id:
            return {"ok": True, "data": ch}
    raise HTTPException(404, "Р“Р»Р°РІР° РЅРµ РЅР°Р№РґРµРЅР°")


@lru_cache(maxsize=1)
def _build_full_text(config_obj=None) -> str:
    """РЎРєР»РµРµРЅРЅС‹Р№ С‚РµРєСЃС‚ РІСЃРµР№ РєРЅРёРіРё вЂ” РєСЌС€РёСЂСѓРµС‚СЃСЏ РѕРґРёРЅ СЂР°Р·."""
    chunks = _load_enriched_chunks(config_obj)
    return "\n\n".join(ch.get("text", "") for ch in chunks)


@router.get("/text", dependencies=[Depends(require_role("reader"))])
async def get_book_text(offset: int = Query(0, ge=0), limit: int = Query(2000, ge=100, le=10000), config=Depends(get_config)):
    """Р¤СЂР°РіРјРµРЅС‚ С‚РµРєСЃС‚Р° РєРЅРёРіРё СЃ РїР°РіРёРЅР°С†РёРµР№ РїРѕ СЃРёРјРІРѕР»Р°Рј."""
    full_text = _build_full_text(config)
    if not full_text:
        raise HTTPException(404, "РўРµРєСЃС‚ РєРЅРёРіРё РЅРµ РЅР°Р№РґРµРЅ")
    total = len(full_text)
    chunk = full_text[offset:offset + limit]
    return {
        "ok": True,
        "data": chunk,
        "offset": offset,
        "limit": limit,
        "total": total,
        "has_more": offset + limit < total,
    }


# в”Ђв”Ђ Screenplay: РєРёРЅРѕСЃС†РµРЅР°СЂРёР№ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


@lru_cache(maxsize=1)
def _load_screenplay_text(config_obj=None) -> str:
    if config_obj is None:
        config_obj = get_config()
    path = config_obj.SOURCE_OF_TRUTH / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_screenplay_scenes(text: str) -> list[dict]:
    """Р Р°Р·Р±РёС‚СЊ СЃС†РµРЅР°СЂРёР№ РЅР° СЃС†РµРЅС‹ РїРѕ Р·Р°РіРѕР»РѕРІРєР°Рј (N. INT/EXT)."""
    if not text:
        return []

    lines = text.split("\n")
    scenes = []
    current_title = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.\s+(INT|EXT)", stripped):
            if current_lines and current_title:
                content = "\n".join(current_lines).strip()
                if content:
                    scenes.append({
                        "id": f"scene_{len(scenes):03d}",
                        "title": current_title,
                        "content": content,
                        "char_count": len(content),
                    })
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines and current_title:
        content = "\n".join(current_lines).strip()
        if content:
            scenes.append({
                "id": f"scene_{len(scenes):03d}",
                "title": current_title,
                "content": content,
                "char_count": len(content),
            })

    for i, s in enumerate(scenes):
        s["id"] = f"scene_{i:03d}"
        s["index"] = i

    return scenes


@lru_cache(maxsize=1)
def _load_screenplay_scenes(config_obj=None) -> list[dict]:
    text = _load_screenplay_text(config_obj)
    return _parse_screenplay_scenes(text)


@router.get("/screenplay", dependencies=[Depends(require_role("reader"))])
async def get_screenplay_scenes(config=Depends(get_config)):
    """РЎРїРёСЃРѕРє СЃС†РµРЅ РєРёРЅРѕСЃС†РµРЅР°СЂРёСЏ."""
    scenes = _load_screenplay_scenes(config)
    return {
        "ok": True,
        "data": [
            {"id": s["id"], "title": s["title"], "char_count": s["char_count"], "index": s["index"]}
            for s in scenes
        ],
        "total": len(scenes),
    }


@router.get("/screenplay/genome", dependencies=[Depends(require_role("reader"))])
async def get_screenplay_genome():
    """Получить genome-данные сценария."""
    import json as _json
    kb = Path(__file__).resolve().parent.parent.parent.parent / "core" / "KNOWLEDGE"
    extracts_path = kb / "screenplay_extracts.json"
    if not extracts_path.exists():
        return {"ok": True, "data": {"characters": [], "dialogues": [], "locations": []}}
    extracts = _json.loads(extracts_path.read_text(encoding="utf-8"))
    characters = []
    for o in extracts.get("oceania_officers", []):
        characters.append({"name": o.get("name", ""), "role": o.get("rank", ""), "description": o.get("description", "")})
    stranger = extracts.get("the_stranger", "")
    if stranger:
        characters.append({"name": "Незнакомец", "role": "гипербореец", "description": stranger})
    dialogues = [{"participants": d.get("participants", []), "topic": d.get("topic", ""), "excerpt": d.get("excerpt", "")} for d in extracts.get("key_dialogues", [])]
    return {"ok": True, "data": {"characters": characters, "dialogues": dialogues, "total_characters": len(characters), "total_dialogues": len(dialogues)}}



@router.get("/screenplay/context/{query}", dependencies=[Depends(require_role("reader"))])
async def get_screenplay_context(query: str):
    """RAG-поиск по screenplay с genome-обогащением."""
    import json as _json
    kb = Path(__file__).resolve().parent.parent.parent.parent / "core" / "KNOWLEDGE"
    extracts_path = kb / "screenplay_extracts.json"
    if not extracts_path.exists():
        return {"ok": True, "data": {"dialogues": [], "characters": [], "visual_notes": []}}
    extracts = _json.loads(extracts_path.read_text(encoding="utf-8"))
    q = query.lower()
    dialogues = []
    for d in extracts.get("key_dialogues", []):
        participants = " ".join(d.get("participants", [])).lower()
        topic = d.get("topic", "").lower()
        if any(w in q for w in participants.split() + topic.split()):
            dialogues.append({"scene": d.get("scene", ""), "participants": d.get("participants", []), "topic": d.get("topic", ""), "excerpt": d.get("excerpt", ""), "significance": d.get("significance", "")})
    characters = []
    for o in extracts.get("oceania_officers", []):
        if o.get("name", "").lower() in q:
            characters.append({"name": o["name"], "role": o.get("rank", ""), "description": o.get("description", ""), "key_dialogue": o.get("key_dialogue", "")})
    visual_notes = []
    if "незнакомец" in q:
        s = extracts.get("the_stranger", "")
        if s:
            visual_notes.append({"name": "Незнакомец", "description": s})
    if any(w in q for w in ["обучение", "комната", "транс"]):
        room = extracts.get("teaching_room", {})
        if room:
            visual_notes.append({"name": "Комната обучения", "description": room.get("description", "")})
    return {"ok": True, "data": {"dialogues": dialogues, "characters": characters, "visual_notes": visual_notes}}

@router.get("/screenplay/{scene_id}", dependencies=[Depends(require_role("reader"))])
async def get_screenplay_scene(scene_id: str, config=Depends(get_config)):
    """РўРµРєСЃС‚ РєРѕРЅРєСЂРµС‚РЅРѕР№ СЃС†РµРЅС‹."""
    scenes = _load_screenplay_scenes(config)
    for s in scenes:
        if s["id"] == scene_id:
            return {"ok": True, "data": s}
    raise HTTPException(404, "РЎС†РµРЅР° РЅРµ РЅР°Р№РґРµРЅР°")



# ── Screenplay Genome ──────────────────────────────────


# ── Knowledge Autocomplete ─────────────────────────────


@router.get("/knowledge/autocomplete", dependencies=[Depends(require_role("reader"))])
async def knowledge_autocomplete(q: str = "", limit: int = 8):
    """Автодополнение для поисковой строки."""
    if not q or len(q) < 1:
        return {"ok": True, "data": [], "query": q}

    q_lower = q.lower()
    suggestions = []

    # 1. Search in ExpansionLayer topics
    try:
        loader = _get_expansion_loader()
        if loader:
            for topic in loader._knowledge.keys():
                if q_lower in topic:
                    suggestions.append({"text": topic, "type": "expansion", "score": 10 if topic.startswith(q_lower) else 5})
    except Exception as e:
        log.warning("autocomplete_expansion_error: %s", e)

    # 2. Search in Genome themes
    try:
        genome = _get_genome_data()
        modules = genome.get("modules", {})
        for theme in modules.get("themes", []):
            name = theme.get("name", "")
            if q_lower in name.lower():
                suggestions.append({"text": name, "type": "theme", "score": 8 if name.lower().startswith(q_lower) else 4})
        for char in modules.get("characters", []):
            name = char.get("name", "")
            if q_lower in name.lower():
                suggestions.append({"text": name, "type": "character", "score": 8 if name.lower().startswith(q_lower) else 4})
        for sym in modules.get("symbols", []):
            name = sym.get("name", "")
            if q_lower in name.lower():
                suggestions.append({"text": name, "type": "symbol", "score": 6 if name.lower().startswith(q_lower) else 3})
    except Exception as e:
        log.warning("autocomplete_genome_error: %s", e)

    # 3. Sort by score and limit
    suggestions.sort(key=lambda x: x.get("score", 0), reverse=True)
    seen = set()
    unique = []
    for s in suggestions:
        if s["text"].lower() not in seen:
            seen.add(s["text"].lower())
            unique.append(s)
    return {"ok": True, "data": unique[:limit], "query": q}

# ── Knowledge Search ──────────────────────────────────


@router.get("/knowledge/search", dependencies=[Depends(require_role("reader"))])
async def search_knowledge(q: str = "", limit: int = 10, offset: int = 0, type: str = "", sort: str = "relevance"):
    """Поиск по базе знаний (ExpansionLayer + Genome).
    
    Параметры:
      q: поисковый запрос
      limit: максимальное количество результатов (по умолчанию 10)
      offset: смещение для пагинации (по умолчанию 0)
      type: фильтр по типу контента (theme, character, symbol, conflict, expansion)
      sort: сортировка (relevance или date)
    """
    if not q or len(q) < 2:
        return {"ok": True, "data": [], "query": q, "type_filter": type, "total": 0, "offset": offset, "limit": limit}

    # 1. Search in ExpansionLayer
    expansion_results = []
    try:
        loader = _get_expansion_loader()
        if loader and (not type or type == "expansion"):
            expansion_results = loader.search(q, limit=limit + offset + 50)
    except Exception as e:
        log.warning("search_expansion_error: %s", e)
        expansion_results = []

    # 2. Search in Genome
    try:
        genome = _get_genome_data()
        genome_results = []
        modules = genome.get("modules", {})
        q_lower = q.lower()

        # Search themes
        if not type or type == "theme":
         for theme in modules.get("themes", []):
            name = theme.get("name", "").lower()
            desc = theme.get("description", "").lower()
            if q_lower in name or q_lower in desc:
                genome_results.append({"type": "theme", "name": theme.get("name", ""), "description": theme.get("description", "")[:200]})

        # Search characters
        if not type or type == "character":
         for char in modules.get("characters", []):
            name = char.get("name", "").lower()
            desc = char.get("description", "").lower()
            if q_lower in name or q_lower in desc:
                genome_results.append({"type": "character", "name": char.get("name", ""), "description": char.get("description", "")[:200]})

        # Search symbols
        if not type or type == "symbol":
         for sym in modules.get("symbols", []):
            name = sym.get("name", "").lower()
            desc = sym.get("description", "").lower()
            if q_lower in name or q_lower in desc:
                genome_results.append({"type": "symbol", "name": sym.get("name", ""), "description": sym.get("description", "")[:200]})

        # Search conflicts
        if not type or type == "conflict":
         for conf in modules.get("conflicts", []):
            name = conf.get("name", "").lower()
            desc = conf.get("description", "").lower()
            if q_lower in name or q_lower in desc:
                genome_results.append({"type": "conflict", "name": conf.get("name", ""), "description": conf.get("description", "")[:200]})
    except Exception as e:
        log.warning("search_genome_error: %s", e)
        genome_results = []

    # 3. Combine results
    all_results = []
    for r in expansion_results[:limit]:
        all_results.append({
            "source": "expansion",
            "topic": r.get("topic", ""),
            "score": r.get("score", 0),
            "data": {k: v for k, v in r.get("data", {}).items() if k != "layers"} if isinstance(r.get("data"), dict) else {},
        })
    for r in genome_results[:limit]:
        all_results.append({
            "source": "genome",
            "type": r.get("type", ""),
            "name": r.get("name", ""),
            "description": r.get("description", ""),
        })

        # Sort results
    if sort == "date":
        all_results.sort(key=lambda x: x.get("data", {}).get("added_at", x.get("created_at", "")), reverse=True)
    else:
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Apply pagination
    paginated = all_results[offset:offset + limit]
    return {"ok": True, "data": paginated, "query": q, "total": len(all_results), "offset": offset, "limit": limit, "type_filter": type or "all", "sort": sort}


# ── Cache Stats ──────────────────────────────────────────

@router.get("/cache/stats", summary="Статистика кэша", dependencies=[Depends(require_role("reader"))])
async def cache_stats():
    """Показать статистику всех кэшей."""
    from core.cache import genome_cache, chunks_cache, world_model_cache, api_cache, rag_cache
    return {
        "ok": True,
        "data": {
            "genome": genome_cache.stats,
            "chunks": chunks_cache.stats,
            "world_model": world_model_cache.stats,
            "api": api_cache.stats,
            "rag": rag_cache.stats,
        }
    }
