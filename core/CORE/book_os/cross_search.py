"""Cross-document Search — поиск по нескольким документам с группировкой.

Отличается от обычного search_chunks тем, что:
1. Результаты группируются по doc_id
2. Для каждого документа показывается топ-N чанков
3. Добавляется сводка: сколько чанков/документов нашлось
4. Поддерживает фильтр по конкретным документам
"""

from typing import Dict, List, Optional

from schemas.chunk import Chunk

# Максимум чанков на документ при группировке
DEFAULT_CHUNKS_PER_DOC = 3


class CrossDocumentResult:
    """Результат cross-document поиска."""

    def __init__(self, query: str, chunks: List[Chunk], chunks_per_doc: int = DEFAULT_CHUNKS_PER_DOC):
        self.query = query
        self.total_chunks = len(chunks)

        # Группируем по doc_id
        grouped: Dict[str, List[Chunk]] = {}
        for c in chunks:
            grouped.setdefault(c.doc_id, []).append(c)

        self.documents_matched = len(grouped)
        # Топ-N чанков на документ
        self.results: Dict[str, List[dict]] = {}
        for doc_id, doc_chunks in grouped.items():
            self.results[doc_id] = [
                {
                    "id": c.id,
                    "text": c.text[:300],
                    "position": c.position,
                    "score": float(c.metadata.get("_score", "0")) if c.metadata else 0.0,
                }
                for c in doc_chunks[:chunks_per_doc]
            ]

        # Сводка по каждому документу
        self.doc_summaries: Dict[str, dict] = {
            doc_id: {
                "doc_id": doc_id,
                "chunks_found": len(doc_chunks),
                "max_score": max(
                    (float(c.metadata.get("_score", "0")) if c.metadata else 0.0)
                    for c in doc_chunks
                ),
            }
            for doc_id, doc_chunks in grouped.items()
        }

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_chunks": self.total_chunks,
            "documents_matched": self.documents_matched,
            "doc_summaries": self.doc_summaries,
            "results": self.results,
        }


class CrossDocumentSearch:
    """Поиск по нескольким документам."""

    def __init__(self, index_engine, source_store=None):
        self.index_engine = index_engine
        self.source_store = source_store

    def search(self, query: str,
               doc_ids: Optional[List[str]] = None,
               n_results: int = 20,
               chunks_per_doc: int = DEFAULT_CHUNKS_PER_DOC) -> CrossDocumentResult:
        """Поиск с группировкой по документам.

        Args:
            query: поисковый запрос
            doc_ids: ограничить набор документов (None = все)
            n_results: общее количество чанков
            chunks_per_doc: максимум чанков на документ в результате

        Returns:
            CrossDocumentResult со сгруппированными результатами
        """
        chunks = self.index_engine.search(
            query=query,
            doc_ids=doc_ids,
            n_results=n_results,
        )
        return CrossDocumentResult(
            query=query,
            chunks=chunks,
            chunks_per_doc=chunks_per_doc,
        )

    def search_summary(self, query: str,
                       doc_ids: Optional[List[str]] = None,
                       n_results: int = 100) -> dict:
        """Быстрая сводка: только статистика, без текста чанков."""
        chunks = self.index_engine.search(
            query=query,
            doc_ids=doc_ids,
            n_results=n_results,
        )
        doc_chunks: Dict[str, int] = {}
        for c in chunks:
            doc_chunks[c.doc_id] = doc_chunks.get(c.doc_id, 0) + 1

        summaries = {}
        for doc_id, count in sorted(doc_chunks.items(), key=lambda x: -x[1]):
            doc_title = ""
            doc_type = ""
            if self.source_store:
                try:
                    doc = self.source_store.get(doc_id)
                    if doc:
                        doc_title = doc.title
                        doc_type = doc.type
                except Exception:
                    pass
            summaries[doc_id] = {
                "doc_id": doc_id,
                "title": doc_title,
                "type": doc_type,
                "chunks_found": count,
            }

        return {
            "query": query,
            "total_chunks": len(chunks),
            "documents_matched": len(summaries),
            "documents": list(summaries.values()),
        }
