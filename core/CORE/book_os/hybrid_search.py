"""Hybrid Search — комбинированный keyword (BM25) + vector (ChromaDB) поиск.

Алгоритм:
1. BM25: инвертированный индекс + IDF + TF нормализация
2. Vector: делегирует ChromaDB через IndexEngine
3. RRF (Reciprocal Rank Fusion): объединение результатов двух систем
4. Финальное ранжирование по комбинированному скору
"""

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from schemas.chunk import Chunk

# Веса для RRF
RRF_K = 60.0
DEFAULT_KEYWORD_WEIGHT = 0.3
DEFAULT_VECTOR_WEIGHT = 0.7


class BM25Index:
    """BM25 индекс на основе проиндексированных чанков.

    Строит инвертированный индекс из текстов чанков,
    вычисляет IDF для каждого термина, поддерживает
    поиск с ранжированием по BM25.
    """

    def __init__(self, avg_dl: float = 100.0, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_dl = avg_dl
        self._N = 0  # всего документов
        self._doc_lens: Dict[str, int] = {}  # chunk_id -> длина в словах
        self._inverted: Dict[str, Set[str]] = defaultdict(set)  # term -> set(chunk_id)
        self._doc_texts: Dict[str, str] = {}  # chunk_id -> text
        self._idf_cache: Dict[str, float] = {}
        self._dirty = True

    # ── Индексация ───────────────────────────────

    def index_chunks(self, chunks: List[Chunk]) -> None:
        """Добавить чанки в BM25 индекс."""
        for chunk in chunks:
            terms = self._tokenize(chunk.text)
            self._doc_lens[chunk.id] = len(terms)
            self._doc_texts[chunk.id] = chunk.text
            for term in set(terms):
                self._inverted[term].add(chunk.id)
        self._N = len(self._doc_lens)
        if self._N:
            total_len = sum(self._doc_lens.values())
            self.avg_dl = total_len / self._N
        self._dirty = True

    def remove(self, chunk_ids: List[str]) -> None:
        """Удалить чанки из индекса."""
        for cid in chunk_ids:
            self._doc_texts.pop(cid, None)
            doc_len = self._doc_lens.pop(cid, 0)
            if doc_len:
                for term, docs in list(self._inverted.items()):
                    docs.discard(cid)
                    if not docs:
                        del self._inverted[term]
        self._N = len(self._doc_lens)
        self._dirty = True

    def clear(self) -> None:
        """Очистить индекс."""
        self._inverted.clear()
        self._doc_lens.clear()
        self._doc_texts.clear()
        self._idf_cache.clear()
        self._N = 0
        self._dirty = True

    def count(self) -> int:
        return self._N

    # ── Поиск ────────────────────────────────────

    def search(self, query: str, n_results: int = 5) -> List[Tuple[str, float]]:
        """BM25 поиск: возвращает список (chunk_id, score)."""
        if self._N == 0:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # IDF для каждого термина запроса
        idf_weights = {}
        for term in query_terms:
            if term not in self._idf_cache or self._dirty:
                df = len(self._inverted.get(term, []))
                self._idf_cache[term] = self._idf(df)
            idf_weights[term] = self._idf_cache[term]

        # TF для каждого термина в каждом документе
        term_tf: Dict[str, Counter] = defaultdict(Counter)
        for term in query_terms:
            for doc_id in self._inverted.get(term, []):
                doc_terms = self._tokenize(self._doc_texts.get(doc_id, ""))
                tf = doc_terms.count(term) / max(len(doc_terms), 1)
                term_tf[doc_id][term] = tf

        # BM25 score
        scores: Dict[str, float] = {}
        for doc_id, tf_counter in term_tf.items():
            doc_len = self._doc_lens.get(doc_id, self.avg_dl)
            score = 0.0
            for term, tf in tf_counter.items():
                idf = idf_weights.get(term, 0)
                score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_dl))
            chunk_id = doc_id
            if chunk_id:
                scores[chunk_id] = score

        # Сортировка
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:n_results]

    # ── Внутреннее ───────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Токенизация: нижний регистр, только буквы."""
        text = text.lower()
        tokens = re.findall(r"[а-яёa-z]+", text)
        return tokens

    def _idf(self, df: int) -> float:
        """IDF = ln((N - df + 0.5) / (df + 0.5) + 1)."""
        if df == 0:
            return 0.0
        return math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)


