import logging
from datetime import timedelta
from html import escape as html_escape
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from auth.users import UserStore
from auth.oauth.telegram import verify_telegram_login
from auth.oauth.google import (
    exchange_code,
    verify_google_id_token,
    parse_google_user,
    get_google_auth_url,
    GoogleOAuthError,
)
from auth.login_tokens import generate_login_token, verify_login_token
from auth.rbac import require_role
from auth.tokens import create_access_token
from auth.api_keys import generate_api_key, mask_api_key
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])
log = logging.getLogger("hermes.auth")
user_store = UserStore()


_LOGIN_HTML = Path(__file__).resolve().parent / "login.html"


@router.get("/login")
async def auth_login(request: Request):
    html = _LOGIN_HTML.read_text(encoding="utf-8")
    html = html.replace("{{TELEGRAM_BOT_USERNAME}}", html_escape(settings.TELEGRAM_BOT_USERNAME or ""))
    html = html.replace('data-auth-url="{{PUBLIC_BASE_URL}}/auth/telegram/callback"', 'data-auth-url="/auth/telegram/callback"')
    if not settings.GOOGLE_CLIENT_ID:
        html = html.replace('<a href="/auth/google"', '<a href="/auth/google" style="display:none"')
    return Response(content=html, media_type="text/html")


@router.post("/telegram/callback")
async def telegram_callback(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON")

    telegram_data = verify_telegram_login(body)
    user = await user_store.upsert_user(
        provider=telegram_data["provider"],
        provider_user_id=telegram_data["provider_user_id"],
        username=telegram_data.get("username"),
        display_name=telegram_data.get("display_name"),
        role="reader",
    )
    token = create_access_token(
        subject=user["id"],
        role=user["role"],
        provider=user["provider"],
        expires_delta=timedelta(hours=12),
    )
    resp = JSONResponse({"ok": True, "user": {"id": user["id"], "role": user["role"], "username": user.get("username"), "display_name": user.get("display_name")}})
    is_secure = bool(settings.PUBLIC_BASE_URL.startswith("https://"))
    resp.set_cookie(
        "arkaim_session",
        token,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        max_age=3600 * 12,
        path="/",
    )
    log.info("user_logged_in provider=%s user_id=%s", telegram_data["provider"], user["id"])
    return resp


@router.post("/telegram/login")
async def telegram_login_token(request: Request):
    """Вход по одноразовому токену (сгенерированному ботом /login)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON")

    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Отсутствует token")

    telegram_data = verify_login_token(token)
    if not telegram_data:
        raise HTTPException(status_code=400, detail="Токен недействителен или истёк")

    user = await user_store.upsert_user(
        provider=telegram_data["provider"],
        provider_user_id=telegram_data["provider_user_id"],
        username=telegram_data.get("username"),
        display_name=telegram_data.get("display_name"),
        role=telegram_data.get("role", "reader"),
    )
    jwt_token = create_access_token(
        subject=user["id"],
        role=user["role"],
        provider=user["provider"],
        expires_delta=timedelta(hours=12),
    )
    resp = JSONResponse({
        "ok": True,
        "user": {
            "id": user["id"],
            "role": user["role"],
            "username": user.get("username"),
            "display_name": user.get("display_name"),
        },
    })
    is_secure = bool(settings.PUBLIC_BASE_URL.startswith("https://"))
    resp.set_cookie(
        "arkaim_session",
        jwt_token,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        max_age=3600 * 12,
        path="/",
    )
    log.info("user_logged_in_via_token provider=%s user_id=%s", telegram_data["provider"], user["id"])
    return resp


@router.post("/dev/generate-token")
async def dev_generate_token(request: Request):
    """Только для разработки: генерирует тестовый токен для входа."""
    body = await request.json()
    telegram_user_id = body.get("telegram_user_id", "dev-test-user")
    username = body.get("username", "dev_user")
    display_name = body.get("display_name", "Dev User")
    role = body.get("role", "admin")
    token = generate_login_token(telegram_user_id, username, display_name, role=role)
    return {"token": token, "login_url": f"/login?token={token}"}


@router.get("/google")
async def google_login():
    redirect_uri = f"{settings.PUBLIC_BASE_URL}/auth/google/callback"
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth не настроен")
    auth_url = get_google_auth_url(redirect_uri)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None):
    if not code:
        raise HTTPException(status_code=400, detail="Отсутствует code")
    try:
        redirect_uri = f"{settings.PUBLIC_BASE_URL}/auth/google/callback"
        tokens = await exchange_code(code, redirect_uri)
        id_token = tokens.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="Отсутствует id_token")
        payload = verify_google_id_token(id_token)
        google_data = parse_google_user(payload)
        user = await user_store.upsert_user(
            provider=google_data["provider"],
            provider_user_id=google_data["provider_user_id"],
            username=google_data.get("username"),
            display_name=google_data.get("display_name"),
            role="reader",
        )
        token = create_access_token(
            subject=user["id"],
            role=user["role"],
            provider=user["provider"],
            expires_delta=timedelta(hours=12),
        )
        is_secure = bool(settings.PUBLIC_BASE_URL.startswith("https://"))
        resp = RedirectResponse(url="/_ui")
        resp.set_cookie(
            "arkaim_session",
            token,
            httponly=True,
            secure=is_secure,
            samesite="Lax",
            max_age=3600 * 12,
            path="/",
        )
        log.info("user_logged_in provider=google user_id=%s", user["id"])
        return resp
    except GoogleOAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def auth_logout_post():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("arkaim_session", path="/")
    return resp


@router.get("/logout")
async def auth_logout_get():
    resp = RedirectResponse(url="/auth/login")
    resp.delete_cookie("arkaim_session", path="/")
    return resp


@router.post("/register")
async def auth_register(request: Request):
    """Регистрация нового пользователя по email/username."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON")

    username = body.get("username", "").strip()
    email = body.get("email", "").strip()
    display_name = body.get("display_name", "").strip() or username

    if not username:
        raise HTTPException(status_code=400, detail="Введите имя пользователя")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Имя пользователя — минимум 3 символа")

    # Проверяем уникальность username
    existing = await user_store.get_user_by_provider("email", username)
    if existing:
        raise HTTPException(status_code=409, detail="Пользователь с таким именем уже существует")

    user = await user_store.upsert_user(
        provider="email",
        provider_user_id=username,
        username=username,
        display_name=display_name,
        role="reader",
    )

    token = create_access_token(
        subject=user["id"],
        role=user["role"],
        provider=user["provider"],
        expires_delta=timedelta(hours=12),
    )

    resp = JSONResponse({
        "ok": True,
        "user": {
            "id": user["id"],
            "role": user["role"],
            "username": user.get("username"),
            "display_name": user.get("display_name"),
        },
    })
    is_secure = bool(settings.PUBLIC_BASE_URL.startswith("https://"))
    resp.set_cookie(
        "arkaim_session",
        token,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        max_age=3600 * 12,
        path="/",
    )
    log.info("user_registered provider=email user_id=%s username=%s", user["id"], username)
    return resp


