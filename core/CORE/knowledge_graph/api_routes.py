"""FastAPI router для Knowledge Graph эндпоинтов."""
from fastapi import APIRouter, HTTPException

from knowledge_graph.graph_engine import GraphEngine

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


def _get_engine() -> GraphEngine:
    from core.adc_deps import get_graph_engine
    return get_graph_engine()


@router.get("/stats")
async def graph_stats():
    """Статистика графа: узлы, рёбра, типы."""
    engine = _get_engine()
    return engine.stats()


@router.get("/entity/{entity_id}/neighbors")
async def entity_neighbors(entity_id: str, depth: int = 1, rel_type: str | None = None):
    """Соседи сущности (BFS, depth=1 прямые связи)."""
    engine = _get_engine()
    return {"entity_id": entity_id, "neighbors": engine.get_neighbors(entity_id, rel_type=rel_type, max_depth=depth)}


@router.get("/path")
async def shortest_path(from_id: str, to_id: str):
    """Кратчайший путь между двумя сущностями."""
    engine = _get_engine()
    path = engine.shortest_path(from_id, to_id)
    if not path:
        raise HTTPException(404, "Путь не найден")
    return {"path": path}


@router.get("/subgraph")
async def subgraph(entity_ids: str, depth: int = 1):
    """Подграф вокруг заданных entity_ids (через запятую)."""
    engine = _get_engine()
    ids = [e.strip() for e in entity_ids.split(",") if e.strip()]
    return engine.subgraph(ids, depth=depth)


@router.get("/context/{entity_id}")
async def entity_context(entity_id: str):
    """Текстовый контекст сущности для RAG (с фактами и связями)."""
    engine = _get_engine()
    context = engine.context_for_entities([entity_id])
    return {"entity_id": entity_id, "context": context}


@router.post("/populate")
async def populate():
    """Заполнить граф из генома + BOOK OS."""
    from book_os.entity_store import EntityStore
    from book_os.relationship_store import RelationshipStore
    from book_os.fact_store import FactStore
    from knowledge_graph.populate import populate_from_genome, populate_from_book_os
    from core.services.registry import registry

    entity_store = EntityStore()
    rel_store = RelationshipStore()
    fact_store = FactStore()

    e1, r1, f1 = populate_from_genome(entity_store, rel_store, fact_store)
    e2, r2 = populate_from_book_os(entity_store, rel_store)

    engine = GraphEngine(entity_store, rel_store, fact_store)
    engine.build()

    # Replace the cached instance in registry
    registry._instances["graph_engine"] = engine

    return {
        "genome_added": {"entities": e1, "relationships": r1, "facts": f1},
        "book_os_existing": {"entities": e2, "relationships": r2},
    }
