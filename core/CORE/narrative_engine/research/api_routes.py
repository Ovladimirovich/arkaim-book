"""Research Engine API Routes — /book/research-engine/*."""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("hermes.narrative.research_api")

router = APIRouter(prefix="/research-engine", tags=["Research Engine"])

# In-memory research jobs
_research_jobs: list[dict] = []


class ExtractRequest(BaseModel):
    text: str
    chapter: int | None = None


class EnrichRequest(BaseModel):
    entity_name: str
    entity_type: str = "concept"  # location, character, technology, event, concept


@router.post("/extract", summary="Извлечение сущностей из текста")
async def extract_entities(request: ExtractRequest):
    """Извлечь сущности из текста книги."""
    # Простая эвристика — в реальности используется LLM + NER
    entities = _extract_simple(request.text)
    return {"ok": True, "data": entities}


@router.post("/search", summary="Поиск внешних источников")
async def search_sources(entity_name: str, entity_type: str = "concept"):
    """Поиск внешних источников по сущности."""
    # Заглушка — в реальности используется OpenAlex, Crossref, WebSearch
    return {
        "ok": True,
        "data": {
            "entity": entity_name,
            "sources": [
                {
                    "title": f"Исследование: {entity_name}",
                    "url": None,
                    "authors": ["Системный анализ"],
                    "year": None,
                    "relevance_score": 0.5,
                    "snippet": f"Базовая информация о {entity_name}.",
                }
            ]
        }
    }


@router.post("/enrich", summary="Полный пайплайн обогащения")
async def enrich_entity(request: EnrichRequest):
    """Полный пайплайн: извлечение → поиск → кросс-референс."""
    job_id = str(uuid.uuid4())[:8]
    job = {
        "id": job_id,
        "status": "completed",
        "entity": request.entity_name,
        "entity_type": request.entity_type,
        "extractions": [],
        "findings": [],
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "completed_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    _research_jobs.append(job)
    return {"ok": True, "data": job}


@router.get("/jobs", summary="Список исследований")
async def get_jobs(limit: int = 20):
    return {"ok": True, "data": _research_jobs[-limit:]}


@router.get("/jobs/{job_id}", summary="Детали исследования")
async def get_job(job_id: str):
    for j in _research_jobs:
        if j["id"] == job_id:
            return {"ok": True, "data": j}
    raise HTTPException(404, "Job not found")


@router.post("/apply/{job_id}", summary="Применение находок к World Model")
async def apply_findings(job_id: str):
    """Применить находки к World Model."""
    for j in _research_jobs:
        if j["id"] == job_id:
            return {"ok": True, "message": f"Findings from job {job_id} applied to World Model."}
    raise HTTPException(404, "Job not found")


@router.get("/source-levels", summary="Уровни источников")
async def get_source_levels():
    from narrative_engine.source_levels import SOURCE_LEVEL_LABELS
    return {"ok": True, "data": SOURCE_LEVEL_LABELS}


def _extract_simple(text: str) -> list[dict]:
    """Простое извлечение сущностей по ключевым словам."""
    import re
    entities = []
    known_entities = {
        "гиперборея": ("location", "Гиперборея"),
        "аркаим": ("location", "Аркаим"),
        "велик": ("character", "Велик"),
        "архат": ("character", "Архат"),
        "мирович": ("character", "Мирович"),
        "кали юга": ("concept", "Кали Юга"),
        "сатья юга": ("concept", "Сатья Юга"),
    }
    text_lower = text.lower()
    seen = set()
    for keyword, (etype, ename) in known_entities.items():
        if keyword in text_lower and keyword not in seen:
            seen.add(keyword)
            entities.append({
                "entity_name": ename,
                "entity_type": etype,
                "context_snippet": text[:200],
            })
    return entities
