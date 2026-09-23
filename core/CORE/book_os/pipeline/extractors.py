"""EntityExtractor, FactExtractor, RelationshipExtractor.

Извлекают сущности, факты и связи из текста документа
с использованием существующих SemanticChunker и GenomeEnricher.
"""

from typing import Dict, List, Optional, Set

from schemas.entity import Entity
from schemas.fact import Fact
from schemas.relationship import Relationship


class EntityExtractor:
    """Извлекает сущности из enriched chunks."""

    @staticmethod
    def extract(chunks: List[Dict],
                existing_entities: Optional[Dict[str, Entity]] = None) -> List[Entity]:
        """Извлечь сущности из enriched chunks.

        Собирает уникальные сущности по именам из enriched_characters,
        enriched_themes, enriched_symbols chunks.
        """
        seen: Set[str] = set()
        entities = []

        type_map = {
            "characters": "person",
            "themes": "concept",
            "symbols": "symbol",
            "conflicts": "concept",
            "values": "concept",
        }

        for chunk in chunks:
            for field, etype in type_map.items():
                items = chunk.get(f"enriched_{field}", [])
                for item in items:
                    name = item if isinstance(item, str) else item.get("name", str(item))
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        entities.append(Entity(
                            name=name,
                            type=etype,
                            aliases=[name],
                            description="Извлечено из документа",
                        ))

        return entities

    @staticmethod
    def extract_from_text(text: str) -> List[Entity]:
        """Простое извлечение: возвращает пустой список.

        Полноценное извлечение из plain text — через LLM (будущее).
        """
        return []


class FactExtractor:
    """Извлекает факты из enriched chunks."""

    @staticmethod
    def extract(chunks: List[Dict],
                doc_id: str,
                entity_map: Dict[str, str]) -> List[Fact]:
        """Извлечь факты из enriched chunks.

        Каждый enriched chunk порождает факты:
        - Факт присутствия темы
        - Факт присутствия персонажа
        - Факт присутствия символа
        """
        facts = []
        seen = set()

        for chunk in chunks[:500]:
            chunk_id = chunk.get("id", "")
            chunk.get("text", "")[:200]

            # Факты о персонажах
            for char_name in chunk.get("enriched_characters", []):
                key = f"{char_name}|упоминается|{chunk.get('chapter_id', '')}"
                if key not in seen:
                    seen.add(key)
                    entity_id = entity_map.get(char_name.lower(), "")
                    if entity_id:
                        facts.append(Fact(
                            statement=f"{char_name} упоминается в главе "
                                      f"{chunk.get('chapter_title', '')}",
                            entity_id=entity_id,
                            doc_id=doc_id,
                            chunk_id=chunk_id,
                            provenance="source",
                            confidence=0.9,
                        ))

            # Факты о темах
            for theme_name in chunk.get("enriched_themes", []):
                key = f"{theme_name}|тема|{chunk.get('chapter_id', '')}"
                if key not in seen:
                    seen.add(key)
                    entity_id = entity_map.get(theme_name.lower(), "")
                    if entity_id:
                        facts.append(Fact(
                            statement=f"Тема '{theme_name}' раскрывается в "
                                      f"главе {chunk.get('chapter_title', '')}",
                            entity_id=entity_id,
                            doc_id=doc_id,
                            chunk_id=chunk_id,
                            provenance="source",
                            confidence=0.8,
                        ))

        return facts


class RelationshipExtractor:
    """Извлекает связи между сущностями из enriched chunks."""

    @staticmethod
    def extract(chunks: List[Dict],
                doc_id: str,
                entity_map: Dict[str, str]) -> List[Relationship]:
        """Извлечь связи: если в одном chunk упомянуты две entity — возможна связь."""
        relationships = []
        seen = set()

        for chunk in chunks:
            char_names = chunk.get("enriched_characters", [])
            if len(char_names) < 2:
                continue

            for i in range(len(char_names)):
                for j in range(i + 1, len(char_names)):
                    src_name = char_names[i]
                    tgt_name = char_names[j]
                    key = f"{src_name}|{tgt_name}" if src_name < tgt_name else f"{tgt_name}|{src_name}"
                    if key in seen:
                        continue
                    seen.add(key)

                    src_id = entity_map.get(src_name.lower(), "")
                    tgt_id = entity_map.get(tgt_name.lower(), "")
                    if not src_id or not tgt_id:
                        continue

                    relationships.append(Relationship(
                        source_id=src_id,
                        target_id=tgt_id,
                        type="friend",
                        doc_id=doc_id,
                        description=f"Совместное упоминание: {src_name} и {tgt_name}",
                        weight=0.5,
                    ))

        return relationships
