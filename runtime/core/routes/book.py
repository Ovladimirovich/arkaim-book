"""Book Intelligence — основные эндпоинты (/book/*)."""

import json
import logging
import re
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.rbac import require_role
from core.adc_deps import (
    get_config,
    get_drafts,
    get_event_logger,
    get_herald,
    get_keeper,
    get_pulse,
)
from core.cache import chunks_cache, genome_cache
from core.dto.requests import BookAskRequest, BookGenerateRequest
from core.dto.responses import (
    BookGenomeResponse,
    BookLayersResponse,
    HealthResponse,
    SuccessResponse,
)

log = logging.getLogger("hermes.routes.book")


_expansion_loader = None
_expansion_loader_mtime: float = 0


def _get_expansion_loader():
    """Cached ExpansionLoader - reloads if KNOWLEDGE files changed."""
    global _expansion_loader, _expansion_loader_mtime

    try:
        from knowledge_expansion.expansion_loader import ExpansionLoader
        from knowledge_expansion.store.knowledge_store import KNOWLEDGE_DIR

        # Check if any knowledge file has changed
        current_mtime = 0
        if KNOWLEDGE_DIR and KNOWLEDGE_DIR.exists():
            for f in KNOWLEDGE_DIR.rglob("*.json"):
                try:
                    current_mtime = max(current_mtime, f.stat().st_mtime)
                except OSError:
                    pass

        if _expansion_loader is None or current_mtime > _expansion_loader_mtime:
            loader = ExpansionLoader()
            loader.load()
            _expansion_loader = loader
            _expansion_loader_mtime = current_mtime

        return _expansion_loader
    except Exception as e:
        log.warning("expansion_loader_init_failed: %s", e)
        return None


def reset_expansion_loader_cache() -> None:
    """Reset expansion loader cache (for testing)."""
    global _expansion_loader, _expansion_loader_mtime
    _expansion_loader = None
    _expansion_loader_mtime = 0


@lru_cache(maxsize=1)
def _get_genome_data():
    """Cached genome data - loads once."""
    try:
        from genome.extractor import GENOME_DIR, load_json

        return load_json(GENOME_DIR / "GENOME_v1.0.0.json")
    except Exception as e:
        log.warning("genome_load_failed: %s", e)
        return {}


router = APIRouter(tags=["Book Intelligence"])


@lru_cache(maxsize=1)
def _load_genome_raw() -> bytes | None:
    """Читаем genome JSON один раз, кэшируем сырой байт."""
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
from core.services.knowledge_core_context import gather_canonical_event_views, merge_knowledge_core as _merge_knowledge_core


def _stage2_enabled() -> bool:
    """OWNER-GATE для Stage 2 (gap-driven расширение знаний).

    По умолчанию выключено: система не расширяет знания по запросу читателя
    без явного решения владельца (принцип №4 «никаких автономных действий»).
    Флаг читается на каждом вызове, чтобы его можно было переключить без
    перезапуска процесса в dev-режиме.
    """
    try:
        from shared_config import settings as shared_settings

        return bool(getattr(shared_settings, "STAGE2_ENABLED", False))
    except Exception as exc:  # pragma: no cover - конфиг всегда доступен
        log.warning("stage2_gate_check_failed error=%s", exc)
        return False


def _edm_res_pilot_enabled() -> bool:
    """OWNER-GATE для EDM-RES пилота (/book/ask и /visualize).

    По умолчанию выключено: без флага ответ /book/ask не получает ключ
    `edm`, Voice использует штатный t1-провайдер — публичный контракт
    byte-идентичен legacy. Флаг читается на каждом вызове (dev-переключение
    без перезапуска, паттерн _stage2_enabled).
    """
    try:
        from shared_config import settings as shared_settings

        return bool(getattr(shared_settings, "EDM_RES_PILOT_ENABLED", False))
    except Exception as exc:  # pragma: no cover - конфиг всегда доступен
        log.warning("edm_res_pilot_gate_check_failed error=%s", exc)
        return False


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
        raise HTTPException(404, "Геном не найден")
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
        raise HTTPException(503, "Pulse не загружен")
    k = pulse.layers.get("knowledge")
    m = pulse.layers.get("meaning")
    i = pulse.layers.get("identity")
    ms = pulse.layers.get("mission")
    w = pulse.layers.get("world_engine")
    e = pulse.layers.get("expansion")
    return BookLayersResponse(
        knowledge_layer=k.summary if k else "",
        meaning_layer=m.summary if m else "",
        identity_layer=i.summary if i else "",
        mission_layer=ms.summary if ms else "",
        world_engine_layer=w.summary if w else "",
        expansion_layer=e.summary if e else "",
    )


