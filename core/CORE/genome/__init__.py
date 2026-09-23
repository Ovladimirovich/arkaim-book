"""Genome module — извлечение и валидация генома книги."""
from .schema import BookGenome, BookGenomeProfile, NarrativeArc, Beat
from .validator import validate_genome, validate_genome_file
from .extractor import main as run_extractor

__all__ = [
    "BookGenome", "BookGenomeProfile",
    "NarrativeArc", "Beat",
    "validate_genome", "validate_genome_file", "run_extractor",
]