class HybridSearchEngine:
    """Гибридный поиск: BM25 + векторный (ChromaDB)."""

    def __init__(self, index_engine=None,
                 keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
                 vector_weight: float = DEFAULT_VECTOR_WEIGHT):
        self.bm25 = BM25Index()
        self.index_engine = index_engine
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight

    # ── Индексация ───────────────────────────────

    def index_chunks(self, chunks: List[Chunk]) -> None:
        """Индексировать чанки в BM25 (ChromaDB через index_engine отдельно)."""
        self.bm25.index_chunks(chunks)

    def remove(self, chunk_ids: List[str]) -> None:
        """Удалить из BM25."""
        self.bm25.remove(chunk_ids)

    def clear(self) -> None:
        """Очистить BM25."""
        self.bm25.clear()

    def count(self) -> int:
        return self.bm25.count()

    # ── Поиск ────────────────────────────────────

    def search(self, query: str,
               entity_ids: Optional[List[str]] = None,
               provenance: Optional[str] = None,
               doc_ids: Optional[List[str]] = None,
               n_results: int = 5,
               keyword_weight: Optional[float] = None,
               vector_weight: Optional[float] = None) -> List[Chunk]:
        """Гибридный поиск: BM25 + ChromaDB с RRF.

        Returns:
            Список Chunk с metadata["hybrid_score"] = комбинированный скор
            и metadata["keyword_score"] / metadata["vector_score"].
        """
        kw = keyword_weight if keyword_weight is not None else self.keyword_weight
        vw = vector_weight if vector_weight is not None else self.vector_weight

        # 1. BM25 keyword search
        bm25_results = self.bm25.search(query, n_results=n_results * 2)
        bm25_ids = {cid for cid, _ in bm25_results}

        # 2. Vector search
        vector_chunks = []
        if self.index_engine:
            vector_chunks = self.index_engine.search(
                query=query,
                entity_ids=entity_ids,
                provenance=provenance,
                doc_ids=doc_ids,
                n_results=n_results * 2,
            )
        vector_ids = {c.id for c in vector_chunks}

        # 3. RRF merge
        all_ids = bm25_ids | vector_ids
        ranked = []

        # BM25 rank map
        bm25_rank = {cid: idx for idx, (cid, _) in enumerate(bm25_results)}
        # Vector rank map
        vector_rank = {c.id: idx for idx, c in enumerate(vector_chunks)}
        # Vector score map
        vector_scores = {}
        for c in vector_chunks:
            vs = c.metadata.get("_score", "0") if c.metadata else "0"
            try:
                vector_scores[c.id] = float(vs)
            except (ValueError, TypeError):
                vector_scores[c.id] = 0.0

        # BM25 score map
        bm25_scores = dict(bm25_results)

        for cid in all_ids:
            rrf_score = 0.0
            # RRF for BM25
            if cid in bm25_rank:
                rrf_score += kw / (RRF_K + bm25_rank[cid] + 1)
            # RRF for Vector
            if cid in vector_rank:
                rrf_score += vw / (RRF_K + vector_rank[cid] + 1)
            ranked.append((cid, rrf_score, bm25_scores.get(cid, 0.0), vector_scores.get(cid, 0.0)))

        ranked.sort(key=lambda x: -x[1])

        # 4. Собираем Chunk-результаты
        vector_map = {c.id: c for c in vector_chunks}
        results = []
        for cid, hybrid_score, kw_score, vec_score in ranked[:n_results]:
            # Берём из vector_chunks если есть, иначе создаём заглушку с текстом из BM25
            if cid in vector_map:
                chunk = vector_map[cid]
            else:
                chunk = Chunk(
                    id=cid,
                    doc_id="",
                    text=self.bm25._doc_texts.get(cid, ""),
                    position=0,
                    metadata={},
                )
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["hybrid_score"] = f"{hybrid_score:.4f}"
            chunk.metadata["keyword_score"] = f"{kw_score:.4f}"
            chunk.metadata["vector_score"] = f"{vec_score:.4f}"
            results.append(chunk)

        return results
