"""
Retriever — RAG-поиск по тексту книги через ChromaDB.
Поддерживает enriched chunks с метаданными из генома.
"""

import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import partial
from time import time

from config import config
from llm_client import llm

CHROMA_DIR = config.CHROMA_DIR
GENOME_PATH = config.GENOME_DIR / "GENOME_v1.0.0.json"
CATALOG_PATH = config.KNOWLEDGE_DIR / "enriched_catalog.json"


class BookRetriever:
    def __init__(self, persist_dir: Optional[Path] = None, cache_ttl: int = 60):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._collection = None
        self._chroma_client = None
        self._genome = None
        self._cache_ttl = cache_ttl  # TTL кэша в секундах
        self._cache = {}  # Простой кэш: {query_hash: (timestamp, results)}
        self._catalog_cache: list | None = None  # Кэш enriched_catalog
        self._load_genome()

    def _load_genome(self):
        if GENOME_PATH.exists():
            self._genome = json.loads(GENOME_PATH.read_text(encoding="utf-8"))

    def _load_catalog(self) -> list:
        """Загрузить enriched_catalog.json с кэшированием в памяти."""
        if self._catalog_cache is not None:
            return self._catalog_cache
        if CATALOG_PATH.exists():
            try:
                self._catalog_cache = json.loads(CATALOG_PATH.read_bytes())
            except Exception:
                self._catalog_cache = []
        else:
            self._catalog_cache = []
        return self._catalog_cache

    def _get_cache_key(self, query: str, n_results: int) -> str:
        """Генерирует ключ кэша для запроса."""
        return f"{query}:{n_results}"

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Получает результаты из кэша если они не устарели."""
        if cache_key in self._cache:
            timestamp, results = self._cache[cache_key]
            if time() - timestamp < self._cache_ttl:
                return results
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, results: List[Dict]):
        """Сохраняет результаты в кэш."""
        # Ограничиваем размер кэша (максимум 256 записей)
        if len(self._cache) >= 256:
            # Удаляем самую старую запись
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        self._cache[cache_key] = (time(), results)

    def clear_cache(self):
        """Очищает кэш."""
        self._cache.clear()

    def _get_client(self):
        if self._chroma_client is None:
            try:
                import chromadb

                self._chroma_client = chromadb.PersistentClient(
                    path=str(self.persist_dir)
                )
            except ImportError:
                return None
        return self._chroma_client

    def _get_collection(self):
        client = self._get_client()
        if client is None:
            return None
        if self._collection is None:
            try:
                self._collection = client.get_collection("arkaim_book")
            except Exception:
                self._collection = client.create_collection("arkaim_book")
        return self._collection

    def clear_collection(self):
        """Очищает коллекцию для переиндексации."""
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete_collection("arkaim_book")
        except Exception:
            pass
        self._collection = None

    def count_source(self, source: str) -> int:
        """Сколько записей с данным source — проверка целостности индексации."""
        collection = self._get_collection()
        if collection is None:
            return 0
        try:
            result = collection.get(where={"source": source}, include=[])
            return len(result.get("ids", []))
        except Exception as e:
            print(f"[Retriever] count_source error: {e}")
            return 0

    def delete_source(self, source: str):
        """Удаляет записи одного source; остальные источники не затрагиваются."""
        collection = self._get_collection()
        if collection is None:
            return
        try:
            collection.delete(where={"source": source})
        except Exception as e:
            print(f"[Retriever] delete_source error: {e}")
            raise

    def index_chunk(self, chunk_id: str, text: str, metadata: Optional[Dict] = None):
        """
        Индексирует один chunk в ChromaDB.
        """
        collection = self._get_collection()
        if collection is None:
            return
        try:
            collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[chunk_id],
            )
        except Exception as e:
            print(f"[Retriever] index_chunk error: {e}")

    def batch_index(self, chunks: List[Dict]):
        """
        Пакетная индексация enriched chunks в ChromaDB (одним вызовом).
        Каждый chunk должен содержать: id, text, metadata (rest).
        """
        collection = self._get_collection()
        if collection is None:
            return
        documents = []
        metadatas = []
        ids = []
        for c in chunks:
            documents.append(c["text"])
            metadatas.append(c.get("metadata", {}))
            ids.append(c["id"])
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            print(f"[Retriever] batch_index error: {e}")

    def index_text(self, text: str, metadata: Optional[Dict] = None):
        """Оригинальный метод индексации (500/50 chars). Сохранён для совместимости."""
        collection = self._get_collection()
        if collection is None:
            return

        chunk_size = 500
        overlap = 50
        chunks = []
        metadatas = []
        ids = []

        # Загружаем существующие ID для дедупликации
        existing_ids = set()
        try:
            existing = collection.get(limit=100000)  # все документы
            existing_ids = set(existing.get("ids", []))
        except Exception:
            pass

        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i : i + chunk_size]
            if len(chunk.strip()) < 50:
                continue
            chunk_id = hashlib.md5(chunk.encode()).hexdigest()[:12]
            doc_id = f"chunk_{i}_{chunk_id}"
            if doc_id in existing_ids:
                continue
            chunks.append(chunk)
            meta = {"chunk_id": chunk_id, "start_pos": i, "source": "book"}
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)
            ids.append(doc_id)

        if not ids:
            return

        try:
            collection.add(documents=chunks, metadatas=metadatas, ids=ids)
        except Exception as e:
            print(f"[Retriever] Index error: {e}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск по ChromaDB с enriched fallback и кэшированием."""
        cache_key = self._get_cache_key(query, n_results)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        collection = self._get_collection()
        if collection is None:
            results = self._enriched_fallback(query, n_results)
            self._set_cache(cache_key, results)
            return results

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            output = []
            for i, doc in enumerate(documents):
                meta = metadatas[i] if i < len(metadatas) else {}
                score = 1.0 - distances[i] if i < len(distances) else 0.0
                output.append(
                    {
                        "text": doc,
                        "metadata": meta,
                        "score": score,
                        "chunk_id": meta.get("chunk_id", meta.get("id", f"chroma_{i}")),
                        "chapter_title": meta.get("chapter_title", ""),
                        "chapter_number": meta.get("chapter_number", -1),
                        "paragraph_id": meta.get("paragraph_id", ""),
                        "char_start": meta.get("char_start", -1),
                        "char_end": meta.get("char_end", -1),
                        "source": meta.get("source", "book"),
                        "provenance_category": "AUTHOR_CANON",  # Book text is always canon
                        "themes": meta.get("themes", "").split(",")
                        if isinstance(meta.get("themes"), str)
                        else meta.get("themes", []),
                        "characters": meta.get("characters", "").split(",")
                        if isinstance(meta.get("characters"), str)
                        else meta.get("characters", []),
                        "symbols": meta.get("symbols", "").split(",")
                        if isinstance(meta.get("symbols"), str)
                        else meta.get("symbols", []),
                    }
                )
            self._set_cache(cache_key, output)
            return output
        except Exception:
            results = self._enriched_fallback(query, n_results)
            self._set_cache(cache_key, results)
            return results

    def _enriched_fallback(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Улучшенный fallback: поиск по enriched_catalog.json + геному.
        """
        results = []

        # Поиск по enriched_catalog.json (кэшированному)
        catalog = self._load_catalog()
        if catalog:
            query_lower = query.lower()
            for entry in catalog:
                text_lower = entry.get("text", "").lower()
                if any(
                    word in text_lower for word in query_lower.split() if len(word) > 3
                ):
                    results.append(
                        {
                            "text": entry["text"],
                            "metadata": {
                                "source": "catalog",
                                "chapter_title": entry.get("chapter_title", ""),
                            },
                            "score": 0.6,
                            "chunk_id": entry.get("id", entry.get("chunk_id", "")),
                            "chapter_title": entry.get("chapter_title", ""),
                            "chapter_number": entry.get("chapter_number", -1),
                            "source": "catalog",
                            "provenance_category": "AUTHOR_CANON",
                            "themes": entry.get("themes", []),
                            "characters": entry.get("characters", []),
                            "symbols": entry.get("symbols", []),
                        }
                    )

        # Дополнительный поиск по геному
        if self._genome and len(results) < n_results:
            m = self._genome.get("modules", {})
            query_lower = query.lower()
            words = [w for w in query_lower.split() if len(w) > 3]

            for theme in m.get("themes", []):
                if any(w in theme["name"].lower() for w in words):
                    results.append(
                        {
                            "text": f"Тема: {theme['name']} — {theme.get('description', '')}",
                            "metadata": {"source": "genome", "type": "theme"},
                            "score": 0.7,
                            "chunk_id": f"genome_theme_{theme.get('id', '')}",
                            "chapter_title": "",
                            "source": "genome",
                            "provenance_category": "AUTHOR_CANON",
                            "themes": [theme["name"]],
                            "characters": [],
                            "symbols": [],
                        }
                    )

            for char in m.get("characters", []):
                if any(w in char["name"].lower() for w in words):
                    results.append(
                        {
                            "text": f"Персонаж: {char['name']} ({char.get('archetype', '')}) — {char.get('description', '')}",
                            "metadata": {"source": "genome", "type": "character"},
                            "score": 0.8,
                            "chunk_id": f"genome_char_{char.get('id', '')}",
                            "chapter_title": "",
                            "source": "genome",
                            "provenance_category": "AUTHOR_CANON",
                            "themes": [],
                            "characters": [char["name"]],
                            "symbols": [],
                        }
                    )

        return results[:n_results]

    async def search_async(self, query: str, n_results: int = 5) -> List[Dict]:
        """Async-обёртка над search."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(self.search, query, n_results))

    async def rerank(
        self, query: str, candidates: List[Dict], top_n: int = 3
    ) -> List[Dict]:
        """LLM-реранжировка кандидатов. Отбирает top_n релевантных."""
        if not candidates:
            return []

        scored = []
        for c in candidates:
            text = c.get("text", "")[:500]
            prompt = (
                f"Запрос: {query}\n"
                f"Фрагмент: {text}\n\n"
                "Оцени релевантность фрагмента запросу от 0.0 до 1.0. "
                "Верни ТОЛЬКО число."
            )
            try:
                resp = await llm.chat(
                    [{"role": "user", "content": prompt}], model="GigaChat-Pro"
                )
                score = float(resp.strip())
                score = max(0.0, min(1.0, score))
            except Exception:
                score = c.get("score", 0.0)
            c["rerank_score"] = score
            scored.append(c)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_n]

    def get_collection_stats(self) -> dict:
        collection = self._get_collection()
        if collection is None:
            return {"count": 0, "status": "unavailable"}
        try:
            count = collection.count()
            return {"count": count, "status": "ok"}
        except Exception as e:
            return {"count": 0, "status": f"error: {e}"}
