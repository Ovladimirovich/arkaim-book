# Hermes Execution Contract

> **Hard freeze.** This document defines the single execution path, layer boundaries, state ownership, and forbidden patterns of the Hermes Runtime. Violations are architecture breaches.

---

## 1. Single Execution Path

There is exactly **one** execution path:

```text
Client
  ↓
Gateway   (port 8000 — transport layer, stateless)
  ↓ HTTP
Core      (port 8642 — AI runtime, stateful)
  ↓ Provider API
Provider  (GigaChat → OpenRouter)
```

Every request **must** follow this path. There is no bypass, no alternative route, no hidden channel.

### 1.1 What this means

- Integrations (Telegram, VK, Discord, WebUI) **always** go through Gateway.
- Gateway **always** proxies to Core.
- Core **always** calls providers through the Provider Registry.
- Providers are **never** called from Gateway, Integrations, or Skills.

---

## 2. Layer Boundaries

| Layer | Responsibility | State | Can call |
|---|---|---|---|
| **Gateway** | Transport, auth, rate-limit, normalize, proxy, observe | Stateless | Core only (HTTP) |
| **Core** | AI orchestration, provider chain, memory, skills, identity, tools, routing | Orchestration state | Providers only (API) |
| **Memory** | Persistence (conversations, leads) | Persistent state | Called by Core only |
| **Skills** | Context augmentation, classification, sanitization | No state | Nothing external |
| **Integrations** | Transport adaptation (normalize → Gateway) | Transport only | Gateway only (HTTP) |
| **Observability** | Logging, tracing, metrics | Ephemeral | All layers (import only) |

### 2.1 State ownership

- **Gateway**: MUST NOT hold state between requests. No conversation cache, no session store, no memory.
- **Core**: owns orchestration state (active request context, trace IDs). No persistent state.
- **Memory**: owns persistent state (SQLite). Only accessible through `memory.store.MemoryStore`.
- **Skills**: MUST NOT hold state. No DB connections, no file I/O beyond read-only config.
- **Integrations**: MUST NOT hold state. No dialog cache, no user store.

---

## 3. Forbidden Patterns

### 3.1 Gateway MUST NOT

- Call providers directly
- Store memory / conversations
- Execute skills
- Import `core.orchestrator`, `core.providers`, `core.router`
- Import `memory`, `skills`, `aiosqlite`
- Make decisions about routing, fallback, or provider selection

### 3.2 Core MUST NOT

- Import `gateway`, `integrations`
- Expose infrastructure details (provider chain, fallback, retry policy) to the user
- Leak provider identity in responses

### 3.3 Skills MUST NOT

- Import `core.orchestrator`, `core.providers`, `core.router`
- Import `httpx`, `requests`, `aiohttp`, `websockets`
- Call `asyncio.create_task`, `threading`, `multiprocessing`, `subprocess`, `os.system`
- Hold state between executions
- Make HTTP calls to any service
- Import or call Gateway

### 3.4 Integrations MUST NOT

- Import `core`, `skills`, `memory`
- Know about providers, orchestration, or skills
- Store conversation state
- Make decisions about response content

---

## 4. Identity Contract

Hermes presents itself as **Hermes**, an AI-powered cognitive agent. It MUST NOT:

- Identify as a model (GPT, GigaChat, Claude, etc.)
- Identify as an LLM or language model
- Expose its provider chain or fallback mechanism
- Disclose runtime architecture or orchestration details
- Expose provider metadata, version strings, or OAuth information

The **only** acceptable provider disclosure: *"I use GigaChat as my cognitive provider"* — and only when directly asked.

---

## 5. Contract Verification

The following test modules enforce this contract:

- `tests/test_contract.py` — layer import isolation
- `tests/test_gateway.py` — gateway dumbness guarantees
- `tests/test_core.py` — core isolation
- `tests/test_identity.py` — identity integrity
