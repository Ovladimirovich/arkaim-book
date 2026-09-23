"""
Knowledge Graph — графовый движок для связей сущностей мира книги.
Строит граф из EntityStore + RelationshipStore + FactStore + genome.
"""
from .graph_engine import GraphEngine
from .populate import populate_from_genome, populate_from_book_os
from . import api_routes