@router.post("/ask", response_model=SuccessResponse, summary="Задать вопрос книге")
async def ask(
    req: BookAskRequest,
    user: dict = Depends(require_role("reader")),
    keeper=Depends(get_keeper),
    event_logger=Depends(get_event_logger),
):
    from core.presence_manager import register_question

    result = await keeper.act(
        {
            "question": req.question,
            "context": req.context,
            "messages": [{"role": m.role, "content": m.content} for m in (req.messages or [])],
            "reader_id": user.get("user_id", ""),
            "reader_name": user.get("display_name", "") or user.get("username", ""),
        }
    )
    # Подмешиваем оригинал вопроса в payload скоринга related_entities.
    # Контракт keeper.act() не возвращает question, а только ответ — без
    # оригинала тематическое отношение теряется: краткий ответ, не назвавший
    # часть тем вопроса, приводит к тому, что эти темы не доходят до
    # Knowledge Core. Вопрос — авторитетный источник тем, но контракт
    # ответа наружу не меняется (всплываемый вопрос не появляется в data).
    #
    # Option B, t1: Knowledge Context уже собран ДО LLM (voice, по вопросу и
    # тексту слоя) и приходит во внутреннем ключе — переиспользуем его для
    # metadata, считая дельту (новые сущности финального ответа) только один раз.
    # Ключ снимается ДО metadata/ответа: публичный контракт не меняется.
    t1_contexts = result.pop("_dialogue_context", None) or []
    result["related_entities"] = _resolve_related_entities({**result, "question": req.question})
    result["knowledge_core"] = _merge_knowledge_core(t1_contexts, result["related_entities"])
    result["canonical_events"] = gather_canonical_event_views(result["knowledge_core"])

    # Stage 2: managed knowledge expansion. Если Knowledge Core не
    # закрывает вопрос (MISSING / PARTIALLY_KNOWN), гоняем gap-driven
    # pipeline: source search -> candidates -> validation -> ACCEPT-only
    # storage в изолированный ASK_EXPANSIONS.json. Сбоя не ломает ask —
    # расширение не критично для ответа. CONFLICTING НЕ расширяем
    # автоматически: конфликт требует владельца.
    #
    # OWNER-GATE: Stage 2 выключен по умолчанию (shared_config.STAGE2_ENABLED).
    # Пока флаг выключен, публичный контракт /book/ask не меняется — ключ
    # knowledge_expansion в ответе не появляется. Даже при включении Stage 2
    # пишет предложения в runtime-пространство, а не в core/KNOWLEDGE.
    if _stage2_enabled():
        try:
            from core.services.ask_gap_detector import detect_gap as _detect_gap
            from core.services.ask_expansion_orchestrator import (
                expand as _expand,
            )

            gap_report = _detect_gap(
                req.question,
                related_entities=result["related_entities"],
                existing_knowledge_core=result["knowledge_core"],
            )
            if gap_report.status in ("MISSING", "PARTIALLY_KNOWN"):
                expansion = await _expand(
                    req.question,
                    related_entities=result["related_entities"],
                    knowledge_contexts=result["knowledge_core"],
                )
                result["knowledge_expansion"] = {
                    "gap_status": gap_report.status,
                    "accepted": len(expansion.accepted),
                    "review": len(expansion.review),
                    "rejected": len(expansion.rejected),
                    "gap_closed": expansion.gap_recheck.get("gap_closed"),
                    "summary": expansion.summary,
                }
            else:
                result["knowledge_expansion"] = {
                    "gap_status": gap_report.status,
                    "accepted": 0,
                    "review": 0,
                    "rejected": 0,
                    "gap_closed": None,
                    "summary": "Extension not required: knowledge already sufficient (status=%s)." % gap_report.status,
                }
        except Exception as _exp_exc:
            import logging as _logging

            _logging.getLogger("hermes.book_ask").warning(
                "knowledge_expansion_failed question=%s error=%s",
                req.question[:60],
                _exp_exc,
            )
            result["knowledge_expansion"] = {
                "gap_status": "ERROR",
                "summary": "Knowledge extension not executed: %s" % _exp_exc,
            }

    # EDM-RES пилот (OWNER-GATE, по умолчанию выключено): при флаге ответ
    # /book/ask получает опциональный metadata-блок `edm` — слоистое описание
    # затронутых сущностей из Entity Description Model (provenance-слои,
    # честные границы знания). Ключ additive: нет совпадения сущностей —
    # ключ не появляется; флаг выключен — ответ byte-identичен legacy.
    # Сбой блока не ломает ответ (как Stage 2: пилот не критичен).
    if _edm_res_pilot_enabled():
        try:
            from core.services.edm_pilot import build_edm_dialogue_block

            edm_block = build_edm_dialogue_block(req.question, result.get("answer", ""))
            if edm_block:
                result["edm"] = edm_block
        except Exception as _edm_exc:
            import logging as _logging

            _logging.getLogger("hermes.book_ask").warning(
                "edm_pilot_block_failed question=%s error=%s",
                req.question[:60],
                _edm_exc,
            )

    event_logger.log_event(
        {
            "event_type": "api_ask",
            "topic": req.question[:100],
            "user_sentiment": "neutral",
            "system_action": "keeper_response",
            "outcome": "ok",
        }
    )
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

    # WebSocket уведомление
    from core.websocket import notify_new_question

    await notify_new_question(req.question, req.question[:60], user.get("user_id", ""))

    return SuccessResponse(data=persisted_result)


