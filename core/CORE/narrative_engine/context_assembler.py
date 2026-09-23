"""Context Assembler — сборка полного контекста из всех источников.

Гибридный подход:
- ChromaDB (BookRetriever) для семантического поиска
- enriched_chunks.json для фильтрации по метаданным
- WorldModel для структурированных данных
- JSON-файлы KNOWLEDGE/ для тем, символов, мифологии
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.canon_validator import CanonCheckResult
from narrative_engine.contexts.historical import HistoricalContext, HistoricalContextBuilder
from narrative_engine.contexts.geography import GeographyContext, GeographyContextBuilder
from narrative_engine.contexts.mythology import MythologyContext, MythologyContextBuilder

log = logging.getLogger("hermes.narrative.context_assembler")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"

# Module-level cache for expensive resources
_retriever_cache = None
_enriched_chunks_cache = None
_enriched_chunks_loaded = False


class ScreenplayContext(BaseModel):
    """Screenplay context for visual/cinematic scenes."""
    scenes: list[str] = Field(default_factory=list)
    dialogues: list[str] = Field(default_factory=list)
    visual_notes: list[str] = Field(default_factory=list)


class BookContext(BaseModel):
    """Контекст из книги (RAG)."""
    chunks: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    source_chunks: list[dict] = Field(default_factory=list)


class FullContext(BaseModel):
    """Полный контекст для генерации истории."""
    world_state: Optional[dict] = None
    historical: HistoricalContext = Field(default_factory=HistoricalContext)
    geography: GeographyContext = Field(default_factory=GeographyContext)
    mythology: MythologyContext = Field(default_factory=MythologyContext)
    book: BookContext = Field(default_factory=BookContext)
    screenplay: ScreenplayContext = Field(default_factory=ScreenplayContext)
    relevant_chunks: list[str] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)


class ContextAssembler:
    """
    Собирает полный контекст из всех источников.

    Использование:
        assembler = ContextAssembler(world_model)
        full_context = assembler.assemble(canon_result)
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._historical_builder = HistoricalContextBuilder(world_model)
        self._geography_builder = GeographyContextBuilder(world_model)
        self._mythology_builder = MythologyContextBuilder()
        self._retriever = None
        self._resolver = None
        self._enriched_chunks = None

    def _get_retriever(self):
        global _retriever_cache
        if _retriever_cache is None:
            try:
                from intelligence.retriever import BookRetriever
                _retriever_cache = BookRetriever()
                log.info("BookRetriever initialized (cached)")
            except ImportError:
                log.warning("BookRetriever not available, RAG disabled")
        return _retriever_cache

    def _get_resolver(self):
        if self._resolver is None:
            try:
                from intelligence.nameresolver import NameResolver
                self._resolver = NameResolver()
            except ImportError:
                log.warning("NameResolver not available")
        return self._resolver

    def _load_enriched_chunks(self) -> list:
        global _enriched_chunks_cache, _enriched_chunks_loaded
        if _enriched_chunks_loaded:
            return _enriched_chunks_cache or []
        path = KNOWLEDGE_DIR / "enriched_chunks.json"
        if path.exists():
            try:
                _enriched_chunks_cache = json.loads(path.read_text(encoding="utf-8"))
                log.info("enriched_chunks loaded (cached) count=%d", len(_enriched_chunks_cache))
            except Exception:
                _enriched_chunks_cache = []
        else:
            _enriched_chunks_cache = []
        _enriched_chunks_loaded = True
        return _enriched_chunks_cache

    def assemble(self, canon: CanonCheckResult) -> FullContext:
        request = canon.constraints.story_request
        ctx = canon.constraints.resolved_context

        epoch_id = ctx.epoch.get("id") if ctx.epoch else None
        location_id = ctx.location.get("id") if ctx.location else None

        # Parallel context building: historical + geography + mythology + book
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._historical_builder.build, epoch_id): "historical",
                executor.submit(self._geography_builder.build, location_id, epoch_id): "geography",
                executor.submit(self._mythology_builder.build, request.prompt): "mythology",
                executor.submit(self._build_book_context, request.prompt, ctx): "book",
            }
            results = {}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    log.error("context_build_error stage=%s error=%s", name, e)
                    results[name] = self._default_for(name)

        historical = results["historical"]
        geography = results["geography"]
        mythology = results["mythology"]
        book_ctx = results["book"]

        key_facts = []
        key_facts.extend(canon.allowed_facts)
        key_facts.extend([f.text for f in historical.epoch_facts[:3]])
        key_facts.extend(book_ctx.facts[:5])

        screenplay_ctx = self._build_screenplay_context(request.prompt)

        return FullContext(
            world_state=ctx.model_dump() if hasattr(ctx, 'model_dump') else ctx,
            historical=historical,
            geography=geography,
            mythology=mythology,
            book=book_ctx,
            screenplay=screenplay_ctx,
            relevant_chunks=book_ctx.chunks + screenplay_ctx.scenes,
            key_facts=key_facts,
        )

    def _default_for(self, stage: str):
        """Вернуть пустой объект при ошибке."""
        from narrative_engine.contexts.historical import HistoricalContext
        from narrative_engine.contexts.geography import GeographyContext
        from narrative_engine.contexts.mythology import MythologyContext
        defaults = {
            "historical": HistoricalContext,
            "geography": GeographyContext,
            "mythology": MythologyContext,
            "book": BookContext,
        }
        return defaults.get(stage, lambda: None)()

    def _build_screenplay_context(self, query: str) -> ScreenplayContext:
        """Build screenplay context from screenplay_extracts.json."""
        scenes = []
        dialogues = []
        visual_notes = []

        extracts_path = KNOWLEDGE_DIR / "screenplay_extracts.json"
        if not extracts_path.exists():
            return ScreenplayContext()

        try:
            extracts = json.loads(extracts_path.read_text(encoding="utf-8"))
        except Exception:
            return ScreenplayContext()

        q = query.lower()

        # Match dialogues
        for d in extracts.get("key_dialogues", []):
            participants = " ".join(d.get("participants", [])).lower()
            topic = d.get("topic", "").lower()
            if any(w in q for w in participants.split() + topic.split()):
                dialogues.append(
                    f"Dialogue ({d.get('scene', '')}): {d.get('participants', [])} - {d.get('topic', '')}\n"
                    f"\u00ab{d.get('excerpt', '')}\u00bb"
                )

        # Match characters
        for o in extracts.get("oceania_officers", []):
            if o.get("name", "").lower() in q:
                visual_notes.append(f"{o['name']}: {o.get('description', '')}")

        # Stranger
        if "незнакомец" in q or "stranger" in q:
            s = extracts.get("the_stranger", "")
            if s:
                visual_notes.append(f"The Stranger: {s}")

        # Teaching room
        if any(w in q for w in ["обучение", "комната", "транс", "teaching"]):
            room = extracts.get("teaching_room", {})
            if room:
                visual_notes.append(f"Teaching room: {room.get('description', '')}")

        return ScreenplayContext(
            scenes=scenes[:5],
            dialogues=dialogues[:5],
            visual_notes=visual_notes[:5],
        )


    def _build_book_context(self, query: str, resolved_context) -> BookContext:
        chunks = []
        facts = []
        source_chunks = []

        resolver = self._get_resolver()
        expanded_query = query
        if resolver:
            try:
                expanded_terms = resolver.expand_query(query)
                expanded_query = " ".join(expanded_terms)
            except Exception:
                pass

        retriever = self._get_retriever()
        if retriever:
            try:
                vector_results = retriever.search(expanded_query, n_results=10)
                for r in vector_results:
                    chunks.append(r.get("text", ""))
                    source_chunks.append({
                        "text": r.get("text", "")[:300],
                        "score": r.get("score", 0),
                        "chapter": r.get("chapter_title", ""),
                        "themes": r.get("themes", []),
                    })
            except Exception as e:
                log.warning("retriever_search_error error=%s", e)

        enriched = self._load_enriched_chunks()
        if enriched:
            relevant_themes = set()
            relevant_characters = set()

            chars_alive = resolved_context.characters_alive if hasattr(resolved_context, 'characters_alive') else []
            for fact in chars_alive:
                name = fact.get("character_name", "") if isinstance(fact, dict) else ""
                if name:
                    relevant_characters.add(name.lower())

            for chunk in enriched:
                chunk_themes = set(t.lower() for t in chunk.get("enriched_themes", []))
                chunk_chars = set(c.lower() for c in chunk.get("enriched_characters", []))

                theme_match = bool(chunk_themes & relevant_themes) if relevant_themes else False
                char_match = bool(chunk_chars & relevant_characters) if relevant_characters else False

                if theme_match or char_match:
                    text = chunk.get("text", "")
                    if text and text not in chunks:
                        chunks.append(text)
                        facts.append(f"Из книги: {text[:150]}...")

        return BookContext(
            chunks=chunks[:15],
            facts=facts[:10],
            source_chunks=source_chunks[:10],
        )