@router.get("/me")
async def auth_me(request: Request):
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    return JSONResponse({"user": {"id": user["user_id"], "role": user["role"], "username": user.get("username"), "display_name": user.get("display_name"), "provider": user.get("provider")}})


@router.post("/update-profile")
async def update_profile(request: Request):
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    body = await request.json()
    display_name = body.get("display_name", "").strip()
    if display_name:
        await user_store.set_display_name(user["user_id"], display_name)
    return {"ok": True}


@router.post("/api-key")
async def create_api_key(request: Request, name: str | None = None):
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    raw, key_hash, prefix = generate_api_key()
    key_id = await user_store.save_api_key(user_id=user["user_id"], key_prefix=prefix, key_hash=key_hash, name=name)
    return JSONResponse({"key_id": key_id, "key": raw, "key_masked": mask_api_key(raw)})


@router.get("/api-keys")
async def list_api_keys(request: Request):
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    keys = await user_store.list_api_keys(user_id=user["user_id"])
    return JSONResponse([{k: v for k, v in key.items() if k != "key_hash"} for key in keys])


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, request: Request):
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    ok = await user_store.revoke_api_key_for_user(key_id, user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="API-ключ не найден")
    log.info("api_key_revoked key_id=%s user_id=%s", key_id, user["user_id"])
    return {"ok": True, "key_id": key_id}