@router.post("/generate", response_model=SuccessResponse, summary="Генерация контента", dependencies=[Depends(require_role("editor"))])
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


@router.get("/drafts", response_model=SuccessResponse, summary="Получить черновики", dependencies=[Depends(require_role("reader"))])
async def get_drafts_endpoint(status: str | None = None, drafts=Depends(get_drafts)):
    if status == "pending":
        return SuccessResponse(data=drafts.get_pending_drafts())
    return SuccessResponse(data=drafts.get_all_drafts())


@router.post("/drafts/{draft_id}/approve", response_model=SuccessResponse, summary="Одобрить черновик", dependencies=[Depends(require_role("editor"))])
async def approve_draft(draft_id: str, drafts=Depends(get_drafts)):
    if drafts.approve_draft(draft_id):
        return SuccessResponse(data={"status": "approved", "draft_id": draft_id})
    raise HTTPException(404, "Черновик не найден")


@router.get("/memory/stats", response_model=SuccessResponse, summary="Статистика памяти", dependencies=[Depends(require_role("admin"))])
async def get_memory_stats(event_logger=Depends(get_event_logger)):
    if hasattr(event_logger, "get_statistics"):
        return SuccessResponse(data=event_logger.get_statistics())
    return SuccessResponse(data={"total_events": 0, "status": "ok"})


# ── Chapters: чтение текста книги ─────────────────


