# Hermes Skill Contract

> **Hard freeze.** Skills are passive plugins within Hermes Runtime. They are NOT execution units, NOT mini-agents, and NOT a second orchestrator. Violations must be rejected at code review.

---

## 1. What a Skill IS

A Skill is a **passive context augmentation layer**. It executes within the Core orchestrator's execution loop and can only:

| Operation | Description |
|---|---|
| `augment` | Inject system prompts (identity, personality, rules) |
| `classify` | Detect intent, extract entities, score leads |
| `sanitize` | Clean provider responses (identity leaks, forbidden patterns) |
| `inject` | Add knowledge-base context to the request |
| `extract` | Parse structured data from user input (pricing, area, city) |

### 1.1 Skill lifecycle

```python
# The ONLY thing a skill can return:
SkillResult(
    handled=False,       # True only if skill fully resolves the request (no LLM needed)
    response=None,       # Direct response if handled=True
    context="",          # KB context to inject into LLM prompt
    system_prompt="",    # System prompt fragment to prepend
    metadata={},         # Structured data for observability
)
```

---

## 2. What a Skill MUST NOT do

### 2.1 Forbidden imports

A Skill file MUST NOT import:

- `core.orchestrator`
- `core.providers` (any module)
- `core.router`
- `core.main`
- `gateway` (any module)
- `httpx`, `requests`, `aiohttp`, `urllib3`, `httplib2`
- `asyncio` (except `asyncio.sleep` with review)
- `threading`, `multiprocessing`, `concurrent.futures`
- `subprocess`, `os.system`, `os.popen`
- `websockets`, `socket`
- `aiosqlite`, `sqlite3` (any DB driver)

### 2.2 Forbidden operations

- Call any provider API directly
- Initiate HTTP calls
- Start background tasks (`asyncio.create_task`, `loop.create_task`)
- Spawn threads or processes
- Store state between executions (no module-level mutable state)
- Read or write to the filesystem (except read-only config/knowledge-base at import time)
- Import or call another Skill directly
- Control or override the orchestrator's execution flow
- Access or modify the provider chain
- Route execution based on business logic

---

## 3. Skill Interface

```python
class Skill(ABC):
    name: str = ""
    priority: int = 0       # Lower = runs first

    @abstractmethod
    async def execute(self, ctx: SkillContext) -> SkillResult:
        ...

    async def post_process(self, response: str, ctx: SkillContext) -> str:
        return response
```

### 3.1 Execution order

Skills are sorted by `priority` (ascending). Lower priority runs first.

- **Identity skills**: priority -10 (inject system prompt before any logic)
- **Detection skills**: priority 0–10 (classify intent, extract entities)
- **Pricing/calculator skills**: priority 20 (direct response, bypasses LLM)
- **Knowledge/context skills**: priority 30 (inject KB into LLM context)

### 3.2 `handled = True` rules

If a Skill returns `handled=True`, the orchestrator:

- Uses `response` as the final answer
- Skips all remaining skills
- Skips the provider chain entirely
- WARNING: `handled=True` bypasses the LLM. Use only for deterministic responses (pricing, calculator, form responses).

---

## 4. Skill Isolation

- Skills share **no state** with each other
- Skills cannot call each other
- Each skill receives a fresh `SkillContext` per execution
- Skills cannot access the provider registry
- Skills cannot access the orchestrator's internal state
- The `memory` object in `SkillContext` is limited to `retrieve()` and `store_lead()` — no raw DB access

---

## 5. Business Pack Contract

A Business Pack is a directory loaded at startup via `BUSINESS_PACK` env var:

```
hermes-business-potolki/
├── skills/
│   ├── base.py           (vendored minimal — Skill, SkillContext, SkillResult)
│   ├── sanitizer.py      (vendored minimal — sanitize_response)
│   ├── _synonyms.py
│   ├── identity.py
│   ├── lead_detection.py
│   ├── pricing.py
│   └── rag.py
├── kb/                   (knowledge base files)
├── prompts/              (SOUL.md, system prompts)
└── pyproject.toml
```

The Business Pack:

- MUST be an independent project with its own tests and git history
- MUST NOT depend on the runtime for testing (vendors base classes)
- MUST NOT import from the runtime's internal modules
- MAY import from `skills.base` and `skills.sanitizer` (resolves to runtime's copies at runtime, to local copies during standalone testing)

---

## 6. Contract Verification

- `tests/test_skill_contract.py` (to be created)
- `tests/test_identity.py` — identity leak detection