# ── Admin endpoints ──────────────────────────────────


@router.get("/admin/users", dependencies=[Depends(require_role("admin"))])
async def admin_list_users(request: Request):
    """Список всех пользователей (только admin)."""
    users = await user_store.list_users(limit=200)
    return JSONResponse([
        {
            "id": u["id"],
            "provider": u["provider"],
            "provider_user_id": u["provider_user_id"],
            "username": u["username"],
            "display_name": u["display_name"],
            "role": u["role"],
            "is_active": u["is_active"],
            "created_at": u["created_at"],
        }
        for u in users
    ])


@router.post("/admin/users/{user_id}/role", dependencies=[Depends(require_role("admin"))])
async def admin_set_role(user_id: str, role: str):
    """Сменить роль пользователя."""
    if role not in ("reader", "editor", "admin"):
        raise HTTPException(status_code=400, detail="Недопустимая роль")
    ok = await user_store.set_role(user_id, role)
    if not ok:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"ok": True, "user_id": user_id, "role": role}


@router.post("/admin/users/{user_id}/toggle", dependencies=[Depends(require_role("admin"))])
async def admin_toggle_user(user_id: str):
    """Активировать/деактивировать пользователя."""
    user = await user_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    new_state = not user["is_active"]
    await user_store.set_active(user_id, new_state)
    return {"ok": True, "user_id": user_id, "is_active": new_state}


@router.get("/admin/stats", dependencies=[Depends(require_role("admin"))])
async def admin_stats():
    """Общая статистика системы."""
    from core.presence_manager import get_observer, get_suggester, get_email_store
    users = await user_store.list_users()
    presence = get_observer()
    suggester = get_suggester()
    email = get_email_store()
    email_stats = await email.get_stats()
    return {
        "users": {
            "total": len(users),
            "by_role": {r: sum(1 for u in users if u["role"] == r) for r in ("reader", "editor", "admin")},
        },
        "reader_memory": {},  # будет заполнено ниже
        "presence": {
            "trending_topics": len(await presence.get_trending_topics(min_hits=1)) if hasattr(presence, "get_trending_topics") else 0,
            "pending_suggestions": len(suggester.list_pending()),
        },
        "email": email_stats,
    }


async def _get_reader_stats():
    try:
        from core.pulse_manager import get_reader_memory
        mem = get_reader_memory()
        return await mem.get_stats()
    except Exception:
        return {}


# ── Admin CRUD: пользователи ─────────────────────────


