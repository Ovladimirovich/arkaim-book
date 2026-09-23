"""Relation Extractor — извлечение связей из WORLD_MODEL/*.json."""
from __future__ import annotations

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional

from .relation_models import (
    WorldRelation, RelationType, RelationGraph
)

log = logging.getLogger("hermes.relation_extractor")

WORLD_MODEL_DIR = Path(__file__).resolve().parent.parent / "WORLD_MODEL"


def _make_id(source: str, target: str, rel_type: str) -> str:
    """Создать детерминированный ID связи."""
    raw = f"{source}:{target}:{rel_type}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class RelationExtractor:
    """Извлекает связи из WORLD_MODEL/*.json."""
    
    def __init__(self, world_model_dir: Path | None = None):
        self._dir = world_model_dir or WORLD_MODEL_DIR
        self._graph = RelationGraph()
    
    def extract_all(self) -> RelationGraph:
        """Извлечь все связи из WORLD_MODEL."""
        self._extract_geography_relations()
        self._extract_civilization_relations()
        self._extract_technology_relations()
        self._extract_religion_relations()
        self._extract_mythology_relations()
        self._extract_character_relations()
        
        log.info("extraction_complete relations=%d", len(self._graph._relations))
        return self._graph
    
    def _load_json(self, filename: str) -> list[dict]:
        """Загрузить JSON-файл."""
        path = self._dir / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, list) else [data]
        except Exception as e:
            log.error("load_error file=%s: %s", filename, e)
            return []
    
    def _extract_geography_relations(self):
        """Извлечь географические связи."""
        regions = self._load_json("GEOGRAPHY.json")
        
        # Создаём связи между регионами на основе типов
        region_types = {}
        for region in regions:
            region_id = region.get("id", "")
            if not region_id:
                continue
            
            region_type = region.get("properties", {}).get("type", "unknown")
            if region_type not in region_types:
                region_types[region_type] = []
            region_types[region_type].append(region_id)
        
        # Связи между регионами одного типа
        for region_type, region_ids in region_types.items():
            for i, id1 in enumerate(region_ids):
                for id2 in region_ids[i+1:]:
                    self._graph.add_relation(WorldRelation(
                        id=_make_id(id1, id2, "geographic_same_type"),
                        source_id=id1,
                        target_id=id2,
                        relation_type=RelationType.GEOGRAPHIC,
                        description=f"Регионы одного типа: {region_type}",
                        strength=0.5,
                        bidirectional=True,
                    ))
        
        # Связи регионов с эпохами
        for region in regions:
            region_id = region.get("id", "")
            era = region.get("properties", {}).get("era", "")
            if region_id and era:
                self._graph.add_relation(WorldRelation(
                    id=_make_id(region_id, f"era_{era}", "historical_geo"),
                    source_id=region_id,
                    target_id=f"era_{era}",
                    relation_type=RelationType.HISTORICAL,
                    description=f"Регион существовал в эпоху {era}",
                    strength=0.8,
                ))
    
    def _extract_civilization_relations(self):
        """Извлечь связи цивилизаций."""
        civs = self._load_json("CIVILIZATIONS.json")
        
        for civ in civs:
            civ_id = civ.get("id", "")
            if not civ_id:
                continue
            
            # Связи с эпохой
            props = civ.get("properties", {})
            if isinstance(props, dict):
                epoch = props.get("epoch", "")
                if epoch:
                    self._graph.add_relation(WorldRelation(
                        id=_make_id(civ_id, f"era_{epoch}", "historical_civ"),
                        source_id=civ_id,
                        target_id=f"era_{epoch}",
                        relation_type=RelationType.HISTORICAL,
                        description=f"Цивилизация существовала в эпоху {epoch}",
                        strength=0.9,
                    ))
    
    def _extract_technology_relations(self):
        """Извлечь связи технологий."""
        techs = self._load_json("TECHNOLOGIES.json")
        
        for tech in techs:
            tech_id = tech.get("id", "")
            if not tech_id:
                continue
            
            # Связи с эпохой
            props = tech.get("properties", {})
            if isinstance(props, dict):
                epoch = props.get("epoch_first", "")
                if epoch:
                    self._graph.add_relation(WorldRelation(
                        id=_make_id(tech_id, f"era_{epoch}", "historical_tech"),
                        source_id=tech_id,
                        target_id=f"era_{epoch}",
                        relation_type=RelationType.HISTORICAL,
                        description=f"Технология появилась в эпоху {epoch}",
                        strength=0.9,
                    ))
    
    def _extract_religion_relations(self):
        """Извлечь религиозные связи."""
        religions = self._load_json("RELIGION.json")
        
        for rel in religions:
            rel_id = rel.get("id", "")
            if not rel_id:
                continue
            
            # Связи с эпохой
            props = rel.get("properties", {})
            if isinstance(props, dict):
                epoch = props.get("epoch", "")
                if epoch:
                    self._graph.add_relation(WorldRelation(
                        id=_make_id(rel_id, f"era_{epoch}", "historical_religion"),
                        source_id=rel_id,
                        target_id=f"era_{epoch}",
                        relation_type=RelationType.HISTORICAL,
                        description=f"Религия существовала в эпоху {epoch}",
                        strength=0.8,
                    ))
    
    def _extract_mythology_relations(self):
        """Извлечь мифологические связи."""
        myths = self._load_json("MYTHOLOGY.json")
        
        # Связи между мифами на основе общих тем
        for i, myth1 in enumerate(myths):
            myth1_id = myth1.get("id", "")
            if not myth1_id:
                continue
            
            desc1 = myth1.get("description", "").lower()
            
            for myth2 in myths[i+1:]:
                myth2_id = myth2.get("id", "")
                if not myth2_id:
                    continue
                
                desc2 = myth2.get("description", "").lower()
                
                # Проверяем общие темы
                common_themes = ["гиперборея", "атлантида", "аркаим", "катастрофа", 
                                "пробуждение", "духовн", "символ", "ритуал"]
                for theme in common_themes:
                    if theme in desc1 and theme in desc2:
                        self._graph.add_relation(WorldRelation(
                            id=_make_id(myth1_id, myth2_id, "mythological_theme"),
                            source_id=myth1_id,
                            target_id=myth2_id,
                            relation_type=RelationType.MYTHOLOGICAL,
                            description=f"Общая тема: {theme}",
                            strength=0.6,
                            bidirectional=True,
                        ))
                        break
    
    def _extract_character_relations(self):
        """Извлечь связи персонажей (из KNOWLEDGE)."""
        knowledge_dir = self._dir.parent.parent / "KNOWLEDGE"
        chars_path = knowledge_dir / "CHARACTERS.json"
        
        if not chars_path.exists():
            return
        
        try:
            data = json.loads(chars_path.read_text(encoding="utf-8-sig"))
            characters = data.get("characters", data) if isinstance(data, dict) else data
            
            if not isinstance(characters, list):
                return
            
            for char in characters:
                if not isinstance(char, dict):
                    continue
                
                char_name = char.get("name", "")
                char_id = f"char_{char_name.lower().replace(' ', '_')}"
                
                # Связи персонажей
                for other in characters:
                    if not isinstance(other, dict) or other.get("name") == char_name:
                        continue
                    
                    other_name = other.get("name", "")
                    other_id = f"char_{other_name.lower().replace(' ', '_')}"
                    
                    # Если оба упоминаются в описании друг друга
                    char_desc = char.get("description", "")
                    other_desc = other.get("description", "")
                    
                    if other_name in char_desc:
                        self._graph.add_relation(WorldRelation(
                            id=_make_id(char_id, other_id, "historical_character"),
                            source_id=char_id,
                            target_id=other_id,
                            relation_type=RelationType.HISTORICAL,
                            description=f"{char_name} связан с {other_name}",
                            strength=0.7,
                            bidirectional=True,
                        ))
        except Exception as e:
            log.error("character_relations_error: %s", e)


# ── Фабрика ────────────────────────────────────────────────────

def extract_relations(world_model_dir: Path | None = None) -> RelationGraph:
    """Извлечь все связи и вернуть граф."""
    extractor = RelationExtractor(world_model_dir)
    return extractor.extract_all()



