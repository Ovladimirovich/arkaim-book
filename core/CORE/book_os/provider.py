"""BookOSProvider — единый публичный контракт BOOK OS.

Объединяет Source Store, Knowledge Graph и Provenance Layer
в единый интерфейс для внешних клиентов.
"""

from pathlib import Path
from typing import Dict, List, Optional

from schemas.document import Document
from schemas.entity import Entity
from schemas.fact import Fact
from schemas.relationship import Relationship
from schemas.provenance import Provenance
from schemas.chunk import Chunk

from book_os.source_store import SourceStore
from book_os.entity_store import EntityStore
from book_os.fact_store import FactStore
from book_os.relationship_store import RelationshipStore
from book_os.provenance_tracker import ProvenanceTracker
from book_os.index_engine import IndexEngine
from book_os.hybrid_search import HybridSearchEngine
from book_os.cross_search import CrossDocumentSearch
from book_os.multimodal import process_multimodal, detect_file_type, get_available_extractors
from book_os.context import trace_context, TraceContext


class BookOSProvider:
    """Единый интерфейс BOOK OS.

    Принимает готовые экземпляры хранилищ (DI).
    Если хранилище не передано — создаёт со стандартным data_dir.
    """

    def __init__(
        self,
        source_store: Optional[SourceStore] = None,
        entity_store: Optional[EntityStore] = None,
        fact_store: Optional[FactStore] = None,
        relationship_store: Optional[RelationshipStore] = None,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        index_engine: Optional[IndexEngine] = None,
        data_dir: Optional[Path] = None,
    ):
        self.source_store = source_store or SourceStore(data_dir=data_dir)
        self.entity_store = entity_store or EntityStore(data_dir=data_dir)
        self.fact_store = fact_store or FactStore(data_dir=data_dir)
        self.relationship_store = relationship_store or RelationshipStore(data_dir=data_dir)
        self.provenance_tracker = provenance_tracker or ProvenanceTracker(data_dir=data_dir)
        self.index_engine = (index_engine or
                             IndexEngine(persist_dir=data_dir / "chroma" if data_dir else None))
        self.hybrid_engine = HybridSearchEngine(index_engine=self.index_engine)
        self.cross_engine = CrossDocumentSearch(
            index_engine=self.index_engine,
            source_store=self.source_store,
        )
        self._bm25_built = False
        # Прогрев клиента ChromaDB при старте
        self.index_engine.warmup()

    # ── Source Store ───────────────────────────────

    def get_document(self, doc_id: str) -> Document:
        """Вернуть документ по ID."""
        with trace_context("get_document"):
            return self.source_store.get(doc_id)

    def list_documents(self, doc_type: Optional[str] = None) -> List[Document]:
        """Список всех документов (с фильтром по типу)."""
        with trace_context("list_documents"):
            return self.source_store.list(doc_type=doc_type)

    def delete_document(self, doc_id: str) -> None:
        """Удалить документ и связанные provenance-записи."""
        with trace_context("delete_document"):
            self.source_store.delete(doc_id)
            self.provenance_tracker.delete_by_document(doc_id)

    # ── Knowledge Graph: Entity ────────────────────

    def get_entity(self, name: str) -> Entity:
        """Вернуть entity по каноническому имени (с разрешением алиасов)."""
        with trace_context("get_entity"):
            return self.entity_store.get(name)

    def search_entities(self, query: str,
                        entity_type: Optional[str] = None) -> List[Entity]:
        """Поиск entity по имени/алиасу."""
        with trace_context("search_entities"):
            return self.entity_store.search(query, entity_type=entity_type)

    def resolve_name(self, name: str) -> str:
        """Привести любое имя/алиас к канонической форме."""
        with trace_context("resolve_name"):
            return self.entity_store.resolve(name)

    # ── Knowledge Graph: Facts ──────────────────────

    def get_facts(self, entity_id: str,
                  provenance: Optional[str] = None) -> List[Fact]:
        """Все факты о сущности (с фильтром по provenance)."""
        with trace_context("get_facts"):
            return self.fact_store.get_by_entity(entity_id, provenance=provenance)

    def search_facts(self, statement: str) -> List[Fact]:
        """Поиск фактов по тексту утверждения."""
        with trace_context("search_facts"):
            return self.fact_store.search(statement)

    # ── Knowledge Graph: Relationships ─────────────

    def get_relationships(self, entity_id: str,
                          rel_type: Optional[str] = None) -> List[Relationship]:
        """Все связи entity (с фильтром по типу)."""
        with trace_context("get_relationships"):
            return self.relationship_store.get_by_entity(entity_id, rel_type=rel_type)

    # ── Provenance ─────────────────────────────────

    def get_provenance(self, fact_id: str) -> Provenance:
        """Вернуть происхождение факта."""
        with trace_context("get_provenance"):
            return self.provenance_tracker.get(fact_id)

    def verify_fact(self, fact_id: str) -> bool:
        """Проверить цепочку происхождения факта."""
        with trace_context("verify_fact"):
            return self.provenance_tracker.verify(fact_id, fact_store=self.fact_store)

    def get_fact_chain(self, fact_id: str) -> List[dict]:
        """Цепочка происхождения факта к source."""
        with trace_context("get_fact_chain"):
            return self.provenance_tracker.get_chain(fact_id, fact_store=self.fact_store)

    # ── Search / Chunks ────────────────────────────

    def search_chunks(self, query: str,
                      entity_ids: Optional[List[str]] = None,
                      provenance: Optional[str] = None,
                      doc_ids: Optional[List[str]] = None,
                      n_results: int = 5) -> List[Chunk]:
        """Векторный поиск по тексту через Index Engine."""
        with trace_context("search_chunks"):
            return self.index_engine.search(
                query, entity_ids=entity_ids,
                provenance=provenance, doc_ids=doc_ids,
                n_results=n_results,
            )

    # ── Ingestion ──────────────────────────────────

    def ingest_document(self, path: str) -> Dict:
        """Импортировать документ: полный цикл через Ingestion Pipeline."""
        with trace_context("ingest_document"):
            from book_os.pipeline.orchestrator import IngestionOrchestrator

            orchestrator = IngestionOrchestrator(
                source_store=self.source_store,
                entity_store=self.entity_store,
                fact_store=self.fact_store,
                relationship_store=self.relationship_store,
                provenance_tracker=self.provenance_tracker,
                index_engine=self.index_engine,
            )
            return orchestrator.ingest(Path(path))

    # ── Hybrid Search ──────────────────────────────

    def build_bm25_index(self) -> int:
        """Построить BM25 индекс из всех чанков ChromaDB."""
        if self.index_engine.count() == 0:
            return 0
        chunks = self.index_engine.search("", n_results=self.index_engine.count())
        if chunks:
            self.hybrid_engine.index_chunks(chunks)
            self._bm25_built = True
        return len(chunks)

    def hybrid_search(self, query: str,
                      entity_ids: Optional[List[str]] = None,
                      provenance: Optional[str] = None,
                      doc_ids: Optional[List[str]] = None,
                      n_results: int = 5,
                      keyword_weight: Optional[float] = None,
                      vector_weight: Optional[float] = None) -> List[Chunk]:
        """Гибридный поиск: BM25 + векторный с RRF."""
        if not self._bm25_built and self.index_engine.count() > 0:
            self.build_bm25_index()
        with trace_context("hybrid_search"):
            return self.hybrid_engine.search(
                query=query,
                entity_ids=entity_ids,
                provenance=provenance,
                doc_ids=doc_ids,
                n_results=n_results,
                keyword_weight=keyword_weight,
                vector_weight=vector_weight,
            )

    # ── Cross-document Search ─────────────────────

    def cross_document_search(self, query: str,
                              doc_ids: Optional[List[str]] = None,
                              n_results: int = 20,
                              chunks_per_doc: int = 3) -> dict:
        """Поиск по нескольким документам с группировкой."""
        with trace_context("cross_document_search"):
            return self.cross_engine.search(
                query=query, doc_ids=doc_ids,
                n_results=n_results, chunks_per_doc=chunks_per_doc,
            ).to_dict()

    def cross_search_summary(self, query: str,
                             doc_ids: Optional[List[str]] = None,
                             n_results: int = 100) -> dict:
        """Быстрая сводка: только статистика, без текста."""
        with trace_context("cross_search_summary"):
            return self.cross_engine.search_summary(
                query=query, doc_ids=doc_ids, n_results=n_results,
            )

    # ── Multi-modal ────────────────────────────────

    def ingest_multimodal(self, path: Path, doc_id: Optional[str] = None,
                          chunk_size: int = 2000) -> dict:
        """Извлечь текст и проиндексировать файл (PDF / image / audio).

        Returns:
            dict с {doc_id, chunks_created, indexed, format, source_file}
        """
        with trace_context("ingest_multimodal"):
            file_type = detect_file_type(path)
            if file_type is None:
                raise ValueError(f"Unsupported file type: {path.suffix}")

            chunks = process_multimodal(path, doc_id=doc_id, chunk_size=chunk_size)
            if not chunks:
                return {
                    "doc_id": doc_id,
                    "chunks_created": 0,
                    "indexed": False,
                    "format": file_type,
                    "source_file": path.name,
                    "error": f"No text extracted from {path.name}",
                }

            actual_doc_id = chunks[0].doc_id

            # Сохраняем документ
            doc = Document(
                doc_id=actual_doc_id,
                title=path.stem,
                source=file_type,
                metadata={"format": file_type, "source_file": path.name},
            )
            self.source_store.put(doc)

            # Индексируем чанки
            self.index_engine.index_chunks(chunks)

            return {
                "doc_id": actual_doc_id,
                "chunks_created": len(chunks),
                "indexed": True,
                "format": file_type,
                "source_file": path.name,
            }

    def get_multimodal_extractors(self) -> dict:
        """Какие экстракторы доступны в текущем окружении."""
        return get_available_extractors()

    # ── Stats ──────────────────────────────────────

    def get_stats(self) -> Dict:
        """Статистика всех хранилищ."""
        with trace_context("get_stats"):
            return {
                "source_store": self.source_store.get_stats(),
                "entity_store": self.entity_store.get_stats(),
                "fact_store": self.fact_store.get_stats(),
                "relationship_store": self.relationship_store.get_stats(),
                "provenance_tracker": self.provenance_tracker.get_stats(),
                "index_engine": self.index_engine.get_stats(),
                "hybrid_search": {
                    "bm25_count": self.hybrid_engine.count(),
                    "built": self._bm25_built,
                },
                "trace_id": TraceContext.get_trace_id(),
            }

    # ── Внутреннее ─────────────────────────────────

    @staticmethod
    def _find_all_positions(text: str, query: str) -> List[int]:
        """Найти все позиции вхождения query в text."""
        positions = []
        start = 0
        while True:
            pos = text.lower().find(query, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
