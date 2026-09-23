"""FastAPI router РґР»СЏ BOOK OS endpoints."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from auth.rbac import require_role

from book_os.provider import BookOSProvider
from book_os.pipeline.orchestrator import IngestionOrchestrator
from book_os.exceptions import EntityNotFoundError, DocumentNotFoundError
from schemas.chunk import Chunk

router = APIRouter(prefix="/os", tags=["book_os"])

# Global provider вЂ” РёРЅРёС†РёР°Р»РёР·РёСЂСѓРµС‚СЃСЏ РїСЂРё СЃС‚Р°СЂС‚Рµ
_provider: Optional[BookOSProvider] = None


def init_provider(data_dir: Optional[Path] = None) -> BookOSProvider:
    global _provider
    if _provider is None:
        _provider = BookOSProvider(data_dir=data_dir)
    return _provider


def get_provider() -> BookOSProvider:
    if _provider is None:
        raise RuntimeError("BOOK OS Provider not initialized")
    return _provider


# в”Ђв”Ђ Request/Response models в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


class SearchRequest(BaseModel):
    query: str
    entity_ids: Optional[List[str]] = None
    provenance: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    n_results: int = 5


class StatsResponse(BaseModel):
    source_store: dict
    entity_store: dict
    fact_store: dict
    relationship_store: dict
    provenance_tracker: dict
    index_engine: dict
    trace_id: str


class FactResponse(BaseModel):
    id: str
    statement: str
    entity_id: str
    doc_id: str
    provenance: str
    confidence: float


# в”Ђв”Ђ Endpoints в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


@router.get("/stats", dependencies=[Depends(require_role("reader"))])
async def get_stats() -> StatsResponse:
    """РЎС‚Р°С‚РёСЃС‚РёРєР° РІСЃРµС… С…СЂР°РЅРёР»РёС‰ BOOK OS."""
    return get_provider().get_stats()  # type: ignore


@router.get("/documents", dependencies=[Depends(require_role("reader"))])
async def list_documents(doc_type: Optional[str] = None) -> List[dict]:
    """Список документов."""
    provider = get_provider()
    docs = provider.list_documents(doc_type=doc_type)
    result = []
    for d in docs:
        entry = d.model_dump()
        facts = provider.fact_store.get_by_document(d.id)
        entry["chunks_count"] = len(facts)
        result.append(entry)
    return result


@router.get("/documents/{doc_id}", dependencies=[Depends(require_role("reader"))])
async def get_document(doc_id: str) -> dict:
    """РџРѕР»СѓС‡РёС‚СЊ РґРѕРєСѓРјРµРЅС‚ РїРѕ ID."""
    try:
        doc = get_provider().get_document(doc_id)
        if doc is None:
            raise HTTPException(404, "Document not found")
        return doc.model_dump()
    except DocumentNotFoundError:
        raise HTTPException(404, "Document not found")


@router.delete("/documents/{doc_id}", dependencies=[Depends(require_role("editor"))])
async def delete_document(doc_id: str) -> dict:
    """Удалить документ из хранилища и связанных хранилищ."""
    try:
        get_provider().delete_document(doc_id)
        return {"deleted": doc_id}
    except DocumentNotFoundError:
        raise HTTPException(404, "Document not found")


@router.post("/documents/ingest", dependencies=[Depends(require_role("editor"))])
async def ingest_document(file: UploadFile = File(...)) -> dict:
    """Р—Р°РіСЂСѓР·РёС‚СЊ РґРѕРєСѓРјРµРЅС‚ РІ BOOK OS."""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    import tempfile
    suffix = Path(file.filename).suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        result = get_provider().ingest_document(str(tmp_path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return result


@router.post("/pipeline/ingest", dependencies=[Depends(require_role("editor"))])
async def pipeline_ingest(file: UploadFile = File(...), doc_type: str = "primary_source", version: str = "1.0.0") -> dict:
    """РџРѕР»РЅС‹Р№ РєРѕРЅРІРµР№РµСЂ: Р·Р°РіСЂСѓР·РєР° в†’ Source Store в†’ С‡Р°РЅРєРёРЅРі в†’ РёР·РІР»РµС‡РµРЅРёРµ в†’ Knowledge Graph в†’ ChromaDB.

    РџРѕСЃР»Рµ СѓСЃРїРµС€РЅРѕРіРѕ РёРЅРіРµСЃС‚Р° С‚СЂРёРіРіРµСЂРёС‚ Pulse.evolve(), С‡С‚РѕР±С‹ РєРЅРёРіР° "СѓР·РЅР°Р»Р°" РЅРѕРІС‹Р№ РјР°С‚РµСЂРёР°Р».
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")
    import tempfile
    suffix = Path(file.filename).suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        provider = get_provider()
        orchestrator = IngestionOrchestrator(
            source_store=provider.source_store,
            entity_store=provider.entity_store,
            fact_store=provider.fact_store,
            relationship_store=provider.relationship_store,
            provenance_tracker=provider.provenance_tracker,
            index_engine=provider.index_engine,
        )
        result = orchestrator.ingest(tmp_path, doc_type=doc_type, version=version)

        if result.get("status") == "ok":
            try:
                from core.pulse_manager import get_pulse
                pulse = get_pulse()
                if pulse and pulse.is_loaded:
                    pulse.evolve()
            except Exception:
                pass

        return result
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {e}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@router.get("/entities", dependencies=[Depends(require_role("reader"))])
async def search_entities(query: str = "",
                          entity_type: Optional[str] = None) -> List[dict]:
    """РџРѕРёСЃРє СЃСѓС‰РЅРѕСЃС‚РµР№."""
    entities = get_provider().search_entities(query, entity_type=entity_type)
    return [e.model_dump() for e in entities]


