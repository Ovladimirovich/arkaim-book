"""
ui_routes — Web UI для читателей. Jinja2 + HTMX, без сборок.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from auth.rbac import get_current_user, require_role
from core.adc_deps import get_keeper, get_event_logger

log = logging.getLogger("hermes.ui")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/_ui", tags=["Web UI"])


def configure_static(app):
    """Подключить статические файлы к приложению."""
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Страницы ─────────────────────────

@router.get("/book", response_class=HTMLResponse)
async def book_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("book.html", {"request": request, "active": "book"})




@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, user: dict = Depends(get_current_user), role=Depends(require_role("admin"))):
    return templates.TemplateResponse("admin.html", {"request": request, "active": "admin"})

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, user: dict = Depends(get_current_user), role_check=Depends(require_role("editor"))):
    return templates.TemplateResponse("upload.html", {"request": request, "active": "upload"})


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("about.html", {"request": request, "active": "about"})


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "active": "profile"})


@router.get("/visual-genome", response_class=HTMLResponse)
async def visual_genome_page(request: Request, user: dict = Depends(get_current_user), role_check=Depends(require_role("editor"))):
    """Страница редактора Visual Genome."""
    try:
        pulse = _get_pulse_from_import()
        genome = pulse.genome if pulse and pulse.is_loaded else {}
    except Exception:
        genome = {}

    modules = genome.get("modules", {})
    characters = modules.get("characters", [])
    loc_visuals = modules.get("location_visuals", [])
    world_entities = genome.get("world_entities", [])

    return templates.TemplateResponse("visual_genome.html", {
        "request": request,
        "active": "visual-genome",
        "characters": characters,
        "locations": loc_visuals,
        "world_entities": world_entities,
    })


@router.get("/crowdfunding", response_class=HTMLResponse)
async def crowdfunding_page(request: Request, user: dict = Depends(get_current_user)):
    """Страница краудфандинга."""
    return templates.TemplateResponse("crowdfunding.html", {
        "request": request,
        "active": "crowdfunding",
    })


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, user: dict = Depends(get_current_user)):
    """Страница истории вопросов."""
    return templates.TemplateResponse("history.html", {"request": request, "active": "history"})


def _get_pulse_from_import():
    """Импортировать Pulse без Depends (для шаблонов)."""
    import sys
    from pathlib import Path
    core_path = Path(__file__).resolve().parent.parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))
    from pulse.pulse import BookPulse
    from core.config import config
    pulse = BookPulse()
    pulse.load()
    return pulse


# ── HTMX чат ─────────────────────────

@router.post("/ask", response_class=HTMLResponse)
async def chat_ask(
    request: Request,
    question: str = Form(...),
    user: dict = Depends(get_current_user),
    keeper=Depends(get_keeper),
    event_logger=Depends(get_event_logger),
):
    result = await keeper.act({
        "question": question,
        "context": "",
        "reader_id": user.get("user_id", ""),
        "reader_name": user.get("display_name", "") or user.get("username", ""),
    })
    event_logger.log_event({
        "event_type": "ui_ask", "topic": question[:100],
        "user_sentiment": "neutral", "system_action": "keeper_response", "outcome": "ok",
    })

    from core.presence_manager import register_question
    register_question(question[:60], question, result.get("answer", ""))

    # WebSocket уведомление о новом вопросе
    from core.websocket import notify_new_question
    await notify_new_question(question, question[:60], user.get("user_id", ""))

    return templates.TemplateResponse("chat_message.html", {
        "request": request,
        "question": question,
        "answer": result.get("answer", ""),
        "source": result.get("source", ""),
        "llm_used": result.get("llm_used", False),
    })


# ── Redirect корня _ui ───────────────

@router.get("", response_class=HTMLResponse)
async def ui_root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/_ui/book")


__all__ = ["router", "configure_static"]
