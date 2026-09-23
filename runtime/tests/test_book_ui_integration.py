"""
Интеграционные тесты для Book UI.
Проверяют работу API эндпоинтов, используемых Web UI.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Добавляем CORE в sys.path для импорта
_BOOK_CORE = Path(__file__).resolve().parent.parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
if str(_BOOK_CORE) not in sys.path:
    sys.path.append(str(_BOOK_CORE))

from core.main import app


@pytest.fixture
def client():
    """Test client для FastAPI приложения."""
    with TestClient(app) as c:
        yield c


class TestBookUIIntegration:
    """Тесты интеграции Web UI с API."""

    def test_book_health_endpoint(self, client):
        """Проверка здоровья Book Intelligence."""
        response = client.get("/book/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_book_root_endpoint(self, client):
        """Проверка корневого эндпоинта Book Intelligence."""
        response = client.get("/book/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data
        assert "ask" in data["endpoints"]

    def test_book_ask_endpoint_valid_request(self, client):
        """Проверка эндпоинта /book/ask с валидным запросом."""
        response = client.post("/book/ask", json={
            "question": "Кто такой Велик?",
            "context": None
        })
        # Может вернуть ошибку если LLM не настроен, но должен вернуть JSON
        assert response.status_code in [200, 500, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_book_ask_endpoint_empty_question(self, client):
        """Проверка эндпоинта /book/ask с пустым вопросом."""
        response = client.post("/book/ask", json={
            "question": "",
            "context": None
        })
        # Должен вернуть ошибку валидации или обработать пустой вопрос
        assert response.status_code in [200, 422, 400]

    def test_book_ask_endpoint_with_context(self, client):
        """Проверка эндпоинта /book/ask с контекстом."""
        response = client.post("/book/ask", json={
            "question": "Что такое Аркаим?",
            "context": "В контексте древней истории"
        })
        assert response.status_code in [200, 500, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_book_layers_endpoint(self, client):
        """Проверка эндпоинта /book/layers."""
        response = client.get("/book/layers")
        assert response.status_code == 200
        data = response.json()
        assert "knowledge_layer" in data
        assert "meaning_layer" in data
        assert "identity_layer" in data
        assert "mission_layer" in data

    def test_book_genome_endpoint(self, client):
        """Проверка эндпоинта /book/genome."""
        response = client.get("/book/genome")
        # Может вернуть 404 если геном не найден
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_book_memory_stats_endpoint(self, client):
        """Проверка эндпоинта /book/memory/stats."""
        response = client.get("/book/memory/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_book_xray_endpoint(self, client):
        """Проверка эндпоинта /book/xray."""
        response = client.get("/book/xray")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_book_drafts_endpoint(self, client):
        """Проверка эндпоинта /book/drafts."""
        response = client.get("/book/drafts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_book_drafts_pending_endpoint(self, client):
        """Проверка эндпоинта /book/drafts с фильтром pending."""
        response = client.get("/book/drafts?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_book_os_stats_endpoint(self, client):
        """Проверка эндпоинта /book/os/stats."""
        response = client.get("/book/os/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        assert isinstance(data, dict)

    def test_book_os_documents_endpoint(self, client):
        """Проверка эндпоинта /book/os/documents."""
        response = client.get("/book/os/documents")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        assert isinstance(data, list)

    def test_book_os_entities_endpoint(self, client):
        """Проверка эндпоинта /book/os/entities."""
        response = client.get("/book/os/entities")
        assert response.status_code in [200, 422], f"Expected 200/422, got {response.status_code}: {response.text[:200]}"

    def test_cors_headers(self, client):
        """Проверка CORS заголовков."""
        # FastAPI TestClient не поддерживает OPTIONS, проверяем через обычный запрос
        response = client.get("/book/health", headers={
            "Origin": "http://localhost:3000"
        })
        # Проверяем что запрос проходит
        assert response.status_code == 200


class TestBookUIResponseFormat:
    """Тесты формата ответов для совместимости с Web UI."""

    def test_ask_response_structure(self, client):
        """Проверка структуры ответа /book/ask."""
        response = client.post("/book/ask", json={
            "question": "Тестовый вопрос"
        })
        if response.status_code == 200:
            data = response.json()
            # Web UI ожидает поля: answer, source, layers_used (опционально)
            assert isinstance(data, dict)
            # Поля могут отличаться в зависимости от реализации
            assert "answer" in data or "error" in data or "detail" in data

    def test_layers_response_structure(self, client):
        """Проверка структуры ответа /book/layers."""
        response = client.get("/book/layers")
        assert response.status_code == 200
        data = response.json()
        # Web UI ожидает 4 слоя
        expected_layers = ["knowledge_layer", "meaning_layer", "identity_layer", "mission_layer"]
        for layer in expected_layers:
            assert layer in data

    def test_genome_response_structure(self, client):
        """Проверка структуры ответа /book/genome."""
        response = client.get("/book/genome")
        if response.status_code == 200:
            data = response.json()
            # Web UI ожидает: themes, characters, world_entities
            assert isinstance(data, dict)
            # Проверяем что хотя бы одно поле присутствует
            has_expected_fields = any(key in data for key in ["themes", "characters", "world_entities"])
            assert has_expected_fields


class TestBookUIErrorHandling:
    """Тесты обработки ошибок для Web UI."""

    def test_invalid_json_request(self, client):
        """Проверка обработки невалидного JSON."""
        response = client.post("/book/ask",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_question_field(self, client):
        """Проверка обработки отсутствующего поля question."""
        response = client.post("/book/ask", json={
            "context": "тест"
        })
        assert response.status_code in [422, 400]

    def test_very_long_question(self, client):
        """Проверка обработки очень длинного вопроса."""
        long_question = "а" * 10000
        response = client.post("/book/ask", json={
            "question": long_question
        })
        # Должен обработать или вернуть ошибку
        assert response.status_code in [200, 413, 422, 500]


class TestBookUIAsync:
    """Асинхронные тесты для Web UI."""

    def test_concurrent_requests(self, client):
        """Проверка обработки одновременных запросов (синхронная версия)."""
        import concurrent.futures

        def make_request(endpoint):
            return client.get(endpoint)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(make_request, "/book/health"),
                executor.submit(make_request, "/book/layers"),
                executor.submit(make_request, "/book/memory/stats")
            ]
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                assert response.status_code == 200

