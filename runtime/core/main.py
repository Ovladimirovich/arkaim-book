import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Добавляем CORE/ в sys.path (один раз при старте) ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # корень проекта
_CORE_DIR = _PROJECT_ROOT / "core" / "CORE"
if _CORE_DIR.exists() and str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response, RedirectResponse

from core.orchestrator import Orchestrator
from core.auth import verify_request
from aethon.xray import store as xray_store
from aethon.xray.version import VERSION, SPEC_VERSION, DTO_VERSION, EVENT_TAXONOMY_VERSION, API_VERSION
from aethon.xray.http_propagation import fastapi_extract_xray
from aethon.xray.manual_scenarios import run_scenario as xray_run_scenario
from aethon.xray.consistency_audit import run_all_audit_checks
from aethon.xray.control_plane.normalizer import (
    trace_to_summary,
    trace_to_detail,
    raw_stats_to_health_metrics,
    replay_entry_to_frame,
)
from core.logging import log
from core.provider_registry import ProviderRegistry
from core.providers.gigachat import GigaChatProvider
from core.providers.openrouter import OpenRouterProvider
from observability.metrics import metrics

# ── In-memory rate limiter ──────────────────────────────
_rate_limits: dict[str, list[float]] = {}
RATE_LIMIT_MAX_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit(client_id: str) -> bool:
    """Simple sliding window rate limiter."""
    now = time.time()
    if client_id not in _rate_limits:
        _rate_limits[client_id] = []
    # Remove old entries outside the window
    _rate_limits[client_id] = [t for t in _rate_limits[client_id] if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(_rate_limits[client_id]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limits[client_id].append(now)
    return True


def get_rate_limit_info(client_id: str) -> dict:
    now = time.time()
    requests = _rate_limits.get(client_id, [])
    requests = [t for t in requests if now - t < RATE_LIMIT_WINDOW_SECONDS]
    remaining = max(0, RATE_LIMIT_MAX_REQUESTS - len(requests))
    return {"rate": RATE_LIMIT_MAX_REQUESTS, "remaining": remaining}


_provider_rate_limits: dict[str, list[float]] = {}
PROVIDER_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("PROVIDER_RATE_LIMIT_MAX_REQUESTS", "30"))
PROVIDER_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("PROVIDER_RATE_LIMIT_WINDOW_SECONDS", "60"))


def check_provider_rate_limit(provider_name: str) -> bool:
    now = time.time()
    key = f"provider:{provider_name}"
    if key not in _provider_rate_limits:
        _provider_rate_limits[key] = []
    _provider_rate_limits[key] = [t for t in _provider_rate_limits[key] if now - t < PROVIDER_RATE_LIMIT_WINDOW_SECONDS]
    if len(_provider_rate_limits[key]) >= PROVIDER_RATE_LIMIT_MAX_REQUESTS:
        return False
    _provider_rate_limits[key].append(now)
    return True


def get_provider_rate_limit_info(provider_name: str) -> dict:
    now = time.time()
    key = f"provider:{provider_name}"
    requests = _provider_rate_limits.get(key, [])
    requests = [t for t in requests if now - t < PROVIDER_RATE_LIMIT_WINDOW_SECONDS]
    remaining = max(0, PROVIDER_RATE_LIMIT_MAX_REQUESTS - len(requests))
    return {"rate": PROVIDER_RATE_LIMIT_MAX_REQUESTS, "remaining": remaining}


# NOTE: gateway dependency intentionally avoided in core for contract tests
# from gateway.rate_limit import check_rate_limit, get_rate_limit_info
from shared_config import settings as shared
from core.analytics import analytics
from core.websocket import ws_endpoint

# Register and freeze providers at startup
ProviderRegistry.register("gigachat", GigaChatProvider)
ProviderRegistry.register("openrouter", OpenRouterProvider)
ProviderRegistry.freeze()

skills_path = os.getenv("HERMES_SKILLS_PATH") or os.getenv("BUSINESS_PACK") or ""
core = Orchestrator(business_pack=skills_path or None)


_TRACE_STORE_PATH = os.getenv("XRAY_TRACE_STORE_PATH", "")
_XRAY_MODE = os.getenv("XRAY_MODE", "live").strip()
_XRAY_SHADOW_MODE = os.getenv("XRAY_SHADOW_MODE", "").lower() in ("1", "true")


