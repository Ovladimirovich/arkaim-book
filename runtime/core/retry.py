import asyncio
import ssl
from enum import Enum

import httpx

from core.logging import log


class ErrorType(Enum):
    SSL = "ssl"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNKNOWN = "unknown"


def classify_error(exc: BaseException, status_code: int | None = None) -> ErrorType:
    if isinstance(exc, ssl.SSLError):
        return ErrorType.SSL
    if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
        return ErrorType.TIMEOUT
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
    elif isinstance(exc, httpx.RequestError):
        return ErrorType.PROVIDER_UNAVAILABLE
    if status_code is not None:
        if status_code in (401, 403):
            return ErrorType.AUTH
        if status_code == 429:
            return ErrorType.RATE_LIMIT
        if status_code in (502, 503, 504):
            return ErrorType.PROVIDER_UNAVAILABLE
        return ErrorType.UNKNOWN
    return ErrorType.UNKNOWN


_POLICY = {
    ErrorType.SSL: {"retry": False, "reason": "SSL misconfiguration"},
    ErrorType.AUTH: {"retry": False, "reason": "invalid credentials"},
    ErrorType.RATE_LIMIT: {"retry": True, "max_attempts": 3, "base_delay": 2.0},
    ErrorType.TIMEOUT: {"retry": True, "max_attempts": 3, "base_delay": 1.0},
    ErrorType.PROVIDER_UNAVAILABLE: {"retry": True, "max_attempts": 3, "base_delay": 2.0},
    ErrorType.UNKNOWN: {"retry": True, "max_attempts": 2, "base_delay": 1.0},
}


async def with_retry(fn, context: str = "", trace_id: str = "", **fn_kwargs):
    last_exc = None
    for attempt in range(1, 4):
        try:
            result = await fn(**fn_kwargs)
            if attempt > 1:
                log.info("retry_success context=%s attempt=%d trace_id=%s", context, attempt, trace_id)
            return result
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            error_type = classify_error(exc, exc.response.status_code)
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            last_exc = exc
            error_type = ErrorType.TIMEOUT
        except ssl.SSLError as exc:
            last_exc = exc
            error_type = ErrorType.SSL
        except httpx.RequestError as exc:
            last_exc = exc
            error_type = ErrorType.PROVIDER_UNAVAILABLE
        except Exception as exc:
            last_exc = exc
            error_type = ErrorType.UNKNOWN

        policy = _POLICY.get(error_type, {})
        if not policy.get("retry", False):
            log.warning("retry_abort context=%s attempt=%d error_type=%s reason=%s trace_id=%s",
                        context, attempt, error_type.value, policy.get("reason", ""), trace_id)
            raise last_exc

        max_attempts = policy.get("max_attempts", 1)
        if attempt >= max_attempts:
            log.warning("retry_exhausted context=%s attempt=%d/%d error_type=%s trace_id=%s",
                        context, attempt, max_attempts, error_type.value, trace_id)
            raise last_exc

        delay = policy.get("base_delay", 1.0) * (2 ** (attempt - 1))
        log.warning("retry context=%s attempt=%d/%d error_type=%s delay=%.1fs trace_id=%s",
                    context, attempt, max_attempts, error_type.value, delay, trace_id)
        await asyncio.sleep(delay)

    raise last_exc
