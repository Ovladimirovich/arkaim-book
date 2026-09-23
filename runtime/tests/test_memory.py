"""Memory store tests: SQLite persistence, session isolation, edge cases."""


import pytest


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_memory.db")


@pytest.mark.asyncio
async def test_store_and_retrieve(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store(
        [{"role": "user", "content": "hello"}],
        "hi there",
        session_id="s1",
    )
    history = await ms.retrieve("hello", session_id="s1")
    assert len(history) >= 2
    assert history[-1]["role"] == "assistant"
    assert "hi there" in history[-1]["content"]


@pytest.mark.asyncio
async def test_session_isolation(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store([{"role": "user", "content": "a"}], "resp a", session_id="s1")
    await ms.store([{"role": "user", "content": "b"}], "resp b", session_id="s2")

    h1 = await ms.retrieve("", session_id="s1")
    h2 = await ms.retrieve("", session_id="s2")

    assert any("resp a" in m["content"] for m in h1)
    assert not any("resp b" in m["content"] for m in h1)
    assert any("resp b" in m["content"] for m in h2)


@pytest.mark.asyncio
async def test_health(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    h = await ms.health()
    assert h["status"] == "ok"
    assert h["type"] == "sqlite"
    assert h["conversations"] >= 0


@pytest.mark.asyncio
async def test_empty_session_returns_empty(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    history = await ms.retrieve("hello", session_id="nonexistent")
    assert history == []


@pytest.mark.asyncio
async def test_no_session_returns_empty(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    history = await ms.retrieve("hello", session_id=None)
    assert history == []


@pytest.mark.asyncio
async def test_close_then_reopen(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store([{"role": "user", "content": "x"}], "y", session_id="s1")
    await ms.close()

    ms2 = MemoryStore(db_path=db_path)
    history = await ms2.retrieve("x", session_id="s1")
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_store_handles_list_response(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store([{"role": "user", "content": "q"}], "", session_id="s1")
    history = await ms.retrieve("q", session_id="s1")
    assert any(m["role"] == "assistant" for m in history)


@pytest.mark.asyncio
async def test_leads_store_and_retrieve(db_path):
    from memory.leads import LeadStore

    ls = LeadStore(db_path=db_path)
    await ls.store_lead(session_id="s1", user_id="u1", user_text="хочу заказать", intent="booking")
    leads = await ls.get_leads()
    assert len(leads) >= 1
    assert leads[-1]["session_id"] == "s1"
    assert leads[-1]["intent"] == "booking"