@router.get("/admin/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def admin_get_user(user_id: str):
    """Получить детали пользователя."""
    user = await user_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {
        "id": user["id"],
        "provider": user["provider"],
        "provider_user_id": user["provider_user_id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.delete("/admin/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def admin_delete_user(user_id: str):
    """Удалить пользователя и все связанные данные (сессии, API-ключи)."""
    user = await user_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    # Удаляем сессии и API-ключи пользователя
    await user_store.delete_user_sessions(user_id)
    await user_store.delete_user_api_keys(user_id)
    # Деактивируем пользователя (мягкое удаление)
    await user_store.set_active(user_id, False)
    log.info("admin_user_deleted user_id=%s by admin", user_id)
    return {"ok": True, "user_id": user_id}


# ── Admin CRUD: сессии ───────────────────────────────


@router.get("/admin/sessions", dependencies=[Depends(require_role("admin"))])
async def admin_list_sessions():
    """Список всех активных сессий."""
    sessions = await user_store.list_sessions()
    return [
        {
            "id": s["id"],
            "user_id": s["user_id"],
            "expires_at": s["expires_at"],
            "created_at": s["created_at"],
        }
        for s in sessions
    ]


@router.delete("/admin/sessions/{session_id}", dependencies=[Depends(require_role("admin"))])
async def admin_delete_session(session_id: str):
    """Отозвать сессию."""
    ok = await user_store.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    log.info("admin_session_revoked session_id=%s", session_id)
    return {"ok": True, "session_id": session_id}


# ── Admin CRUD: API-ключи ────────────────────────────


@router.get("/admin/api-keys", dependencies=[Depends(require_role("admin"))])
async def admin_list_api_keys():
    """Список всех API-ключей."""
    keys = await user_store.list_all_api_keys()
    return [
        {
            "id": k["id"],
            "user_id": k["user_id"],
            "key_prefix": k["key_prefix"],
            "name": k["name"],
            "last_used_at": k["last_used_at"],
            "is_active": k["is_active"],
            "created_at": k["created_at"],
        }
        for k in keys
    ]


@router.delete("/admin/api-keys/{key_id}", dependencies=[Depends(require_role("admin"))])
async def admin_delete_api_key(key_id: str):
    """Отозвать API-ключ."""
    ok = await user_store.revoke_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API-ключ не найден")
    log.info("admin_api_key_revoked key_id=%s", key_id)
    return {"ok": True, "key_id": key_id}


# ── Invite endpoints ────────────────────────────────


@router.post("/admin/invites", dependencies=[Depends(require_role("admin"))])
async def admin_create_invite(request: Request, role: str = "reader", max_uses: int = 1,
                               expires_at: str | None = None, note: str = ""):
    """Создать инвайт-ссылку."""
    from auth.rbac import get_current_user
    user = await get_current_user(request)
    if role not in ("reader", "editor", "admin"):
        raise HTTPException(status_code=400, detail="Недопустимая роль")
    if max_uses < 1 or max_uses > 100:
        raise HTTPException(status_code=400, detail="max_uses должен быть от 1 до 100")
    invite = await user_store.create_invite(
        created_by=user["user_id"], role=role, max_uses=max_uses,
        expires_at=expires_at, note=note,
    )
    base_url = settings.PUBLIC_BASE_URL or "http://localhost:8642"
    invite_url = f"{base_url}/auth/invite/{invite['token']}"
    log.info("admin_invite_created invite_id=%s role=%s by=%s", invite["id"], role, user["user_id"])
    return {"ok": True, "invite": invite, "url": invite_url}


@router.get("/admin/invites", dependencies=[Depends(require_role("admin"))])
async def admin_list_invites():
    """Список всех инвайтов."""
    invites = await user_store.list_invites()
    base_url = settings.PUBLIC_BASE_URL or "http://localhost:8642"
    for inv in invites:
        inv["url"] = f"{base_url}/auth/invite/{inv['token']}"
    return invites


@router.delete("/admin/invites/{invite_id}", dependencies=[Depends(require_role("admin"))])
async def admin_delete_invite(invite_id: str):
    """Деактивировать инвайт."""
    ok = await user_store.revoke_invite(invite_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Инвайт не найден")
    log.info("admin_invite_revoked invite_id=%s", invite_id)
    return {"ok": True, "invite_id": invite_id}


@router.get("/invite/{token}")
async def accept_invite_page(request: Request, token: str):
    """Страница принятия инвайта."""
    invite = await user_store.get_invite_by_token(token)
    if not invite:
        return Response(content="<h2>Инвайт недействителен или уже использован</h2>", media_type="text/html")
    return Response(content=f"""
    <html><head><title>Приглашение</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:50px;">
    <h2>Вы приглашены в «Наследие Аркаима»</h2>
    <p>Роль: <b>{invite['role']}</b></p>
    <p>Осталось использований: {invite['max_uses'] - invite['use_count']}</p>
    <a href="/auth/login" style="display:inline-block;padding:12px 24px;background:#3b82f6;color:white;text-decoration:none;border-radius:8px;">Войти через Telegram</a>
    <br><br>
    <a href="/auth/google" style="display:inline-block;padding:12px 24px;background:#ef4444;color:white;text-decoration:none;border-radius:8px;">Войти через Google</a>
    </body></html>
    """, media_type="text/html")


@router.post("/invite/{token}/accept")
async def accept_invite(token: str, request: Request):
    """Применить инвайт к текущему пользователю."""
    from auth.rbac import get_current_user
    try:
        user = await get_current_user(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Войдите в систему для принятия приглашения")
    invite = await user_store.use_invite(token)
    if not invite:
        raise HTTPException(status_code=400, detail="Инвайт недействителен, истёк или уже использован")
    # Обновляем роль пользователя
    await user_store.set_role(user["user_id"], invite["role"])
    log.info("invite_accepted user_id=%s role=%s invite_id=%s", user["user_id"], invite["role"], invite["id"])
    return {"ok": True, "role": invite["role"]}

