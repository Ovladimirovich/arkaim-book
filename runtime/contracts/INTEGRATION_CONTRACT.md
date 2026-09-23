# Hermes Integration Contract

> **Hard freeze.** Integrations are transport adapters. They are NOT runtime components. An integration's sole job is to convert an external protocol into a Hermes `NormalizedRequest` and forward it to Gateway.

---

## 1. Single Responsibility

Every integration adapter MUST follow this flow:

```text
External Event (Telegram Update / VK Event / Webhook / API call)
  ↓
Normalize to Hermes Protocol
  ↓
HTTP POST to Gateway (/v1/chat or /v1/stream)
  ↓
Return response to external client
```

That is **all** an integration does.

---

## 2. What an Integration MUST NOT do

### 2.1 Forbidden knowledge

An integration MUST NOT:

- Know about **providers** (GigaChat, OpenRouter)
- Know about **skills** (pricing, leads, identity, RAG)
- Know about **memory** or persistence
- Know about **orchestration** or execution flow
- Know about **Core internals** (orchestrator, router, tools)
- Import any module from `core`, `skills`, or `memory`

### 2.2 Forbidden operations

- Store conversation state or dialog history
- Cache responses
- Make decisions about routing, provider selection, or fallback
- Execute business logic
- Format or modify response content beyond transport requirements
- Call Core directly (must go through Gateway)
- Import provider SDKs or AI libraries

---

## 3. Integration Interface

An integration adapter:

```python
# Pseudocode — every integration does this:
async def handle_event(external_event):
    # 1. Normalize to Hermes protocol
    request = NormalizedRequest(
        messages=[{"role": "user", "content": external_event.text}],
        session_id=f"tg:{external_event.chat_id}",
        provider="",
        metadata={
            "user_id": f"tg:{external_event.user_id}",
            "client_type": "telegram",
        },
    )
    # 2. Forward to Gateway
    response = await http_post(
        "http://127.0.0.1:8000/v1/chat",
        json=request_to_dict(request),
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    # 3. Return response to external client
    await external_event.reply(response.text)
```

---

## 4. State Ownership

| What | Who owns it |
|---|---|
| Conversation history | Core → Memory |
| Session mapping | Core (via session_id) |
| Auth tokens | Core → config |
| Transport offset (e.g. Telegram update_id) | Integration only (ephemeral) |

An integration may track transport-level cursors (e.g., `update_id`, `offset`) but MUST NOT derive business meaning from them.

---

## 5. Error Handling

- Transport errors: retry (up to 3 times with backoff)
- Gateway errors (4xx/5xx): return a generic error message to the client
- Provider errors: NOT handled by integration — this is Core's responsibility
- Network timeouts: log and return "Service temporarily unavailable"

---

## 6. Current Integrations

| Integration | Protocol | File | Status |
|---|---|---|---|
| Telegram | Long-polling | `integrations/telegram/` | Active |

### 6.1 Adding a new integration

1. Create `integrations/<name>/` directory
2. Implement: normalize external event → HTTP POST to Gateway
3. Add integration contract tests
4. Verify: no imports from `core`, `skills`, `memory`

---

## 7. Contract Verification

- `tests/test_contract.py` — verifies integrations don't import core/providers
