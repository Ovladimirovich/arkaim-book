"""FastAPI router для Evolution — эволюция книги."""
from fastapi import APIRouter, Depends, HTTPException

from auth.rbac import require_role
from core.adc_deps import get_pulse

router = APIRouter(prefix="/evolution", tags=["Evolution"])


@router.get("/status", dependencies=[Depends(require_role("reader"))])
async def evolution_status(pulse=Depends(get_pulse)):
    """Текущий статус эволюции: версия, иммутабельные слои."""
    ev = pulse.evolution
    return {
        "current_version": pulse.state.genome_version,
        "loaded_at": pulse.state.loaded_at.isoformat() if pulse.state.loaded_at else "",
        "snapshots": ev.get_stats(),
    }


@router.get("/diff", dependencies=[Depends(require_role("editor"))])
async def check_diff(pulse=Depends(get_pulse)):
    """Проверить, изменился ли файл генома."""
    diff = pulse.check_for_changes()
    if diff is None:
        return {"changed": False, "diff": None}
    return {"changed": True, "diff": diff.to_dict()}


@router.post("/evolve", dependencies=[Depends(require_role("admin"))])
async def evolve(pulse=Depends(get_pulse)):
    """Применить новый геном. Эволюционировать."""
    try:
        diff = pulse.evolve()
        return {"ok": True, "diff": diff.to_dict()}
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))


@router.post("/rollback/{version}", dependencies=[Depends(require_role("admin"))])
async def rollback(version: str, pulse=Depends(get_pulse)):
    """Откатить геном к указанной версии."""
    ok = pulse.rollback(version)
    if not ok:
        raise HTTPException(404, f"Версия {version} не найдена")
    return {"ok": True, "version": version}


@router.get("/versions", dependencies=[Depends(require_role("editor"))])
async def list_versions(pulse=Depends(get_pulse)):
    """Список всех версий генома."""
    return {"versions": [s.to_dict() for s in pulse.evolution.list_versions()]}
