"""
Pulse — живое ядро цифрового сознания книги.
Не шаблонные строки, а активные объекты, которые знают книгу.
"""
from .pulse import BookPulse, PulseState, PulseBeat, PulseResponse
from .layers import KnowledgeLayer, MeaningLayer, IdentityLayer, MissionLayer, BaseLayer, NarrativeArcLayer
from .voice import BookVoice, Utterance
from .evolution import EvolutionTracker, GenomeDiff, GenomeSnapshot

__all__ = [
    "BookPulse", "PulseState", "PulseBeat", "PulseResponse",
    "BaseLayer", "KnowledgeLayer", "MeaningLayer", "IdentityLayer", "MissionLayer", "NarrativeArcLayer",
    "BookVoice", "Utterance",
    "EvolutionTracker", "GenomeDiff", "GenomeSnapshot",
]
