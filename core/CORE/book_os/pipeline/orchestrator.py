"""IngestionOrchestrator — полный цикл приёма документа в BOOK OS.

Цепочка:
  1. Валидация документа
  2. Добавление в Source Store
  3. Чанкинг (SemanticChunker для BOOK_DOCUMENT, иначе построчный)
  4. Обогащение (GenomeEnricher)
  5. Извлечение Entity, Fact, Relationship
  6. Проверка конфликтов
  7. Сохранение в Knowledge Graph
  8. Регистрация provenance
  9. Отчёт
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("hermes.ingestion")

from schemas.provenance import Provenance

from schemas.chunk import Chunk as ChunkModel

from book_os.source_store import SourceStore
from book_os.entity_store import EntityStore
from book_os.fact_store import FactStore
from book_os.relationship_store import RelationshipStore
from book_os.provenance_tracker import ProvenanceTracker
from book_os.index_engine import IndexEngine
from book_os.pipeline.validators import DocumentValidator
from book_os.pipeline.extractors import EntityExtractor, FactExtractor, RelationshipExtractor
from book_os.pipeline.conflict_resolver import ConflictResolver

GENOME_PATH = Path(__file__).resolve().parents[3] / "GENOME" / "GENOME_v1.0.0.json"


class IngestionOrchestrator:
    """Оркестратор полного цикла ингеста документа."""

    def __init__(
        self,
        source_store: SourceStore,
        entity_store: EntityStore,
        fact_store: FactStore,
        relationship_store: RelationshipStore,
        provenance_tracker: ProvenanceTracker,
        index_engine: Optional[IndexEngine] = None,
    ):
        self.source_store = source_store
        self.entity_store = entity_store
        self.fact_store = fact_store
        self.relationship_store = relationship_store
        self.provenance_tracker = provenance_tracker
        self.index_engine = index_engine
        self.validator = DocumentValidator()
        self.entity_extractor = EntityExtractor()
        self.fact_extractor = FactExtractor()
        self.rel_extractor = RelationshipExtractor()
        self.conflict_resolver = ConflictResolver()

    def ingest(self, file_path: Path, doc_type: str = "primary_source",
               version: str = "1.0.0") -> Dict:
        """Полный цикл ингеста документа.

        Args:
            file_path: путь к файлу документа
            doc_type: тип документа (primary_source, secondary_source, external)
            version: версия документа

        Returns:
            dict с результатом: статус, document_id, количество сущностей/фактов/связей
        """
        # 1. Валидация
        ok, errors = self.validator.validate(file_path)
        if not ok:
            return {"status": "error", "errors": errors}

        # 1.5. Предобработка PDF → текст
        effective_path = file_path
        if file_path.suffix.lower() == ".pdf":
            effective_path = self._extract_pdf_text(file_path)
            if effective_path is None:
                return {"status": "error", "errors": ["Не удалось извлечь текст из PDF"]}

        # 2. Добавление в Source Store
        doc = self.source_store.add(effective_path, doc_type=doc_type, version=version)
        doc_id = doc.id

        text = effective_path.read_text(encoding="utf-8")

        # 3. Чанкинг
        chunks = self._chunk_text(text, file_path)
        if not chunks:
            return {"status": "error", "errors": ["Не удалось разбить документ на чанки"]}

        # 4. Обогащение геномом
        enriched = self._enrich_chunks(chunks)

        # 5. Извлечение сущностей
        existing = {e.name.lower(): e for e in self.entity_store.list()}
        entities = self.entity_extractor.extract(enriched, existing)
        entity_map = {}
        for entity in entities:
            saved = self.entity_store.add(entity)
            entity_map[entity.name.lower()] = saved.id

        # 6. Извлечение фактов
        facts = self.fact_extractor.extract(enriched, doc_id, entity_map)

        # 7. Проверка конфликтов
        existing_facts = self.fact_store.list()
        conflicts = self.conflict_resolver.check(facts, existing_facts)
        if self.conflict_resolver.has_high_severity_conflicts(conflicts):
            return {
                "status": "conflict",
                "document_id": doc_id,
                "conflicts": [c.to_dict() for c in conflicts],
            }

        # 8. Сохранение фактов
        for fact in facts:
            self.fact_store.add(fact)
            self.provenance_tracker.register(
                fact.id,
                Provenance(
                    fact_id=fact.id,
                    type=fact.provenance,
                    label=f"Извлечено из {file_path.name}",
                    doc_id=doc_id,
                    confidence=fact.confidence,
                ),
            )

        # 9. Индексация чанков в ChromaDB
        if self.index_engine:
            chunk_models = []
            for ec in enriched:
                entity_ids_for_chunk = [
                    e.lower() for e in ec.get("enriched_characters", [])
                ]
                meta = {
                    "chapter_id": ec.get("chapter_id", ""),
                    "chapter_title": ec.get("chapter_title", ""),
                    "entity_ids": entity_ids_for_chunk,
                }
                for k, v in [("themes", ec.get("enriched_themes", [])),
                             ("characters", ec.get("enriched_characters", [])),
                             ("symbols", ec.get("enriched_symbols", []))]:
                    if v:
                        meta[k] = v
                chunk_models.append(ChunkModel(
                    id=ec.get("id", ""),
                    doc_id=doc_id,
                    text=ec.get("text", "")[:2000],
                    position=0,
                    metadata=meta,
                ))
            indexed = self.index_engine.index_chunks(chunk_models, provenance="source")
        else:
            indexed = 0

        # 10. Извлечение и сохранение связей
        relationships = self.rel_extractor.extract(enriched, doc_id, entity_map)
        for rel in relationships:
            self.relationship_store.add(rel)

        return {
            "status": "ok",
            "document_id": doc_id,
            "title": doc.title,
            "hash": doc.hash,
            "chunks_count": len(enriched),
            "entities_added": len(entities),
            "facts_added": len(facts),
            "relationships_added": len(relationships),
            "chunks_indexed": indexed,
        }

    # ── Внутренние методы ─────────────────────

    def _extract_pdf_text(self, pdf_path: Path) -> Optional[Path]:
        """Извлечь текст из PDF во временный .txt файл."""
        try:
            from book_os.pipeline.pdf_extractor import extract_to_temp_txt
            return extract_to_temp_txt(pdf_path)
        except Exception as e:
            log.error("pdf_extract_failed error=%s", e)
            return None

    def _chunk_text(self, text: str, file_path: Path) -> List[Dict]:
        """Разбить текст на чанки.

        Для BOOK_DOCUMENT.json — использует SemanticChunker.
        Для остальных — построчное/поабзацное разбиение.
        """
        if file_path.suffix.lower() == ".json":
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "content" in data:
                    return self._chunk_via_semantic_chunker(data)
            except json.JSONDecodeError:
                pass

        return self._chunk_plain_text(text, file_path)

    def _chunk_via_semantic_chunker(self, data: dict) -> List[Dict]:
        """Чанкинг через существующий SemanticChunker (через импорт данных)."""
        try:
            from intelligence.chunker import SemanticChunker
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(data, f, ensure_ascii=False)
                tmp_path = f.name

            chunker = SemanticChunker(doc_path=Path(tmp_path))
            chunks = chunker.chunk_hybrid()
            Path(tmp_path).unlink(missing_ok=True)
            return chunks
        except Exception:
            return []

    def _chunk_plain_text(self, text: str, file_path: Path) -> List[Dict]:
        """Разбиение plain text/markdown на абзацы."""
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for i, para in enumerate(paragraphs):
            if len(para) < 20:
                continue
            chunk_id = hashlib.md5(para.encode()).hexdigest()[:12]
            chunks.append({
                "id": f"chunk_{i:04d}_{chunk_id}",
                "text": para,
                "chapter_id": f"ch_{i // 50:03d}",
                "chapter_title": file_path.stem,
                "chapter_number": i // 50,
                "paragraph_id": f"p_{i:04d}",
                "char_start": 0,
                "char_end": 0,
                "source": doc_type_hint(file_path),
            })

        return chunks

    def _enrich_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Обогатить чанки через GenomeEnricher."""
        try:
            from intelligence.enricher import GenomeEnricher
            from intelligence.nameresolver import NameResolver

            nr = NameResolver()
            enricher = GenomeEnricher(genome_path=GENOME_PATH, nameresolver=nr)
            return enricher.enrich_chunks(chunks)
        except Exception:
            for chunk in chunks:
                chunk.setdefault("enriched_themes", [])
                chunk.setdefault("enriched_characters", [])
                chunk.setdefault("enriched_symbols", [])
                chunk.setdefault("enriched_conflicts", [])
                chunk.setdefault("enriched_values", [])
                chunk["enrichment_count"] = 0
            return chunks


def doc_type_hint(file_path: Path) -> str:
    """Определить тип документа по расширению."""
    ext = file_path.suffix.lower()
    if ext == ".json":
        return "structured"
    if ext == ".md":
        return "markdown"
    return "text"
