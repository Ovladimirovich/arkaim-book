"""
WorldEngineLayer v2 — слой модели мира, интегрированный с WorldEngine.

Расширяет существующий WorldEngineLayer:
- Использует WorldEngine (406 сущностей, 287 связей)
- Поддерживает FormEngine для визуальных промптов
- Поддерживает ConsistencyEngine для проверки допустимости
"""
import json
import logging
from narrative_engine.source_levels import ProvenanceTag, ProvenanceCategory, SourceLevel
from typing import Optional, Any

from pulse.layers import BaseLayer, PulseResponse

log = logging.getLogger("hermes.pulse.world_engine_v2")


class WorldEngineLayerV2(BaseLayer):
    """
    Слой модели мира v2 — интегрирован с WorldEngine.
    
    Возможности:
    - Ответы на вопросы о мире (эпохи, локации, технологии, религии)
    - Визуальные промпты через FormEngine
    - Проверка консистентности через ConsistencyEngine
    - Режимы работы через ExperienceEngine
    """
    name = "world_engine_v2"

    def __init__(self, genome: dict, retriever=None):
        super().__init__(genome, retriever)
        self._world_engine = None
        self._init_world_engine()

    def _init_world_engine(self):
        """Инициализировать WorldEngine."""
        try:
            from narrative_engine.world_engine import WorldEngine
            self._world_engine = WorldEngine()
            self._world_engine.initialize()
            log.info("world_engine_v2_initialized %s", self._world_engine.summary())
        except Exception as e:
            log.error("world_engine_v2_init_error: %s", e)
            self._world_engine = None

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        """Ответить на запрос о мире."""
        if not self._world_engine:
            return None

        q = query.lower()
        
        # Ключевые слова для активации слоя
        world_keywords = [
            "эпоха", "эры", "где происходит", "кто жил", "что существовало",
            "какие технологии", "цивилизации", "кали юга", "сати юга",
            "сатья юга", "трета юга", "двапара юга", "гиперборея",
            "локации", "города", "страны", "события", "история мира",
            "религия", "философия", "мифология", "символы", "ритуалы",
            "архитектура", "ремёсла", "транспорт", "климат", "природа",
        ]
        
        if not any(kw in q for kw in world_keywords):
            return None

        # Ищем в WorldEngine
        results = self._world_engine.search(query)
        
        if results["total"] > 0:
            context = self._build_response(results)
            return PulseResponse(
                text=context,
                source="world_engine_v2",
                confidence=0.9,
                provenance=[ProvenanceTag(
                    source_level=SourceLevel.SYSTEM_INTERPRETATION,
                    category=ProvenanceCategory.DERIVED,
                    confidence=0.9,
                    notes=f"world engine search: {query[:50]}, {results['total']} results",
                )],
            )
        
        return None

    def _build_response(self, results: dict) -> str:
        """Построить ответ из результатов поиска."""
        parts = []
        
        # WorldModel результаты
        for item in results.get("world_model", [])[:5]:
            name = item.get("name", "")
            category = item.get("category", "")
            description = item.get("description", "")
            if name and description:
                parts.append(f"[{category}] {name}: {description[:200]}")
        
        # Результаты связей
        for rel in results.get("relations", [])[:3]:
            entity_id = rel.get("entity_id", "")
            outgoing = rel.get("outgoing_count", 0)
            incoming = rel.get("incoming_count", 0)
            if entity_id:
                parts.append(f"Связи: {entity_id} (исходящих: {outgoing}, входящих: {incoming})")
        
        return "\n\n".join(parts) if parts else ""

    def get_entity_context(self, entity_id: str) -> dict:
        """Получить контекст сущности."""
        if not self._world_engine:
            return {}
        return self._world_engine.get_entity_context(entity_id)

    def get_visual_prompt(self, entity_id: str, style: str = "cinematic") -> str:
        """Генерировать визуальный промпт."""
        if not self._world_engine or not self._world_engine._form_engine:
            return ""
        return self._world_engine._form_engine.generate_visual_prompt(entity_id, style)

    def validate_entity(self, entity: dict) -> dict:
        """Проверить сущность на консистентность."""
        if not self._world_engine or not self._world_engine._consistency_engine:
            return {"is_valid": True, "score": 1.0}
        report = self._world_engine._consistency_engine.validate_entity(entity)
        return {
            "is_valid": report.is_valid,
            "score": report.score,
            "violations": len(report.violations),
            "warnings": len(report.warnings),
        }

    def get_available_modes(self) -> list[dict]:
        """Получить доступные режимы работы."""
        if not self._world_engine or not self._world_engine._experience_engine:
            return []
        return self._world_engine._experience_engine.get_available_modes()

    @property
    def summary(self) -> str:
        """Текстовая сводка."""
        if not self._world_engine:
            return "Мир не загружен"
        return self._world_engine.summary()
