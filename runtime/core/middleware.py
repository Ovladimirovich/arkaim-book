"""Middleware — rate limiting, auth protection, analytics."""
import time
import logging

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

log = logging.getLogger("hermes.middleware")


def create_rate_limit_middleware(check_rate_limit, get_rate_limit_info, analytics, shared):
    """Фабрика rate-limit middleware (замыкание на зависимости)."""

    async def rate_limit_middleware(request: Request, call_next):
        start_time = time.time()
        request_type = request.url.path.split("/")[-1] or "root"

        if request.url.path in ("/health", "/_ui", "/book/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        if not check_rate_limit(client_ip):
            analytics.track_request(request_type, time.time() - start_time, False)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={
                    "X-RateLimit-Limit": str(int(shared.RATE_LIMIT_REQUESTS_PER_MINUTE)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60",
                },
            )

        try:
            response = await call_next(request)
            response_time = time.time() - start_time
            success = response.status_code < 400
            analytics.track_request(request_type, response_time, success)

            rate_info = get_rate_limit_info(client_ip)
            response.headers["X-RateLimit-Limit"] = str(int(rate_info["rate"] * 60))
            response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
            response.headers["X-RateLimit-Reset"] = "60"
            return response
        except Exception:
            analytics.track_request(request_type, time.time() - start_time, False)
            raise

    return rate_limit_middleware


async def protected_routes_middleware(request: Request, call_next):
    """Защита /_ui (login redirect) и /xray/ (admin only)."""
    path = request.url.path

    if path.startswith("/_ui"):
        try:
            from auth.rbac import get_current_user
            await get_current_user(request)
        except Exception:
            return RedirectResponse(url="/auth/login", status_code=302)

    if path.startswith("/xray/"):
        public_xray = ("/xray/version", "/xray/mode", "/xray/store/status")
        if path not in public_xray:
            try:
                from auth.rbac import get_current_user
                user = await get_current_user(request)
                if user.get("role") != "admin":
                    raise HTTPException(status_code=403, detail="Admin only")
            except HTTPException as exc:
                raise exc

    return await call_next(request)
