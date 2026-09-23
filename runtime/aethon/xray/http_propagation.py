"""HTTP header propagation for distributed tracing.

Defines canonical header names and helpers for injecting/extracting
causal context across HTTP boundaries (gateway, core, providers).
"""

from __future__ import annotations

from typing import Any

# ── Canonical header names ─────────────────────────

HEADER_TRACE_ID = "X-Trace-Id"
HEADER_SPAN_ID = "X-Span-Id"
HEADER_PARENT_SPAN_ID = "X-Parent-Span-Id"
HEADER_LOGICAL_TS = "X-Logical-Ts"
HEADER_CAUSAL_DEPTH = "X-Causal-Depth"

# ── Extract ────────────────────────────────────────


def extract_xray_headers(headers: dict[str, str]) -> dict[str, str]:
    """Extract X-RAY propagation headers from an HTTP header dict.

    Returns a dict with keys: trace_id, span_id, parent_span_id,
    logical_ts, causal_depth. Missing fields are empty strings.
    """
    return {
        "trace_id": headers.get(HEADER_TRACE_ID, ""),
        "span_id": headers.get(HEADER_SPAN_ID, ""),
        "parent_span_id": headers.get(HEADER_PARENT_SPAN_ID, ""),
        "logical_ts": headers.get(HEADER_LOGICAL_TS, ""),
        "causal_depth": headers.get(HEADER_CAUSAL_DEPTH, ""),
    }


# ── Inject ─────────────────────────────────────────


def make_xray_headers(
    trace_id: str,
    span_id: str,
    parent_span_id: str | None = None,
    logical_ts: int = 0,
    depth: int = 0,
) -> dict[str, str]:
    """Build a dict of X-RAY headers ready to attach to an HTTP request.

    These headers are immutable per hop — the receiving process must
    not regenerate trace_id or reset logical_ts.
    """
    headers = {
        HEADER_TRACE_ID: trace_id,
        HEADER_SPAN_ID: span_id,
        HEADER_LOGICAL_TS: str(logical_ts),
        HEADER_CAUSAL_DEPTH: str(depth),
    }
    if parent_span_id:
        headers[HEADER_PARENT_SPAN_ID] = parent_span_id
    return headers


def make_xray_headers_raw(
    trace_id: str,
    span_id: str,
    parent_span_id: str | None = None,
    logical_ts: int = 0,
    depth: int = 0,
) -> str:
    """Build raw HTTP header lines (\\r\\n-separated) for injection into
    a manually-constructed HTTP/1.1 request."""
    lines = []
    lines.append(f"{HEADER_TRACE_ID}: {trace_id}")
    lines.append(f"{HEADER_SPAN_ID}: {span_id}")
    if parent_span_id:
        lines.append(f"{HEADER_PARENT_SPAN_ID}: {parent_span_id}")
    lines.append(f"{HEADER_LOGICAL_TS}: {logical_ts}")
    lines.append(f"{HEADER_CAUSAL_DEPTH}: {depth}")
    return "\r\n".join(lines) + "\r\n"


# ── FastAPI integration ────────────────────────────


def fastapi_extract_xray(request: Any) -> dict[str, str]:
    """Extract X-RAY headers from a FastAPI Request object."""
    return {
        "trace_id": request.headers.get(HEADER_TRACE_ID, ""),
        "span_id": request.headers.get(HEADER_SPAN_ID, ""),
        "parent_span_id": request.headers.get(HEADER_PARENT_SPAN_ID, ""),
        "logical_ts": request.headers.get(HEADER_LOGICAL_TS, ""),
        "causal_depth": request.headers.get(HEADER_CAUSAL_DEPTH, ""),
    }