@router.get("/entities/{name}", dependencies=[Depends(require_role("reader"))])
async def get_entity(name: str) -> dict:
    """РџРѕР»СѓС‡РёС‚СЊ СЃСѓС‰РЅРѕСЃС‚СЊ РїРѕ РєР°РЅРѕРЅРёС‡РµСЃРєРѕРјСѓ РёРјРµРЅРё."""
    try:
        entity = get_provider().get_entity(name)
        if entity is None:
            raise HTTPException(404, "Entity not found")
        return entity.model_dump()
    except EntityNotFoundError:
        raise HTTPException(404, "Entity not found")


@router.get("/entities/{name}/resolve", dependencies=[Depends(require_role("reader"))])
async def resolve_name(name: str) -> dict:
    """РџСЂРёРІРµСЃС‚Рё РёРјСЏ/Р°Р»РёР°СЃ Рє РєР°РЅРѕРЅРёС‡РµСЃРєРѕР№ С„РѕСЂРјРµ."""
    canonical = get_provider().resolve_name(name)
    return {"name": name, "resolved": canonical}


@router.get("/facts", dependencies=[Depends(require_role("reader"))])
async def get_facts(entity_id: str,
                    provenance: Optional[str] = None) -> List[FactResponse]:
    """Р¤Р°РєС‚С‹ Рѕ СЃСѓС‰РЅРѕСЃС‚Рё."""
    facts = get_provider().get_facts(entity_id, provenance=provenance)
    return [FactResponse(
        id=f.id, statement=f.statement, entity_id=f.entity_id,
        doc_id=f.doc_id, provenance=f.provenance, confidence=f.confidence,
    ) for f in facts]


@router.get("/facts/search", dependencies=[Depends(require_role("reader"))])
async def search_facts(statement: str) -> List[FactResponse]:
    """РџРѕРёСЃРє С„Р°РєС‚РѕРІ РїРѕ С‚РµРєСЃС‚Сѓ."""
    facts = get_provider().search_facts(statement)
    return [FactResponse(
        id=f.id, statement=f.statement, entity_id=f.entity_id,
        doc_id=f.doc_id, provenance=f.provenance, confidence=f.confidence,
    ) for f in facts]


@router.get("/relationships", dependencies=[Depends(require_role("reader"))])
async def get_relationships(entity_id: str,
                            rel_type: Optional[str] = None) -> List[dict]:
    """РЎРІСЏР·Рё СЃСѓС‰РЅРѕСЃС‚Рё."""
    rels = get_provider().get_relationships(entity_id, rel_type=rel_type)
    return [r.model_dump() for r in rels]


@router.post("/search", dependencies=[Depends(require_role("reader"))])
async def search_chunks(req: SearchRequest) -> List[dict]:
    """Р’РµРєС‚РѕСЂРЅС‹Р№ РїРѕРёСЃРє РїРѕ С‚РµРєСЃС‚Сѓ СЃ С„РёР»СЊС‚СЂР°С†РёРµР№."""
    chunks = get_provider().search_chunks(
        query=req.query,
        entity_ids=req.entity_ids,
        provenance=req.provenance,
        doc_ids=req.doc_ids,
        n_results=req.n_results,
    )
    return [
        {
            "id": c.id,
            "doc_id": c.doc_id,
            "text": c.text[:300],
            "position": c.position,
            "metadata": {k: v for k, v in c.metadata.items()
                         if not k.startswith("_")} if c.metadata else {},
            "score": c.metadata.get("_score", "0") if c.metadata else "0",
        }
        for c in chunks
    ]