@lru_cache(maxsize=1)
def _load_enriched_chunks(config_obj=None) -> list[dict]:
    """Загрузить enriched_chunks.json (разбитые на главы чанки)."""
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
    """Сгруппировать чанки по chapter_title в главы.

    Внутри «Пролог» автоматически разделяется «Часть 1»: чанки, начинающиеся
    с фразы «Одинокая, словно каменное изваяние…», образуют отдельную главу.
    Это сохраняет исходные тексты без изменений, но даёт корректную структуру
    оглавления: титульная → Пролог → Часть 1 → Часть 2 … → Эпилог.
    """
    if not chunks:
        return []

    from collections import OrderedDict

    chapter_map: dict[str, list[dict]] = OrderedDict()

    for ch in chunks:
        title = ch.get("chapter_title", "Без названия")
        if title not in chapter_map:
            chapter_map[title] = []
        chapter_map[title].append(ch)

    # Маркер, по которому внутри «Пролог» отделяется «Часть 1».
    _PART1_MARKER = "Одинокая, словно каменное изваяние"

    chapters: list[dict] = []

    for title, parts in chapter_map.items():
        if title == "Пролог":
            prolog_parts: list[dict] = []
            part1_parts: list[dict] = []
            for p in parts:
                if not part1_parts and _PART1_MARKER in p.get("text", ""):
                    part1_parts.append(p)
                elif part1_parts:
                    part1_parts.append(p)
                else:
                    prolog_parts.append(p)

            if prolog_parts:
                content = "\n\n".join(p.get("text", "") for p in prolog_parts)
                chapters.append(
                    {
                        "id": f"ch_{len(chapters):02d}",
                        "title": "Пролог",
                        "content": content,
                        "char_count": len(content),
                        "index": len(chapters),
                        "section_type": "prologue",
                    }
                )
            if part1_parts:
                content = "\n\n".join(p.get("text", "") for p in part1_parts)
                chapters.append(
                    {
                        "id": f"ch_{len(chapters):02d}",
                        "title": "Часть 1",
                        "content": content,
                        "char_count": len(content),
                        "index": len(chapters),
                        "section_type": "part",
                    }
                )
        else:
            large_parts = [p for p in parts if len(p.get("text", "")) > 1000]
            if large_parts:
                content = large_parts[0].get("text", "")
            else:
                content = "\n\n".join(p.get("text", "") for p in parts)

            if title == "Часть 0":
                section_type = "title"
            elif title == "Эпилог":
                section_type = "epilogue"
            else:
                section_type = "part"

            chapters.append(
                {
                    "id": f"ch_{len(chapters):02d}",
                    "title": title,
                    "content": content,
                    "char_count": len(content),
                    "index": len(chapters),
                    "section_type": section_type,
                }
            )

    return chapters


@lru_cache(maxsize=1)
def _load_chapters(config_obj=None) -> list[dict]:
    chunks = _load_enriched_chunks(config_obj)
    return _build_chapters_from_chunks(chunks)


@router.get("/chapters", dependencies=[Depends(require_role("reader"))])
async def get_chapters(config=Depends(get_config)):
    """Список глав книги (без контента)."""
    chapters = _load_chapters(config)
    return {
        "ok": True,
        "data": [
            {"id": ch["id"], "title": ch["title"], "char_count": ch["char_count"], "index": ch["index"], "section_type": ch.get("section_type", "part")}
            for ch in chapters
        ],
        "total": len(chapters),
    }


@router.get("/chapters/{chapter_id}", dependencies=[Depends(require_role("reader"))])
async def get_chapter(chapter_id: str, config=Depends(get_config)):
    """Текст конкретной главы."""
    chapters = _load_chapters(config)
    for ch in chapters:
        if ch["id"] == chapter_id:
            return {"ok": True, "data": ch}
    raise HTTPException(404, "Глава не найдена")


@lru_cache(maxsize=1)
def _build_full_text(config_obj=None) -> str:
    """Склеенный текст всей книги — кэшируется один раз."""
    chunks = _load_enriched_chunks(config_obj)
    return "\n\n".join(ch.get("text", "") for ch in chunks)


