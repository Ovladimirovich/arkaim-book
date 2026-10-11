# G0 IMPLEMENTATION PLAN

## 1. Current State
- Provider abstraction: BaseProvider exists with chat(), stream(), health(), close()
- Circuit breaker: ProviderRegistry with _CircuitBreakerState (threshold=3, cooldown=60s)
- Fallback chain: orchestrator.py:127-191 iterates through healthy providers
- Rate limiting: In-memory sliding window in main.py (global, per-IP)
- Health endpoint: GET /provider/health exists (main.py:509-512)
- Model discovery: ABSENT
- OpenAI-compatible API: Partial (/v1/chat exists but custom format)

## 2. Confirmed GAPs
GAP-1: Model Discovery — ABSENT
  - No list_models() in BaseProvider
  - No /v1/models endpoint
  - Models hardcoded in adapters

GAP-2: OpenAI-compatible — PARTIAL
  - /v1/chat exists but uses BookAskRequest format
  - No /v1/chat/completions endpoint
  - Response format is custom, not OpenAI-compatible

GAP-3: Per-provider rate limiting — ABSENT
  - Global rate limiter exists (main.py:42-59)
  - No per-provider or per-model limits
  - RATE_LIMIT_REQUESTS_PER_MINUTE in config unused for providers

GAP-4: Provider health API — EXISTS but minimal
  - GET /provider/health returns basic status
  - Not standardized across providers
  - No model availability info

## 3. Proposed G0 Architecture

### 3.1 BaseProvider.list_models()

Add to BaseProvider:
  async def list_models(self) -> list[dict]:
      """Return available models with metadata."""
      return []

GigaChatProvider:
  - Call GET {base_url}/models
  - Parse response to extract model IDs
  - Return [{id, context_window, modalities}]

OpenRouterProvider:
  - Call GET {base_url}/models
  - Parse response
  - Currently 403 (external blocker)

### 3.2 GET /v1/models

Aggregate from all registered providers:
  ProviderRegistry.get(name).list_models() for each name
  Return OpenAI-compatible format:
  [{"id": "gigachat/GigaChat-Pro", "object": "model", "owned_by": "sber"}, ...]

### 3.3 POST /v1/chat/completions

Accept OpenAI format:
  {model, messages, temperature, max_tokens, stream}
Convert to internal format:
  messages -> BookAskRequest.messages
  model -> provider selection (or default to first in chain)
Call existing orchestrator.chat()
Convert response back to OpenAI format:
  {id, object, created, model, choices, usage}

### 3.4 GET /providers/health

Already exists. Standardize response:
  {status, providers[{name, health, models[], last_error}]}

## 4. Parameter Support Matrix

| Parameter | Status | Notes |
|-----------|--------|-------|
| model | SUPPORTED | Maps to provider selection |
| messages | SUPPORTED | Required, list of {role, content} |
| temperature | IGNORED | Not used by GigaChat |
| max_tokens | IGNORED | GigaChat has fixed context |
| stream | SUPPORTED | Returns SSE format |
| frequency_penalty | IGNORED | Not supported |
| presence_penalty | IGNORED | Not supported |
| logprobs | IGNORED | Not supported |
| top_p | IGNORED | Not used |
| stop | IGNORED | Not used |
| n | REJECTED | Only 1 choice supported |
| tools | REJECTED | Not yet implemented |
| function_call | REJECTED | Not yet implemented |

## 5. Error Handling Semantics

| Error | HTTP Status | Response |
|-------|-------------|----------|
| Provider unavailable | 503 | {error:{code:"PROVIDER_UNAVAILABLE"}} |
| Model not found | 400 | {error:{code:"INVALID_MODEL"}} |
| Auth failure | 401 | {error:{code:"AUTH_FAILED"}} |
| Rate limit | 429 | {error:{code:"RATE_LIMITED"}} |
| Timeout | 504 | {error:{code:"TIMEOUT"}} |
| Circuit breaker open | 503 | {error:{code:"CIRCUIT_BREAKER_OPEN"}} |
| Provider 403/5xx | 502 | {error:{code:"PROVIDER_ERROR"}} |
| Fallback succeeded | 200 | Normal response |