class IndexRequest(BaseModel):
    chunks: List[dict]
    provenance: str = "source"


@router.post("/index", dependencies=[Depends(require_role("editor"))])
async def index_chunks(req: IndexRequest) -> dict:
    """РџСЂРѕРёРЅРґРµРєСЃРёСЂРѕРІР°С‚СЊ С‡Р°РЅРєРё РІ ChromaDB."""
    chunk_models = []
    for item in req.chunks:
        chunk_models.append(Chunk(
            id=item.get("id", ""),
            doc_id=item.get("doc_id", ""),
            text=item.get("text", ""),
            position=item.get("position", 0),
            metadata=item.get("metadata", {}),
        ))
    count = get_provider().index_engine.index_chunks(chunk_models, provenance=req.provenance)
    return {"indexed": count}


class DeleteRequest(BaseModel):
    chunk_ids: List[str]


@router.delete("/chunks", dependencies=[Depends(require_role("editor"))])
async def delete_chunks(req: DeleteRequest) -> dict:
    """РЈРґР°Р»РёС‚СЊ С‡Р°РЅРєРё РїРѕ ID."""
    get_provider().index_engine.delete_chunks(req.chunk_ids)
    return {"deleted": len(req.chunk_ids)}


@router.post("/cross-search", dependencies=[Depends(require_role("reader"))])
async def cross_search(req: SearchRequest) -> dict:
    """РџРѕРёСЃРє РїРѕ РЅРµСЃРєРѕР»СЊРєРёРј РґРѕРєСѓРјРµРЅС‚Р°Рј СЃ РіСЂСѓРїРїРёСЂРѕРІРєРѕР№."""
    return get_provider().cross_document_search(
        query=req.query,
        doc_ids=req.doc_ids,
        n_results=req.n_results * 4,
    )


@router.get("/cross-search/summary", dependencies=[Depends(require_role("reader"))])
async def cross_search_summary(query: str, doc_ids: Optional[str] = None) -> dict:
    """РЎРІРѕРґРєР° РїРѕРёСЃРєР° РїРѕ РґРѕРєСѓРјРµРЅС‚Р°Рј (С‚РѕР»СЊРєРѕ СЃС‚Р°С‚РёСЃС‚РёРєР°)."""
    doc_id_list = doc_ids.split(",") if doc_ids else None
    return get_provider().cross_search_summary(query=query, doc_ids=doc_id_list)


@router.post("/hybrid-search", dependencies=[Depends(require_role("reader"))])
async def hybrid_search(req: SearchRequest) -> List[dict]:
    """Р“РёР±СЂРёРґРЅС‹Р№ РїРѕРёСЃРє: BM25 keyword + РІРµРєС‚РѕСЂРЅС‹Р№ ChromaDB."""
    chunks = get_provider().hybrid_search(
        query=req.query,
        entity_ids=req.entity_ids,
        provenance=req.provenance,
        doc_ids=req.doc_ids,
        n_results=req.n_results,
    )
    return [
        {
            "id": c.id,
            "doc_id": c.doc_id,
            "text": c.text[:300],
            "position": c.position,
            "metadata": {k: v for k, v in c.metadata.items()
                         if not k.startswith("_")} if c.metadata else {},
            "scores": {
                "hybrid": c.metadata.get("hybrid_score", "0") if c.metadata else "0",
                "keyword": c.metadata.get("keyword_score", "0") if c.metadata else "0",
                "vector": c.metadata.get("vector_score", "0") if c.metadata else "0",
            },
        }
        for c in chunks
    ]


@router.post("/build-bm25", dependencies=[Depends(require_role("editor"))])
async def build_bm25() -> dict:
    """РџРѕСЃС‚СЂРѕРёС‚СЊ BM25 РёРЅРґРµРєСЃ РёР· С‡Р°РЅРєРѕРІ ChromaDB."""
    count = get_provider().build_bm25_index()
    return {"bm25_built": count}


@router.post("/clear", dependencies=[Depends(require_role("admin"))])
async def clear_index() -> dict:
    """РћС‡РёСЃС‚РёС‚СЊ РІРµРєС‚РѕСЂРЅС‹Р№ РёРЅРґРµРєСЃ (ChromaDB)."""
    get_provider().index_engine.clear()
    return {"status": "cleared"}