@router.get("/text", dependencies=[Depends(require_role("reader"))])
async def get_book_text(offset: int = Query(0, ge=0), limit: int = Query(2000, ge=100, le=10000), config=Depends(get_config)):
    """Фрагмент текста книги с пагинацией по символам."""
    full_text = _build_full_text(config)
    if not full_text:
        raise HTTPException(404, "Текст книги не найден")
    total = len(full_text)
    chunk = full_text[offset : offset + limit]
    return {
        "ok": True,
        "data": chunk,
        "offset": offset,
        "limit": limit,
        "total": total,
        "has_more": offset + limit < total,
    }


# ── Screenplay: киносценарий ─────────────────────────────


# Маркеры типа сцены: латиница INT/EXT, русские синонимы и монтажные блоки.
_SCENE_MARKERS = r"(?:INT|EXT|ВНУТРЕННИЙ|НАРУЖНЫЙ|ВНЕШНИЙ|ИНТ|ЭКСТ|MONTAGE|МОНТАЖ)"

# Нумерованный заголовок сцены. Терпит разные форматы исходника:
#   «1. EXT. ГЛУБОКИЙ КОСМОС», «13.EXT. ОКЕАН - ДЕНЬ» (без пробела после точки),
#   « 21. EXT. …» (с отступом), «78.ВНУТРЕННИЙ ЗАЛ» (русский маркер),
#   «42. МОНТАЖ - ОБУЧЕНИЕ», «47. MONTAGE …», а также «20 EXT. …»
#   (номер без точки, вместо неё пробел).
# Синхронизирован с core/CORE/intelligence/chunker.py (ScreenplayChunker) —
# правила должны совпадать, чтобы структура индексации не расходилась со списком в UI.
_SCENE_HEADER_RE = re.compile(rf"^\s*\d+(?:\.\s*|\s+){_SCENE_MARKERS}\b", re.IGNORECASE)

# Финальная сцена без номера («INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ»). Название локации
# идёт в ВЕРХНЕМ регистре; это отсекает обычные ремарки вида «EXT. Заснеженные горы…».
_UNNUMBERED_SCENE_HEADER_RE = re.compile(rf"^\s*{_SCENE_MARKERS}\.\s+[А-ЯЁA-Z]{{2,}}")

# Строка только с номером («88.») — часть разорванного заголовка, склеивается
# со следующей строкой-маркером («EXT.ДОЛИНА…») в _merge_split_scene_headers.
_NUMBER_ONLY_RE = re.compile(r"^\s*\d+\.\s*$")
_MARKER_ONLY_RE = re.compile(rf"^\s*{_SCENE_MARKERS}\.", re.IGNORECASE)

# Отделяет маркер (с необязательным номером) от названия локации для _extract_location.
_SCENE_HEADER_PREFIX_RE = re.compile(
    rf"^\s*(?:\d+\s*\.?\s*)?{_SCENE_MARKERS}\.?\s*(.*)$",
    re.IGNORECASE,
)


def _merge_split_scene_headers(lines: list[str]) -> list[str]:
    """Склеить разорванные заголовки («88.» + «EXT.ДОЛИНА…») в одну строку.

    Работает по копии строк для парсинга; исходный текст сценария не меняется.
    Номер и маркер остаются в тексте, поэтому ничего не теряется.
    """
    merged: list[str] = []
    i = 0
    while i < len(lines):
        if _NUMBER_ONLY_RE.match(lines[i].strip()) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if _MARKER_ONLY_RE.match(nxt):
                merged.append(f"{lines[i].strip()} {nxt}")
                i += 2
                continue
        merged.append(lines[i])
        i += 1
    return merged


def _is_screenplay_scene_header(stripped: str) -> bool:
    """True, если строка — заголовок сцены (нумерованный или финальный без номера)."""
    return bool(_SCENE_HEADER_RE.match(stripped) or _UNNUMBERED_SCENE_HEADER_RE.match(stripped))


def _extract_screenplay_location(title: str) -> str:
    """Название локации из заголовка сцены (латиница/русские маркеры, номер опционален)."""
    m = _SCENE_HEADER_PREFIX_RE.match(title)
    location = m.group(1).strip() if m else ""
    return location or title


