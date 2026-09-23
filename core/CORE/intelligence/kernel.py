"""
KnowledgeKernel — центральное информационное ядро проекта.
Объединяет:
  - SemanticChunker (структурный чанкинг)
  - GenomeEnricher (обогащение метаданными из генома)
  - BookRetriever (RAG-поиск по ChromaDB)
  - ChatPDFClient (дополнительный источник)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

from intelligence.chunker import SemanticChunker, ScreenplayChunker
from intelligence.enricher import GenomeEnricher
from intelligence.retriever import BookRetriever
from intelligence.cleaner import TextCleaner
from intelligence.nameresolver import NameResolver


BASE = Path(__file__).resolve().parents[2]


class KnowledgeKernel:
    def __init__(
        self,
        chunker: Optional[SemanticChunker] = None,
        enricher: Optional[GenomeEnricher] = None,
        retriever: Optional[BookRetriever] = None,
        cleaner: Optional[TextCleaner] = None,
        nameresolver: Optional[NameResolver] = None,
    ):
        self.nameresolver = nameresolver or NameResolver()
        self.chunker = chunker or SemanticChunker()
        self.enricher = enricher or GenomeEnricher(nameresolver=self.nameresolver)
        self.retriever = retriever or BookRetriever()
        self.cleaner = cleaner or TextCleaner()
        self._deep_characters = None
        self._concepts = None
        self._civ_profiles = None
        self._deep_profiles = None
        self._chatpdf = None

    @property
    def chatpdf(self):
        if self._chatpdf is None:
            try:
                from chatpdf_client import ChatPDFClient
                self._chatpdf = ChatPDFClient()
            except ImportError:
                pass
        return self._chatpdf

    def index_book(self, mode: str = "hybrid") -> Dict:
        """
        Полная индексация книги:
        1. Чанкинг (по абзацам + главам)
        2. Обогащение геномом
        3. Сохранение enriched_chunks.json
        4. Индексация в ChromaDB
        5. Сохранение enriched_catalog.json (для fallback)
        """
        # 1. Чанкинг
        if mode == "paragraph":
            chunks = self.chunker.chunk_by_paragraph()
        elif mode == "chapter":
            chunks = self.chunker.chunk_by_chapter()
        elif mode == "dense":
            # Dense mode: paragraph + chapter + sliding window for 2000+ chunks
            chunks = (
                self.chunker.chunk_by_paragraph()
                + self.chunker.chunk_by_chapter()
                + self.chunker.chunk_by_sliding_window(chunk_size=120, overlap=30)
            )
        else:
            chunks = self.chunker.chunk_hybrid()

        # 2. Обогащение
        enriched = self.enricher.enrich_chunks(chunks)

        # 3. Сохраняем enriched_chunks.json
        output_path = BASE / "KNOWLEDGE" / "enriched_chunks.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(enriched, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 4. Пакетная индексация в ChromaDB
        batch = []
        for chunk in enriched:
            metadata = {
                "chunk_id": chunk["id"],
                "chapter_id": chunk["chapter_id"],
                "chapter_title": chunk["chapter_title"],
                "chapter_number": str(chunk["chapter_number"]),
                "paragraph_id": chunk["paragraph_id"],
                "source": chunk.get("source", "book"),
                "themes": ",".join(chunk.get("enriched_themes", [])),
                "characters": ",".join(chunk.get("enriched_characters", [])),
                "symbols": ",".join(chunk.get("enriched_symbols", [])),
                "conflicts": ",".join(chunk.get("enriched_conflicts", [])),
                "values": ",".join(chunk.get("enriched_values", [])),
                "enrichment_count": str(chunk.get("enrichment_count", 0)),
            }
            batch.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": metadata,
            })
        self.retriever.batch_index(batch)

        # 5. Сохраняем enriched_catalog.json (для fallback-поиска)
        catalog = [
            {
                "id": c["id"],
                "text": c["text"][:300],
                "chapter_title": c["chapter_title"],
                "themes": c.get("enriched_themes", []),
                "characters": c.get("enriched_characters", []),
                "symbols": c.get("enriched_symbols", []),
            }
            for c in enriched
        ]
        catalog_path = BASE / "KNOWLEDGE" / "enriched_catalog.json"
        catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        chunker_stats = self.chunker.get_stats()
        enricher_stats = self.enricher.get_genome_stats()
        chroma_stats = self.retriever.get_collection_stats()

        return {
            "mode": mode,
            "chunks_total": len(enriched),
            "chunks_indexed": chroma_stats.get("count", 0) or len(batch),
            "enriched_themes": sum(1 for c in enriched if c.get("enriched_themes")),
            "enriched_characters": sum(1 for c in enriched if c.get("enriched_characters")),
            "enriched_symbols": sum(1 for c in enriched if c.get("enriched_symbols")),
            "chunker": chunker_stats,
            "enricher": enricher_stats,
            "chroma": chroma_stats,
            "status": "ok",
        }

    def clean_book(self) -> Dict:
        """
        Очищает исходный текст книги (КНИГА.md) от артефактов OCR/PDF.
        И перестраивает BOOK_DOCUMENT.json и BOOK_PROFILE.json.
        """
        from book_reader import read_book, build_document, build_profile, save

        raw = read_book()
        cleaned = self.cleaner.clean(raw)
        cleaner_stats = self.cleaner.get_stats(raw, cleaned)

        doc = build_document(cleaned)
        profile = build_profile(doc)

        knowledge_dir = BASE / "KNOWLEDGE"
        save(doc, knowledge_dir / "BOOK_DOCUMENT.json")
        save(profile, knowledge_dir / "BOOK_PROFILE.json")

        # Очищаем enriched_chunks если есть
        ec_path = BASE / "KNOWLEDGE" / "enriched_chunks.json"
        if ec_path.exists():
            ec_path.unlink()

        cleaner_stats["document_rebuilt"] = True
        return cleaner_stats

    def resolve_name(self, name: str) -> str:
        """Нормализует имя через NameResolver."""
        return self.nameresolver.resolve(name)

    def expand_query(self, query: str) -> str:
        """
        Расширяет поисковый запрос всеми алиасами.
        Пример: 'Велик' -> 'Велик Велиусмус Великосвет Велом'
        """
        parts = []
        for w in query.split():
            aliases = self.nameresolver.expand_query(w)
            parts.extend(aliases)
        return " ".join(sorted(set(parts), key=len, reverse=True))

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Поиск с расширением запроса через NameResolver."""
        expanded = self.expand_query(query)
        return self.retriever.search(expanded, n_results=n_results)

    async def search_from_chatpdf(self, query: str, source_id: Optional[str] = None) -> Optional[str]:
        """
        Поиск через ChatPDF (асинхронно).
        """
        if not self.chatpdf:
            return None
        try:
            from chatpdf_client import async_ask
            import httpx
            sid = source_id
            if not sid:
                return None
            async with httpx.AsyncClient(timeout=120.0) as client:
                result = await async_ask(client, sid, query)
                return result.get("content", "")
        except Exception as e:
            return f"[ChatPDF error: {e}]"

    def get_enriched_catalog(self, limit: int = 10) -> List[Dict]:
        """
        Возвращает enriched_catalog для отладки/просмотра.
        """
        catalog_path = BASE / "KNOWLEDGE" / "enriched_catalog.json"
        if catalog_path.exists():
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            return catalog[:limit]
        return []


    def get_civilization_profile(self, name: str) -> dict | None:
        """Return deep LLM-extracted civilization profile."""
        cp = self._load_civ_profiles()
        if not cp:
            return None
        name_lower = name.lower()
        for key, civ in cp.items():
            if name_lower == key:
                return civ.get("profile", civ)
            for alias in civ.get("aliases", []):
                if name_lower == alias.lower():
                    return civ.get("profile", civ)
            civ_name = civ.get("profile", {}).get("civilization_name", "").lower()
            if name_lower in civ_name:
                return civ.get("profile", civ)
        return None

    def get_all_civilizations(self) -> dict:
        """Return all civilization profiles as dict."""
        return self._load_civ_profiles()

    def _load_civ_profiles(self) -> dict:
        """Load civilization profiles from JSON."""
        if self._civ_profiles is not None:
            return self._civ_profiles
        cp_path = BASE / "KNOWLEDGE" / "civilization_profiles.json"
        if not cp_path.exists():
            self._civ_profiles = {}
            return self._civ_profiles
        try:
            with open(str(cp_path), "r", encoding="utf-8") as f:
                data = json.load(f)
            self._civ_profiles = data.get("civilizations", {})
        except Exception as e:
            logger.warning("Failed to load civ profiles: %s", e)
            self._civ_profiles = {}
        return self._civ_profiles

    def get_deep_character_profile(self, name: str) -> dict | None:
        """Return deep LLM-extracted character profile for a character."""
        dp = self._load_deep_profiles()
        if not dp:
            return None
        canonical = self.nameresolver.resolve(name)
        profile = dp.get(canonical)
        if profile:
            return profile
        for cname, p in dp.items():
            if name.lower() in cname.lower():
                return p
            for alias in p.get("aliases", []):
                if name.lower() in alias.lower():
                    return p
        return None

    def _load_deep_profiles(self) -> dict:
        """Load all deep character profiles from JSON."""
        if self._deep_profiles is not None:
            return self._deep_profiles
        dp_path = BASE / "KNOWLEDGE" / "character_deep_profiles.json"
        if not dp_path.exists():
            self._deep_profiles = {}
            return self._deep_profiles
        try:
            with open(str(dp_path), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._deep_profiles = {p["canonical_name"]: p for p in data if "canonical_name" in p}
            elif isinstance(data, dict):
                if "canonical_name" in data:
                    self._deep_profiles = {data["canonical_name"]: data}
                else:
                    self._deep_profiles = data
            else:
                self._deep_profiles = {}
        except Exception as e:
            logger.warning("Failed to load deep profiles: %s", e)
            self._deep_profiles = {}
        return self._deep_profiles

    def get_stats(self) -> Dict:
        return {
            "chunker": self.chunker.get_stats(),
            "enricher": self.enricher.get_genome_stats(),
            "chroma": self.retriever.get_collection_stats(),
            "nameresolver": self.nameresolver.get_stats(),
        }

    def index_screenplay(self) -> Dict:
        """Index screenplay scenes into ChromaDB."""
        sp_chunker = ScreenplayChunker()
        stats = sp_chunker.get_stats()
        if stats["status"] != "loaded":
            return {"status": "no_screenplay", "scenes": 0}

        scenes = sp_chunker.chunk_by_scene()
        batch = []
        for scene in scenes:
            metadata = {
                "chunk_id": scene["id"],
                "scene_id": scene.get("scene_id", ""),
                "scene_title": scene.get("scene_title", ""),
                "location": scene.get("location", ""),
                "scene_type": scene.get("scene_type", ""),
                "source": "screenplay",
            }
            batch.append({
                "id": scene["id"],
                "text": scene["text"],
                "metadata": metadata,
            })
        self.retriever.batch_index(batch)
        logger.info("screenplay_indexed scenes=%d", len(scenes))
        return {"status": "ok", "scenes": len(scenes)}