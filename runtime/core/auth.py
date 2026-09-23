import hashlib
import logging

from fastapi import Request, HTTPException
from auth.tokens import decode_access_token
from auth.users import UserStore
from core.config import settings

log = logging.getLogger("hermes.core.auth")


async def verify_request(request: Request) -> dict:
    auth_header = request.headers.get("authorization", "")
    token = None

    if auth_header:
        token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else auth_header.strip()
    else:
        # Fallback: читаем token из cookie arkaim_session
        cookie_header = request.headers.get("cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("arkaim_session="):
                token = part.split("=", 1)[1]
                break

    if not token:
        if settings.HERMES_API_KEY:
            raise HTTPException(status_code=401, detail="Missing API key")
        raise HTTPException(status_code=401, detail="Missing Authorization header or session cookie")

    user_store = UserStore()

    if settings.HERMES_API_KEY and token == settings.HERMES_API_KEY:
        try:
            body = await request.json()
            user_payload = body.get("user") or {}
            user_id = user_payload.get("user_id")
            if user_id:
                user = await user_store.get_user(user_id)
                if user and user.get("is_active"):
                    log.info("auth_via_gateway_forward user_id=%s role=%s", user["id"], user["role"])
                    return {
                        "auth": "ok",
                        "user_id": user["id"],
                        "role": user["role"],
                        "provider": user["provider"],
                        "username": user.get("username"),
                        "display_name": user.get("display_name"),
                    }
        except Exception as e:
            log.warning("auth_gateway_forward_error: %s", e)
        return {
            "auth": "ok",
            "user_id": "service",
            "role": "admin",
            "provider": "internal",
            "username": "gateway_service",
        }

    payload = decode_access_token(token)
    if payload:
        user = await user_store.get_user(payload.sub)
        if user and user.get("is_active"):
            log.info("auth_via_jwt user_id=%s role=%s", user["id"], user["role"])
            return {
                "auth": "ok",
                "user_id": user["id"],
                "role": user["role"],
                "provider": user["provider"],
                "username": user.get("username"),
                "display_name": user.get("display_name"),
            }

    key_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key = await user_store.get_api_key_by_hash(key_hash)
    if api_key and api_key.get("is_active"):
        user = await user_store.get_user(api_key["user_id"])
        if user and user.get("is_active"):
            await user_store.touch_api_key(api_key["id"])
            log.info("auth_via_api_key user_id=%s key_prefix=%s", user["id"], api_key.get("key_prefix"))
            return {
                "auth": "ok",
                "user_id": user["id"],
                "role": user["role"],
                "provider": user["provider"],
                "username": user.get("username"),
                "display_name": user.get("display_name"),
            }

    raise HTTPException(status_code=403, detail="Invalid API key or token")