@lru_cache(maxsize=1)
def _load_screenplay_text(config_obj=None) -> str:
    if config_obj is None:
        config_obj = get_config()
    path = config_obj.SOURCE_OF_TRUTH / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_screenplay_scenes(text: str) -> list[dict]:
    """Разбить сценарий на сцены по заголовкам (N. INT/EXT и варианты).

    Текст каждой сцены заканчивается перед следующим распознанным заголовком,
    поэтому несколько сцен не сливаются в одну. Повторяющиеся номера сохраняются
    как отдельные сцены — объединения по номеру нет.
    """
    if not text:
        return []

    lines = _merge_split_scene_headers(text.split("\n"))
    scenes = []
    current_title = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if _is_screenplay_scene_header(stripped):
            if current_lines and current_title:
                content = "\n".join(current_lines).strip()
                if content:
                    scenes.append(
                        {
                            "id": f"scene_{len(scenes):03d}",
                            "title": current_title,
                            "content": content,
                            "char_count": len(content),
                        }
                    )
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines and current_title:
        content = "\n".join(current_lines).strip()
        if content:
            scenes.append(
                {
                    "id": f"scene_{len(scenes):03d}",
                    "title": current_title,
                    "content": content,
                    "char_count": len(content),
                }
            )

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
    """Список сцен киносценария."""
    scenes = _load_screenplay_scenes(config)
    return {
        "ok": True,
        "data": [{"id": s["id"], "title": s["title"], "char_count": s["char_count"], "index": s["index"]} for s in scenes],
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
    dialogues = [
        {"participants": d.get("participants", []), "topic": d.get("topic", ""), "excerpt": d.get("excerpt", "")} for d in extracts.get("key_dialogues", [])
    ]
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
            dialogues.append(
                {
                    "scene": d.get("scene", ""),
                    "participants": d.get("participants", []),
                    "topic": d.get("topic", ""),
                    "excerpt": d.get("excerpt", ""),
                    "significance": d.get("significance", ""),
                }
            )
    characters = []
    for o in extracts.get("oceania_officers", []):
        if o.get("name", "").lower() in q:
            characters.append(
                {"name": o["name"], "role": o.get("rank", ""), "description": o.get("description", ""), "key_dialogue": o.get("key_dialogue", "")}
            )
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
    """Текст конкретной сцены."""
    scenes = _load_screenplay_scenes(config)
    for s in scenes:
        if s["id"] == scene_id:
            return {"ok": True, "data": s}
    raise HTTPException(404, "Сцена не найдена")


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
@router.post("/os/search", dependencies=[Depends(require_role("reader"))])
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
        all_results.append(
            {
                "source": "expansion",
                "topic": r.get("topic", ""),
                "score": r.get("score", 0),
                "data": {k: v for k, v in r.get("data", {}).items() if k != "layers"} if isinstance(r.get("data"), dict) else {},
            }
        )
    for r in genome_results[:limit]:
        all_results.append(
            {
                "source": "genome",
                "type": r.get("type", ""),
                "name": r.get("name", ""),
                "description": r.get("description", ""),
            }
        )

        # Sort results
    if sort == "date":
        all_results.sort(key=lambda x: x.get("data", {}).get("added_at", x.get("created_at", "")), reverse=True)
    else:
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Apply pagination
    paginated = all_results[offset : offset + limit]
    return {"ok": True, "data": paginated, "query": q, "total": len(all_results), "offset": offset, "limit": limit, "type_filter": type or "all", "sort": sort}


# ── Cache Stats ──────────────────────────────────────────


@router.get("/cache/stats", summary="Статистика кэша", dependencies=[Depends(require_role("reader"))])
async def cache_stats():
    """Показать статистику всех кэшей."""
    from core.cache import api_cache, rag_cache, world_model_cache

    return {
        "ok": True,
        "data": {
            "genome": genome_cache.stats,
            "chunks": chunks_cache.stats,
            "world_model": world_model_cache.stats,
            "api": api_cache.stats,
            "rag": rag_cache.stats,
        },
    }
