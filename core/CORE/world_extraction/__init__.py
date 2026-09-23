"""World Extraction Pipeline — извлечение знаний о мире из книги."""
from .pipeline import WorldExtractionPipeline, create_world_pipeline
from .models import WorldKnowledge, ExtractionResult

__all__ = [
    "WorldExtractionPipeline",
    "create_world_pipeline",
    "WorldKnowledge",
    "ExtractionResult",
]
