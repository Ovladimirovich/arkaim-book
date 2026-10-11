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


@pytest.mark.asyncio
async def test_ask_exchange_persists_full_answer_and_session_summary(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store_exchange(
        session_id="ask-session-1",
        user_id="reader-1",
        question="Кто такой Аркаим?",
        answer="Аркаим — город из книги.",
        metadata={
            "source": "pulse",
            "provenance": [{"type": "theme", "name": "Аркаим"}],
            "pulse_confidence": 0.94,
            "llm_used": False,
        },
    )

    sessions = await ms.get_user_sessions("reader-1")
    full = await ms.get_user_history_full("reader-1", session_id="ask-session-1")

    assert sessions == [
        {
            "session_id": "ask-session-1",
            "created_at": full[0]["created_at"],
            "last_question_at": full[-1]["created_at"],
            "question_count": 1,
        }
    ]
    assert [item["role"] for item in full] == ["user", "assistant"]
    assert full[1]["content"] == "Аркаим — город из книги."
    assert full[1]["metadata"]["source"] == "pulse"
    assert full[1]["metadata"]["provenance"][0]["name"] == "Аркаим"
    assert full[1]["metadata"]["pulse_confidence"] == 0.94


@pytest.mark.asyncio
async def test_history_is_isolated_between_readers(db_path):
    from memory.store import MemoryStore

    ms = MemoryStore(db_path=db_path)
    await ms.store_exchange(
        session_id="shared-looking-id",
        user_id="reader-a",
        question="private A",
        answer="answer A",
        metadata={"source": "pulse"},
    )

    assert await ms.get_user_sessions("reader-a")
    assert await ms.get_user_sessions("reader-b") == []
    assert await ms.get_user_history_full("reader-b", session_id="shared-looking-id") == []