## 6. Files to Change

NEW FILES:
  - runtime/core/dto/openai.py (OpenAI format DTOs)
  - runtime/tests/test_g0_models.py
  - runtime/tests/test_g0_openai.py

MODIFIED FILES:
  - runtime/core/providers/base.py (add list_models)
  - runtime/core/providers/gigachat.py (implement list_models)
  - runtime/core/providers/openrouter.py (implement list_models)
  - runtime/core/main.py (add endpoints)
  - runtime/core/provider_registry.py (add list_models aggregation)

NOT CHANGED:
  - runtime/core/orchestrator.py
  - runtime/core/routes/book.py
  - runtime/core/retry.py
  - runtime/core/middleware.py

## 7. Backward Compatibility

All changes are ADDITIVE:
- Existing /v1/chat endpoint unchanged
- Existing /book/ask endpoint unchanged
- Existing /provider/health endpoint unchanged (new endpoint is /providers/health)
- No changes to provider adapters (except adding list_models method)
- No changes to circuit breaker or retry logic

## 8. Tests to Add

test_g0_models.py:
  - test_base_provider_returns_empty_list()
  - test_gigachat_list_models()
  - test_openrouter_list_models_skips_on_403()
  - test_registry_aggregates_models()

test_g0_openai.py:
  - test_chat_completions_converts_request()
  - test_chat_completions_converts_response()
  - test_chat_completions_fallback_on_error()
  - test_chat_completions_rejects_n_greater_than_1()
  - test_chat_completions_ignores_unsupported_params()

test_g0_health.py:
  - test_providers_health_returns_all()
  - test_providers_health_includes_models()
  - test_providers_health_handles_error()

## 9. Real Runtime Verification

Before implementation:
  - Verify GigaChat /models endpoint is accessible
  - Check OpenRouter /models response format
  - Test with actual GigaChat credentials

After implementation:
  - Run: GET http://localhost:8642/v1/models
  - Run: POST http://localhost:8642/v1/chat/completions
  - Run: GET http://localhost:8642/providers/health
  - Verify existing /v1/chat still works
  - Verify existing /book/ask still works

## 10. Acceptance Criteria

MUST PASS:
  - GET /v1/models returns working list with GigaChat models
  - POST /v1/chat/completions works through GigaChat
  - GET /providers/health returns standardized response
  - All existing tests pass (no regression)
  - New G0 tests pass
  - Existing /v1/chat endpoint regression-free
  - Existing /book/ask endpoint regression-free
  - Fallback/circuit breaker regression-free

OPENROUTER:
  - Not required for acceptance (403 is external blocker)
  - list_models() should return UNKNOWN status gracefully

## 11. Risks / Deferred Items

DEFERRED TO G1:
  - Streaming support for /v1/chat/completions
  - Token usage tracking (usage field in response)
  - Per-model rate limiting
  - Embeddings endpoint (/v1/embeddings)

RISKS:
  - GigaChat /models endpoint may not exist or have different format
  - Need to verify actual API response structure
  - OpenRouter 403 may indicate account issue (not Gateway bug)

## G0 DESIGN STATUS: READY FOR IMPLEMENTATION

IMPLEMENTATION SCOPE:
  1. Add list_models() to BaseProvider + implement in adapters
  2. Add GET /v1/models endpoint
  3. Add POST /v1/chat/completions endpoint (non-streaming)
  4. Standardize GET /providers/health
  5. Add tests for all new endpoints

DEFERRED:
  - Streaming support
  - Token usage tracking
  - Per-model rate limiting
  - Embeddings
  - Tools/functions support

ACCEPTANCE:
  - GET /v1/models → working (GigaChat models)
  - POST /v1/chat/completions → working through GigaChat
  - GET /providers/health → working
  - All existing tests → pass
  - New G0 tests → pass
  - Existing /book/ask → regression-free
  - Fallback/circuit breaker → regression-free
  - Real GigaChat E2E → pass