def _readonly_check():
    """Fail with 403 if XRAY_MODE=readonly and request is mutating."""
    if _XRAY_MODE == "readonly":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Read-only mode: mutation blocked")


from core.pulse_manager import init_pulse, pulse_beat

_RETRIEVER = None


def _init_retriever():
    global _RETRIEVER
    if _RETRIEVER is None:
        try:
            from intelligence.retriever import BookRetriever

            _RETRIEVER = BookRetriever()
        except Exception as e:
            log.warning("retriever_init_failed: %s", e)
            _RETRIEVER = None
    return _RETRIEVER


from skills.health_monitor import periodic_check

_health_check_task: asyncio.Task | None = None
_pulse_beat_task: asyncio.Task | None = None
_suggest_task: asyncio.Task | None = None
_email_task: asyncio.Task | None = None
_crowdfunding_task: asyncio.Task | None = None
_telegram_bot_task: asyncio.Task | None = None
_knowledge_task: asyncio.Task | None = None


# ── Pulse reference for email digest ──────────────────────
_pulse_ref = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_check_task, _pulse_beat_task
    global _suggest_task, _email_task, _pulse_ref, _crowdfunding_task, _telegram_bot_task, _knowledge_task

    # DatabaseManager — единое управление соединениями
    from core.database import get_db_manager, close_db_manager

    _db_manager = get_db_manager()
    log.info("database_manager_initialized")

    # Book OS — источник документов и Knowledge Graph
    try:
        from book_os.api_routes import init_provider as _init_book_os_provider

        _init_book_os_provider()
        log.info("book_os_provider_initialized")
    except Exception as e:
        log.error("book_os_provider_init_failed error=%s", e)

    # X-Ray
    if _TRACE_STORE_PATH:
        xray_store.configure_persistence(_TRACE_STORE_PATH)
        loaded = xray_store.stats.get("completed_traces", 0)
        log.info("xray_persistence_initialized path=%s loaded=%d", _TRACE_STORE_PATH, loaded)
    log.info("xray_mode mode=%s shadow=%s version=%s", _XRAY_MODE, _XRAY_SHADOW_MODE, VERSION)

    # Pulse — живое ядро книги
    retriever = _init_retriever()
    _pulse_ref = init_pulse(retriever=retriever)
    log.info("pulse_initialized")

    # Presence — книга наблюдает за сообществом
    from core.presence_manager import init_presence, periodic_suggest

    init_presence()
    log.info("presence_initialized")

    # Health monitor
    _health_check_task = asyncio.create_task(periodic_check())
    log.info("health_monitor_started")

    # Pulse regularly beats
    async def _beat_loop():
        while True:
            await asyncio.sleep(300)  # раз в 5 минут
            pulse_beat()

    _pulse_beat_task = asyncio.create_task(_beat_loop())

    # Presence suggests periodically
    async def _suggest_loop():
        while True:
            await asyncio.sleep(3600)  # раз в час
            await periodic_suggest()

    _suggest_task = asyncio.create_task(_suggest_loop())

    # Email weekly digest (каждую неделю)
    async def _email_digest_loop():
        from presence.email import SubscriberStore
        from presence.email_sender import send_weekly_digest, load_config

        load_config()  # перезагрузка конфигурации

        store = SubscriberStore()
        interval = int(os.getenv("EMAIL_DIGEST_INTERVAL", "604800"))  # 7 дней по умолчанию

        while True:
            try:
                await asyncio.sleep(interval)
                log.info("email_weekly_digest_scheduled")
                stats = await send_weekly_digest(store, _pulse_ref)
                log.info("email_weekly_digest_complete sent=%d errors=%d", stats.get("sent", 0), stats.get("errors", 0))
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("email_weekly_digest_error error=%s", e)
                await asyncio.sleep(60)  # ошибка — ждём минуту перед повтором

        await store.close()

    _email_task = asyncio.create_task(_email_digest_loop())
    log.info("email_digest_scheduled interval=%ds", int(os.getenv("EMAIL_DIGEST_INTERVAL", "604800")))

    # Crowdfunding monitoring
    async def _crowdfunding_check_loop():
        from community.crowdfunding import CrowdfundingMonitor, load_config as cf_load_config
        from core.websocket import notify_crowdfunding_milestone

        cfg = cf_load_config()
        if not cfg["enabled"]:
            log.info("crowdfunding_disabled")
            return

        monitor = CrowdfundingMonitor(
            campaigns_config=cfg["campaigns"],
            user_agent=cfg["user_agent"],
        )
        interval = cfg["check_interval"]

        while True:
            try:
                await asyncio.sleep(interval)
                log.info("crowdfunding_check_scheduled")
                _alerts = await monitor.check_all()

                # Проверяем майлстоуны
                for cid in monitor.campaigns:
                    milestone_alerts = monitor.check_milestones(cid)
                    for alert in milestone_alerts:
                        # WebSocket
                        await notify_crowdfunding_milestone(alert.to_dict())
                        log.info("crowdfunding_milestone_ws_sent %s", alert.to_dict())

                        # Telegram
                        if os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
                            try:
                                from community.telegram import TelegramBotStub

                                bot = TelegramBotStub()
                                await bot.send_notification(alert.telegram_message())
                                log.info("crowdfunding_milestone_telegram_sent %s", alert.campaign_id)
                            except Exception as e:
                                log.error("crowdfunding_telegram_error error=%s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("crowdfunding_check_error error=%s", e)
                await asyncio.sleep(60)

    _crowdfunding_task = asyncio.create_task(_crowdfunding_check_loop())
    log.info("crowdfunding_scheduled")

    # Telegram Bot — обработка /login
    from bot.telegram_bot import init_bot

    bot = init_bot()
    if bot:

        async def _bot_poll_loop():
            await bot.poll()

        _telegram_bot_task = asyncio.create_task(_bot_poll_loop())
        log.info("telegram_bot_started")

    # Knowledge Expansion Scheduler
    async def _knowledge_enrichment_loop():
        from knowledge_expansion.pipeline import create_default_pipeline
        from knowledge_expansion.scheduler import KnowledgeScheduler

        pipeline = create_default_pipeline()
        scheduler = KnowledgeScheduler(pipeline)
        interval = 3600  # 1 hour
        while True:
            try:
                await asyncio.sleep(interval)
                log.info("knowledge_expansion_check")
                await scheduler.check_and_run()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("knowledge_expansion_error error=%s", e)
                await asyncio.sleep(300)

    _knowledge_task = asyncio.create_task(_knowledge_enrichment_loop())
    log.info("knowledge_expansion_scheduled interval=3600s")

    # Generation queue removed (Arkaim Media Boundary — no local media execution).

    yield

    if _health_check_task:
        _health_check_task.cancel()
    if _pulse_beat_task:
        _pulse_beat_task.cancel()
    if _suggest_task:
        _suggest_task.cancel()
    if _email_task:
        _email_task.cancel()
    if _crowdfunding_task:
        _crowdfunding_task.cancel()
    if _telegram_bot_task:
        _telegram_bot_task.cancel()
    if _knowledge_task:
        _knowledge_task.cancel()
    # Close asset store
    from core.adc_deps import registry

    asset_store = registry.get("asset_store")
    await asset_store.close()
    log.info("health_monitor_stopped")
    log.info("core_shutdown")
    await core.close()
    from core.services.registry import registry

    registry.close_all()
    await close_db_manager()
    log.info("database_connections_closed")


app = FastAPI(
    title="Arkaim Digital Consciousness API",
    description="""
    API для Arkaim Digital Consciousness — цифровой системы исследования книги «Наследие Аркаима».

    ## Аутентификация

    Используйте один из способов:
    - **Bearer Token**: `Authorization: Bearer <token>` (JWT из OAuth)
    - **Cookie**: `arkaim_session=<token>` (устанавливается при входе через веб)
    - **API Key**: `Authorization: Bearer <api_key>` (персональный ключ)

    ## Основные возможности

    * **Book Intelligence**: Задавайте вопросы книге и получайте ответы с помощью AI
    * **Visual Genome**: Управление визуальными описаниями сцен и персонажей
    * **Reader Memory**: Профиль читателя и история взаимодействий
    * **X-Ray Observability**: Мониторинг и отладка системы

    ## Роли

    - `reader` — чтение, вопросы книге
    - `editor` — генерация контента, визуальный редактор
    - `admin` — полный доступ, управление пользователями
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Auth", "description": "Аутентификация и управление пользователями"},
        {"name": "Book Intelligence", "description": "Интеллект книги — вопросы, генерация, черновики"},
        {"name": "Visual Genome", "description": "Визуальные описания сцен, персонажей, локаций"},
        {"name": "Reader Memory", "description": "Профиль и память читателя"},
        {"name": "X-Ray", "description": "Мониторинг и трейсинг"},
    ],
    security=[{"BearerCookie": []}],
    openapi_security_schemes={
        "BearerCookie": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "JWT токен или API ключ. Формат: `Bearer <token>`",
        },
    },
)

# Middleware (вынесен в core/middleware.py)
from core.middleware import create_rate_limit_middleware, protected_routes_middleware

app.middleware("http")(create_rate_limit_middleware(check_rate_limit, get_rate_limit_info, analytics, shared))
app.middleware("http")(protected_routes_middleware)


# ── Глобальные обработчики ошибок ──────────────────────
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse as _JSONResponse


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    """Единый формат ошибок валидации (GO-2, 2026-10-11): envelope как у HTTPException."""
    errors = exc.errors()
    details = [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in errors
    ]
    message = details[0]["msg"] if details else "Ошибка валидации запроса"
    return _JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": {
                "code": "HTTP_422",
                "message": message,
                "details": details,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("unhandled_exception path=%s", request.url.path)
    return _JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Внутренняя ошибка сервера",
            },
        },
    )


# Web UI — Jinja2 + HTMX
from core.ui_routes import router as ui_router, configure_static

configure_static(app)
app.include_router(ui_router)

# Auth routes
from auth.routes import router as auth_router

app.include_router(auth_router)

# X-Ray dashboard (admin only, legacy)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_dashboard_path = Path(__file__).resolve().parent.parent / "xray_dashboard"
if _dashboard_path.exists():
    app.mount("/_ui/admin", StaticFiles(directory=str(_dashboard_path), html=True), name="dashboard")

# ── Root redirect ─────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    """Редирект на Web UI."""
    return RedirectResponse(url="/_ui/book")


# SEO: robots.txt и sitemap.xml
@app.get("/robots.txt")
async def robots_txt():
    """Возвращает robots.txt для поисковых систем."""
    robots_path = _dashboard_path / "robots.txt"
    if robots_path.exists():
        return FileResponse(robots_path)
    return Response(content="User-agent: *\nDisallow: /", media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap_xml():
    """Возвращает sitemap.xml для поисковых систем."""
    sitemap_path = _dashboard_path / "sitemap.xml"
    if sitemap_path.exists():
        return FileResponse(sitemap_path)
    return Response(content="", media_type="application/xml")


# Book Intelligence routes (merged from standalone :9090 API)
from core.book_routes import router as book_router

app.include_router(book_router)

# Studio routes (Phase 1B)
from core.routes.studio import router as studio_router

app.include_router(studio_router)

# Crowdfunding routes
from community.crowdfunding_api import router as crowdfunding_router

app.include_router(crowdfunding_router)

# Community routes (interpretations + artifacts)
from community.community_api import router as community_router

app.include_router(community_router)

# Knowledge Cards routes
from core.routes.knowledge_cards import router as knowledge_cards_router

app.include_router(knowledge_cards_router)

# World References routes (M3)
from core.routes.world_references import router as world_references_router

app.include_router(world_references_router)

# Temporal References routes (M4)
from core.routes.temporal_references import router as temporal_references_router

app.include_router(temporal_references_router)

# Conflicts routes (M5)
from core.routes.conflicts import router as conflicts_router

app.include_router(conflicts_router)

# Reasoning routes (M6)
from core.routes.reasoning import router as reasoning_router

app.include_router(reasoning_router)

# Corrections routes (M7)
from core.routes.corrections import router as corrections_router

app.include_router(corrections_router)

# WebSocket для real-time уведомлений дашборда
app.websocket("/ws")(ws_endpoint)


# Analytics endpoint (только агрегированные данные, без персональной информации)
@app.get("/analytics", tags=["Analytics"])
async def get_analytics():
    """
    Получить анонимную аналитику использования.

    Возвращает только агрегированные метрики без персональных данных.
    """
    return analytics.get_metrics()


@app.post("/v1/chat")
async def chat(request: Request):
    user = await verify_request(request)
    body = await request.json()
    xray_headers = fastapi_extract_xray(request)
    if xray_headers["trace_id"]:
        body["xray_headers"] = xray_headers
    result = await core.chat(body, user)
    return JSONResponse(result)


@app.post("/v1/stream")
async def stream(request: Request):
    user = await verify_request(request)
    body = await request.json()
    xray_headers = fastapi_extract_xray(request)
    if xray_headers["trace_id"]:
        body["xray_headers"] = xray_headers
    return StreamingResponse(core.stream(body, user), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": _XRAY_MODE,
        "trace_store": bool(_TRACE_STORE_PATH),
        "active_traces": xray_store.stats.get("active_traces", 0),
        "completed_traces": xray_store.stats.get("completed_traces", 0),
    }


@app.get("/provider/health")
async def provider_health():
    results = await core.provider_health()
    return {"status": "ok" if all(r.get("status") == "ok" for r in results) else "degraded", "providers": results}


@app.get("/memory/health")
async def memory_health():
    return await core.memory_health()


@app.get("/metrics")
async def get_metrics():
    return metrics.snapshot()


@app.get("/providers/health")
async def providers_health():
    health_results = await core.provider_health()
    models_results = await ProviderRegistry.list_all_models()
    providers = []
    for hr in health_results:
        name = hr.get("name", "unknown")
        pm = [m for m in models_results if m.get("provider") == name]
        providers.append({"name": name, "health": "ok" if hr.get("status") == "ok" else "error", "models": pm, "last_error": hr.get("error")})
    return {"status": "ok" if all(p["health"] == "ok" for p in providers) else "degraded", "providers": providers}


@app.get("/v1/models")
async def v1_list_models():
    models = await ProviderRegistry.list_all_models()
    result = [
        {
            "id": m.get("id", ""),
            "object": "model",
            "owned_by": m.get("owned_by", ""),
            "context_window": m.get("context_window"),
            "modalities": m.get("modalities"),
            "status": m.get("status"),
        }
        for m in models
    ]
    return {"object": "list", "data": result}


@app.post("/v1/chat/completions")
async def v1_chat_completions(request: Request):
    import uuid

    user = await verify_request(request)
    try:
        body = await request.json()
        model = body.get("model", "")
        messages = body.get("messages", [])
        n = body.get("n", 1)
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_REQUEST", "message": "Invalid request body"}})
    if n != 1:
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_PARAM", "message": "Only n=1 is supported"}})
    if "tools" in body or "function_call" in body:
        return JSONResponse(status_code=400, content={"error": {"code": "UNSUPPORTED_FEATURE", "message": "Tools/functions not supported in G0"}})
    if not messages:
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_REQUEST", "message": "messages is required"}})
    xray_headers = fastapi_extract_xray(request)
    if xray_headers["trace_id"]:
        body["xray_headers"] = xray_headers
    provider_name = model.split("/")[0] if "/" in model else model
    if not ProviderRegistry.is_registered(provider_name):
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_MODEL", "message": f"Provider '{provider_name}' not found"}})
    if not check_provider_rate_limit(provider_name):
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": f"Provider {provider_name} rate limit exceeded"}},
            headers={"X-RateLimit-Reset": str(PROVIDER_RATE_LIMIT_WINDOW_SECONDS)},
        )
    internal_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages if isinstance(m, dict)]
    internal_req = {"messages": internal_messages, "provider": provider_name, "metadata": {"session_id": user.get("user_id", "unknown")}}
    try:
        result = await core.chat(internal_req, user)
        if isinstance(result, dict) and "error" in result:
            return JSONResponse(status_code=500, content={"error": {"code": "PROVIDER_ERROR", "message": result["error"]}})
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result["choices"][0]["message"]["content"]}, "finish_reason": "stop"}],
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": {"code": "PROVIDER_ERROR", "message": str(exc)}})


@app.get("/xray/version")
async def xray_version():
    return {
        "version": VERSION,
        "spec_version": SPEC_VERSION,
        "dto_version": DTO_VERSION,
        "event_taxonomy_version": EVENT_TAXONOMY_VERSION,
        "api_version": API_VERSION,
    }


@app.get("/xray/mode")
async def xray_mode():
    return {
        "mode": _XRAY_MODE,
        "shadow": _XRAY_SHADOW_MODE,
        "persist_configured": bool(_TRACE_STORE_PATH),
        "persist_path": _TRACE_STORE_PATH,
    }


# ── X-RAY Trace endpoints ──────────────────────────


@app.get("/xray/traces")
async def xray_traces(limit: int = 50):
    traces = xray_store.get_recent_traces(limit=limit)
    return [trace_to_summary(t).to_dict() for t in traces]


@app.get("/xray/traces/active")
async def xray_traces_active():
    return [trace_to_summary(t).to_dict() for t in xray_store.get_active_traces()]


@app.get("/xray/traces/completed")
async def xray_traces_completed(limit: int = 50):
    return [trace_to_summary(t).to_dict() for t in xray_store.get_completed_traces()[-limit:]]


@app.get("/xray/traces/{trace_id}")
async def xray_trace_detail(trace_id: str):
    tree = xray_store.build_tree(trace_id)
    if tree is None:
        return {"error": "trace not found"}
    trace = xray_store.get_trace(trace_id)
    if trace:
        return trace_to_detail(trace, tree.get("tree", []), metadata=tree.get("metadata")).to_dict()
    return tree


@app.post("/xray/traces/{trace_id}/freeze")
async def xray_freeze_trace(trace_id: str, tags: dict | None = None):
    if tags is None:
        tags = {}
    _readonly_check()
    ok = xray_store.freeze_trace(trace_id)
    return {"ok": ok, "trace_id": trace_id, "action": "freeze"}


@app.post("/xray/traces/{trace_id}/unfreeze")
async def xray_unfreeze_trace(trace_id: str):
    _readonly_check()
    ok = xray_store.unfreeze_trace(trace_id)
    return {"ok": ok, "trace_id": trace_id, "action": "unfreeze"}


@app.post("/xray/traces/{trace_id}/terminate")
async def xray_terminate_trace(trace_id: str):
    _readonly_check()
    ok = xray_store.terminate_trace(trace_id)
    return {"ok": ok, "trace_id": trace_id, "action": "terminate"}


@app.post("/xray/traces/{trace_id}/tag")
async def xray_tag_trace(trace_id: str, tags: dict | None = None):
    _readonly_check()
    ok = xray_store.tag_trace(trace_id, tags)
    return {"ok": ok, "trace_id": trace_id, "tags": tags}


@app.get("/xray/traces/search")
async def xray_search_traces(query: str = "", status: str = "", limit: int = 50):
    traces = xray_store.search_traces(query=query, status=status, limit=limit)
    return [trace_to_summary(t).to_dict() for t in traces]


@app.get("/xray/stats")
async def xray_stats():
    return xray_store.stats


@app.get("/xray/diagnostics")
async def xray_diagnostics():
    diag = xray_store.diagnostics()
    return raw_stats_to_health_metrics(xray_store.stats, diag).to_dict()


@app.get("/xray/replay/{trace_id}")
async def xray_replay(trace_id: str, mode: str = "chronological"):
    result = xray_store.replay(trace_id, mode=mode)
    if result is None:
        return {"error": "trace not found"}
    return {
        "trace_id": result.get("trace_id"),
        "span_count": result.get("span_count", 0),
        "mode": mode,
        "timeline": [replay_entry_to_frame(e).to_dict() for e in result.get("timeline", [])],
    }


@app.get("/xray/sanitize/scan-duplicates")
async def xray_sanitize_scan_duplicates():
    from aethon.xray.data_sanitizer import scan_duplicate_span_ids

    return scan_duplicate_span_ids()


@app.post("/xray/sanitize/repair-duplicates")
async def xray_sanitize_repair_duplicates(dry_run: bool = True):
    _readonly_check()
    from aethon.xray.data_sanitizer import repair_duplicate_span_ids

    return repair_duplicate_span_ids(dry_run=dry_run)


@app.post("/xray/sanitize/orphan-cleanup")
async def xray_sanitize_orphan_cleanup(ttl_hours: float = 24, dry_run: bool = True):
    _readonly_check()
    from aethon.xray.data_sanitizer import orphan_cleanup_pass

    return orphan_cleanup_pass(ttl_hours=ttl_hours, dry_run=dry_run)


@app.get("/xray/sanitize/quarantine-list")
async def xray_sanitize_quarantine_list():
    from aethon.xray.data_sanitizer import corrupted_trace_registry

    return corrupted_trace_registry()


@app.get("/xray/manual/{scenario}")
async def xray_manual(scenario: str):
    """Run a manual validation scenario (A, B, or C) and return diagnostics."""
    result = await xray_run_scenario(scenario)
    if result is None:
        return {"error": f"unknown scenario '{scenario}' — use A, B, or C"}
    return result


@app.get("/xray/store/status")
async def xray_store_status():
    """Report persistence status and store configuration."""
    return {
        "persist_enabled": xray_store._persist_enabled,
        "persist_path": xray_store._persist_path,
        "stats": xray_store.stats,
    }


@app.get("/xray/audit")
async def xray_audit(trace_id: str | None = None):
    """Run all 5 consistency audit checks.

    If trace_id is omitted, checks run against the most recent
    completed trace.
    """
    return run_all_audit_checks(trace_id=trace_id)


@app.get("/xray/audit/{trace_id}")
async def xray_audit_trace(trace_id: str):
    """Run all 5 consistency audit checks on a specific trace."""
    return run_all_audit_checks(trace_id=trace_id)


@app.get("/xray/events/stream")
async def xray_events_stream():
    """Enhanced SSE stream with typed events: trace_completed, trace_frozen,
    trace_terminated, orphan_change, stats_changed, heartbeat."""
    _prev_completed_ids: set[str] = set()
    _prev_active_ids: set[str] = set()
    _prev_orphan = 0
    _prev_frozen_ids: set[str] = set()

    async def event_stream():
        nonlocal _prev_completed_ids, _prev_active_ids, _prev_orphan, _prev_frozen_ids
        first = True
        while True:
            stats = xray_store.stats
            completed_traces = xray_store.get_completed_traces()
            active_traces = xray_store.get_active_traces()
            orphan = stats.get("orphan_spans", 0)

            current_completed_ids = {t.trace_id for t in completed_traces}
            current_active_ids = {t.trace_id for t in active_traces}
            current_frozen_ids = {t.trace_id for t in completed_traces + active_traces if t.freeze}

            if first:
                for t in completed_traces[-5:]:
                    yield f"event: trace_completed\ndata: {json.dumps({'trace_id': t.trace_id, 'name': t.name, 'status': t.status, 'duration_ms': t.duration_ms})}\n\n"
                if orphan:
                    yield f"event: orphan_change\ndata: {json.dumps({'count': orphan})}\n\n"
                yield f"event: stats_changed\ndata: {json.dumps({'active_traces': len(current_active_ids), 'completed_traces': len(current_completed_ids), 'orphan_spans': orphan})}\n\n"
                _prev_completed_ids = current_completed_ids
                _prev_active_ids = current_active_ids
                _prev_orphan = orphan
                _prev_frozen_ids = current_frozen_ids
                first = False
                await asyncio.sleep(1)
                continue

            new_completed = current_completed_ids - _prev_completed_ids
            for tid in new_completed:
                t = xray_store.get_trace(tid)
                if t and t.ended_at is not None:
                    yield f"event: trace_completed\ndata: {json.dumps({'trace_id': tid, 'name': t.name, 'status': t.status, 'duration_ms': t.duration_ms})}\n\n"

            new_active = current_active_ids - _prev_active_ids
            for tid in new_active:
                t = xray_store.get_trace(tid)
                if t:
                    yield f"event: trace_started\ndata: {json.dumps({'trace_id': tid, 'name': t.name})}\n\n"

            removed_active = _prev_active_ids - current_active_ids
            for tid in removed_active:
                yield f"event: trace_ended\ndata: {json.dumps({'trace_id': tid})}\n\n"

            newly_frozen = current_frozen_ids - _prev_frozen_ids
            for tid in newly_frozen:
                yield f"event: trace_frozen\ndata: {json.dumps({'trace_id': tid, 'frozen': True})}\n\n"

            newly_unfrozen = _prev_frozen_ids - current_frozen_ids
            for tid in newly_unfrozen:
                yield f"event: trace_frozen\ndata: {json.dumps({'trace_id': tid, 'frozen': False})}\n\n"

            if orphan != _prev_orphan:
                yield f"event: orphan_change\ndata: {json.dumps({'count': orphan})}\n\n"

            if new_completed or new_active or removed_active or newly_frozen or newly_unfrozen or orphan != _prev_orphan:
                yield f"event: stats_changed\ndata: {json.dumps({'active_traces': len(current_active_ids), 'completed_traces': len(current_completed_ids), 'orphan_spans': orphan})}\n\n"

            _prev_completed_ids = current_completed_ids
            _prev_active_ids = current_active_ids
            _prev_orphan = orphan
            _prev_frozen_ids = current_frozen_ids

            yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/xray/events", deprecated=True)
async def xray_events():
    """[DEPRECATED] Используйте /xray/events/stream — enhanced SSE с typed events."""
    _last_completed_count = 0
    _last_active_count = 0

    async def event_stream():
        nonlocal _last_completed_count, _last_active_count
        while True:
            stats = xray_store.stats
            completed = stats.get("completed_traces", 0)
            active = stats.get("active_traces", 0)
            events = []

            if completed > _last_completed_count:
                traces = xray_store.get_recent_traces(limit=5)
                for t in traces:
                    if t.ended_at is not None:
                        events.append({"type": "trace_completed", "trace_id": t.trace_id, "name": t.name, "status": t.status, "duration_ms": t.duration_ms})
                _last_completed_count = completed

            orphan = stats.get("orphan_spans", 0)
            if orphan > 0:
                events.append({"type": "orphan_spans", "count": orphan})

            if active != _last_active_count:
                events.append({"type": "active_traces", "count": active})
                _last_active_count = active

            if events:
                yield f"data: {json.dumps(events)}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Retention endpoints ─────────────────────────────


@app.post("/xray/retention/run")
async def xray_retention_run(
    dry_run: bool = True,
    max_days: int = 30,
    max_traces: int = 1000,
    max_storage_mb: int = 500,
    archive_before_delete: bool = True,
    skip_frozen: bool = True,
    skip_active: bool = True,
    skip_interrupted: bool = False,
):
    """Run retention policy. All params optional; dry_run by default."""
    _readonly_check()
    from aethon.xray.retention import TraceRetentionPolicy, run_retention_policy

    policy = TraceRetentionPolicy(
        max_days=max_days,
        max_traces=max_traces,
        max_storage_mb=max_storage_mb,
        archive_before_delete=archive_before_delete,
        skip_frozen=skip_frozen,
        skip_active=skip_active,
        skip_interrupted=skip_interrupted,
    )
    persist_path = _TRACE_STORE_PATH
    if not persist_path:
        return {"error": "persistence not configured (XRAY_TRACE_STORE_PATH not set)"}
    return run_retention_policy(persist_path, policy=policy, dry_run=dry_run)


@app.get("/xray/retention/storage-stats")
async def xray_retention_storage_stats():
    """Return current storage usage stats."""
    from aethon.xray.retention import _compute_storage_stats

    persist_path = _TRACE_STORE_PATH
    if not persist_path:
        return {"error": "persistence not configured"}
    return _compute_storage_stats(persist_path)


@app.get("/xray/retention/trace-list")
async def xray_retention_trace_list(days: int = 0, frozen: bool = False):
    """List trace snapshots with metadata. Optionally filter by age."""
    from aethon.xray.retention import _collect_trace_snapshots

    persist_path = _TRACE_STORE_PATH
    if not persist_path:
        return {"error": "persistence not configured"}
    snaps = _collect_trace_snapshots(persist_path)
    if days > 0:
        snaps = [s for s in snaps if s["age_days"] >= days]
    if not frozen:
        snaps = [s for s in snaps if not s.get("frozen", False)]
    return {
        "trace_count": len(snaps),
        "traces": sorted(snaps, key=lambda s: s["mtime"], reverse=True)[:200],
    }
