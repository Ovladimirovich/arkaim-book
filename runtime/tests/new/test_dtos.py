"""Тесты для core.dto — валидация запросов и моделей ответов."""
import pytest
from pydantic import ValidationError

from core.dto.requests import (
    ChatRequest, Message, BookAskRequest, BookGenerateRequest,
    VisualSceneRequest, VisualCharacterRequest, VisualLocationRequest,
    VisualFromSpeechRequest, VisualizeRequest,
)
from core.dto.responses import (
    SuccessResponse, ErrorResponse, ErrorDetail,
    HealthResponse, BookGenomeResponse, BookLayersResponse,
    ReaderProfileResponse, ReaderStatsResponse, VisualizeResponse,
)


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(messages=[{"role": "user", "content": "hello"}])
        assert len(req.messages) == 1
        assert req.stream is False

    def test_empty_messages_invalid(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[{"role": "invalid", "content": "test"}])

    def test_optional_fields(self):
        req = ChatRequest(messages=[{"role": "user", "content": "hi"}])
        assert req.session_id is None
        assert req.provider is None


class TestBookAskRequest:
    def test_valid(self):
        req = BookAskRequest(question="Кто такой Велик?")
        assert req.question == "Кто такой Велик?"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            BookAskRequest(question="ab")

    def test_context_optional(self):
        req = BookAskRequest(question="test question")
        assert req.context is None


class TestBookGenerateRequest:
    def test_valid(self):
        req = BookGenerateRequest(type="chapter", topic="History")
        assert req.auto_publish is False


class TestVisualSceneRequest:
    def test_valid(self):
        req = VisualSceneRequest(chapter=1, title="Scene 1")
        assert req.characters == []

    def test_invalid_chapter(self):
        with pytest.raises(ValidationError):
            VisualSceneRequest(chapter=0, title="test")


class TestVisualizeRequest:
    def test_valid(self):
        req = VisualizeRequest(chapter=1, scene_id="s1")
        assert req.reader_id is None


class TestSuccessResponse:
    def test_default(self):
        resp = SuccessResponse()
        assert resp.ok is True
        assert resp.data is None

    def test_with_data(self):
        resp = SuccessResponse(data={"key": "value"})
        assert resp.data == {"key": "value"}


class TestErrorResponse:
    def test_valid(self):
        resp = ErrorResponse(error=ErrorDetail(code="NOT_FOUND", message="Not found"))
        assert resp.ok is False
        assert resp.error.code == "NOT_FOUND"


class TestHealthResponse:
    def test_valid(self):
        resp = HealthResponse(status="ok", version="1.0.0")
        assert resp.status == "ok"


class TestBookGenomeResponse:
    def test_defaults(self):
        resp = BookGenomeResponse()
        assert resp.themes == []
        assert resp.characters == []


class TestReaderProfileResponse:
    def test_defaults(self):
        resp = ReaderProfileResponse(reader_id="r1")
        assert resp.questions_total == 0
        assert resp.topics == []


class TestReaderStatsResponse:
    def test_defaults(self):
        resp = ReaderStatsResponse()
        assert resp.total_readers == 0
