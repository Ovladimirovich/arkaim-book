from fastapi import Depends, HTTPException, Request


ROLE_HIERARCHY = {"reader": 0, "editor": 1, "admin": 2}


async def get_current_user(request: Request) -> dict:
    from auth.users import UserStore
    from auth.tokens import decode_access_token
    from core.config import settings

    user_store = UserStore()
    authorization = request.headers.get("authorization", "")
    cookie_token = request.cookies.get("arkaim_session")

    token = None
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif cookie_token:
        token = cookie_token

    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Service key (HERMES_API_KEY) — аутентифицирует сервис, НЕ даёт admin
    if settings.HERMES_API_KEY and token == settings.HERMES_API_KEY:
        import hashlib
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = await user_store.get_api_key_by_hash(key_hash)
        if api_key and api_key.get("is_active"):
            user = await user_store.get_user(api_key["user_id"])
            if user and user.get("is_active"):
                return {"user_id": user["id"], "role": user["role"], "provider": user["provider"], "username": user.get("username"), "display_name": user.get("display_name")}
        # Сервисный ключ без привязанного пользователя — запрещаем
        raise HTTPException(status_code=403, detail="Service key не привязан к активному пользователю")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверный или истекший токен")

    user = await user_store.get_user(payload.sub)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Пользователь не активен")

    return {"user_id": user["id"], "role": user["role"], "provider": user["provider"], "username": user.get("username"), "display_name": user.get("display_name")}


def require_role(*allowed: str):
    async def _checker(user: dict = Depends(get_current_user)):
        user_level = ROLE_HIERARCHY.get(user["role"], -1)
        allowed_levels = [ROLE_HIERARCHY.get(r, -1) for r in allowed]
        if user_level < min(allowed_levels):
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user
    return _checker
