"""IndexEngine — векторный поиск по тексту через ChromaDB с фильтрацией.

Обёртка над существующей ChromaDB с поддержкой:
- Фильтрация по provenance, entity_ids, doc_ids
- Пакетная индексация Chunk-объектов с батчингом
- Возврат Chunk-моделей вместо сырых dict
- Retry с exponential backoff при сбоях ChromaDB
- LRU-кэш результатов поиска
- Warm-up для прогрева клиента
"""

import time
from pathlib import Path
from typing import Dict, List, Optional
from collections import OrderedDict

from schemas.chunk import Chunk

CHROMA_DIR = Path(__file__).resolve().parents[2] / "CHROMA_DB"

# Размер пачки для bulk insert в ChromaDB.
# Экспериментально: 50-100 — оптимально;
# больше — растёт вероятность timeout и замедление.
BATCH_SIZE = 100

# Retry parameters
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5  # seconds

# Cache: макс 256 запросов, TTL 60 секунд
CACHE_MAX_SIZE = 256
CACHE_TTL = 60.0


class IndexEngine:
    """Векторный поиск с фильтрацией.

    Хранит в metadata ChromaDB:
      - chunk_id, doc_id, provenance
      - entity_ids (строка, разделённая запятыми)
      - chapter_title, themes, characters, symbols
    """

    def __init__(self, persist_dir: Optional[Path] = None,
                 batch_size: int = BATCH_SIZE):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._collection = None
        self._client = None
        self._batch_size = batch_size
        # LRU-кэш: ключ = (query, frozenset(entity_ids), provenance, frozenset(doc_ids), n_results)
        self._search_cache = OrderedDict()

    # ── Индексация ───────────────────────────────

    def index_chunks(self, chunks: List[Chunk],
                     provenance: str = "source") -> int:
        """Пакетная индексация чанков в ChromaDB с разбивкой на батчи.

        Args:
            chunks: список Chunk-объектов
            provenance: метка происхождения для всех чанков

        Returns:
            количество проиндексированных чанков
        """
        if not chunks:
            return 0

        collection = self._get_collection()
        if collection is None:
            return 0

        total = 0
        # Разбиваем на пачки по _batch_size
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start:start + self._batch_size]
            documents, metadatas, ids = self._prepare_batch(batch, provenance)
            self._add_with_retry(collection, documents, metadatas, ids)
            total += len(ids)

        self._clear_cache()
        return total

    @staticmethod
    def _prepare_batch(chunks: List[Chunk],
                       provenance: str) -> tuple:
        """Подготовить три списка (documents, metadatas, ids) для ChromaDB."""
        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            meta = dict(chunk.metadata) if chunk.metadata else {}
            meta = {k: v for k, v in meta.items()
                    if not (isinstance(v, list) and not v)}
            meta["chunk_id"] = chunk.id
            meta["doc_id"] = chunk.doc_id
            meta["provenance"] = provenance

            entity_ids = meta.pop("entity_ids", [])
            if isinstance(entity_ids, list):
                meta["entity_ids"] = ",".join(entity_ids)

            documents.append(chunk.text)
            metadatas.append(meta)
            ids.append(chunk.id)

        return documents, metadatas, ids

    def _add_with_retry(self, collection, documents, metadatas, ids):
        """collection.add() с exponential backoff при ошибках."""
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
                return
            except Exception as e:
                last_exc = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    time.sleep(delay)
        raise RuntimeError(
            f"ChromaDB batch_index failed after {MAX_RETRIES} attempts: {last_exc}"
        )

    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Удалить чанки по ID с retry."""
        collection = self._get_collection()
        if collection is None or not chunk_ids:
            return
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                collection.delete(ids=chunk_ids)
                self._clear_cache()
                return
            except Exception:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))

    # ── Поиск ─────────────────────────────────────

    def search(self, query: str,
               entity_ids: Optional[List[str]] = None,
               provenance: Optional[str] = None,
               doc_ids: Optional[List[str]] = None,
               n_results: int = 5) -> List[Chunk]:
        """Векторный поиск с фильтрацией, retry и LRU-кэшем."""
        collection = self._get_collection()
        if collection is None:
            return []

        cache_key = self._cache_key(query, entity_ids, provenance, doc_ids, n_results)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        where_filter = self._build_filter(entity_ids, provenance, doc_ids)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter or None,
                )
                chunks = self._results_to_chunks(results)
                self._put_cache(cache_key, chunks)
                return chunks
            except Exception:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
        return []

    # ── Управление ────────────────────────────────

    def clear(self) -> None:
        """Очистить коллекцию."""
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete_collection("book_os_index")
        except Exception:
            pass
        self._collection = None
        self._clear_cache()

    def count(self) -> int:
        """Количество проиндексированных чанков."""
        collection = self._get_collection()
        if collection is None:
            return 0
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return collection.count()
            except Exception:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
        return 0

    def get_stats(self) -> Dict:
        """Статистика индекса."""
        return {"count": self.count(), "status": "ok" if self._get_collection() else "unavailable"}

    # ── Кэш ────────────────────────────────────────

    def _cache_key(self, query, entity_ids, provenance, doc_ids, n_results):
        key = (query, n_results)
        if entity_ids:
            key += (tuple(sorted(entity_ids)),)
        if provenance:
            key += (provenance,)
        if doc_ids:
            key += (tuple(sorted(doc_ids)),)
        return key

    def _get_from_cache(self, key):
        if key not in self._search_cache:
            return None
        result, ts = self._search_cache[key]
        if time.monotonic() - ts > CACHE_TTL:
            del self._search_cache[key]
            return None
        # LRU update: move to end
        self._search_cache.move_to_end(key)
        return result

    def _put_cache(self, key, value):
        self._search_cache[key] = (value, time.monotonic())
        if len(self._search_cache) > CACHE_MAX_SIZE:
            self._search_cache.popitem(last=False)

    def _clear_cache(self):
        self._search_cache.clear()

    # ── Warm-up ────────────────────────────────────

    def warmup(self) -> None:
        """Прогреть клиент и коллекцию до первого использования."""
        self._get_collection()
        self._client

    # ── Внутреннее ────────────────────────────────

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
            except ImportError:
                return None
        return self._client

    def _get_collection(self):
        client = self._get_client()
        if client is None:
            return None
        if self._collection is None:
            try:
                self._collection = client.get_or_create_collection("book_os_index")
            except Exception:
                return None
        return self._collection

    @staticmethod
    def _build_filter(entity_ids: Optional[List[str]] = None,
                      provenance: Optional[str] = None,
                      doc_ids: Optional[List[str]] = None) -> Optional[Dict]:
        """Построить ChromaDB where-фильтр."""
        conditions = []

        if provenance:
            conditions.append({"provenance": provenance})

        if doc_ids:
            if len(doc_ids) == 1:
                conditions.append({"doc_id": doc_ids[0]})
            else:
                conditions.append({"doc_id": {"$in": doc_ids}})

        if entity_ids:
            # ChromaDB $contains работает для строк
            for eid in entity_ids:
                conditions.append({"entity_ids": {"$contains": eid}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _results_to_chunks(results: Dict) -> List[Chunk]:
        """Преобразовать результат ChromaDB в список Chunk."""
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        n = len(documents)
        if n == 0:
            return []

        chunks = [None] * n
        for i, text in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            eid_str = meta.pop("entity_ids", "")
            if eid_str:
                meta["entity_ids"] = eid_str.split(",")
            score = str(1.0 - distances[i]) if i < len(distances) else "0.0"
            meta["_score"] = score
            chunks[i] = Chunk(
                id=meta.get("chunk_id", f"result_{i}"),
                doc_id=meta.get("doc_id", ""),
                text=text,
                position=i,
                metadata=meta,
            )
        return chunks
