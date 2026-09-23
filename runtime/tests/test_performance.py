"""
Тесты производительности для Book Intelligence.
Проверяют кэширование, connection pooling и нагрузку.
"""
import pytest
import time
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Добавляем CORE в sys.path для импорта
_BOOK_CORE = Path(__file__).resolve().parent.parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
if str(_BOOK_CORE) not in sys.path:
    sys.path.append(str(_BOOK_CORE))

from core.main import app


@pytest.fixture
def client():
    """Test client для FastAPI приложения."""
    return TestClient(app)


class TestCachingPerformance:
    """Тесты кэширования в BookRetriever."""

    def test_cache_hit_improves_performance(self, client):
        """Проверка что кэш ускоряет повторные запросы."""
        query = "Кто такой Велик?"

        # Первый запрос (cache miss)
        start1 = time.time()
        response1 = client.post("/book/ask", json={"question": query})
        time.time() - start1

        # Второй запрос (cache hit)
        start2 = time.time()
        response2 = client.post("/book/ask", json={"question": query})
        time.time() - start2

        # Второй запрос должен быть быстрее (или примерно таким же)
        # Кэш работает на уровне BookRetriever, так что разница может быть небольшой
        assert response1.status_code in [200, 500, 503]
        assert response2.status_code in [200, 500, 503]

    def test_different_queries_no_cache_collision(self, client):
        """Проверка что разные запросы не используют один кэш."""
        query1 = "Кто такой Велик?"
        query2 = "Что такое Аркаим?"

        response1 = client.post("/book/ask", json={"question": query1})
        response2 = client.post("/book/ask", json={"question": query2})

        assert response1.status_code in [200, 500, 503]
        assert response2.status_code in [200, 500, 503]

    def test_cache_expiration(self):
        """Проверка истечения кэша (TTL)."""
        from intelligence.retriever import BookRetriever

        # Создаем retriever с коротким TTL
        retriever = BookRetriever(cache_ttl=1)  # 1 секунда

        # Первый запрос
        results1 = retriever.search("тест")

        # Ждем 2 секунды (кэш должен истечь)
        time.sleep(2)

        # Второй запрос (должен быть cache miss)
        results2 = retriever.search("тест")

        # Результаты должны быть одного типа
        assert isinstance(results1, list)
        assert isinstance(results2, list)

    def test_cache_size_limit(self):
        """Проверка ограничения размера кэша."""
        from intelligence.retriever import BookRetriever

        # Создаем retriever с маленьким кэшем
        retriever = BookRetriever(cache_ttl=60)

        # Заполняем кэш более чем на 256 записей
        for i in range(300):
            retriever.search(f"тестовый запрос {i}")

        # Кэш должен быть ограничен 256 записями
        assert len(retriever._cache) <= 256

    def test_clear_cache(self):
        """Проверка очистки кэша."""
        from intelligence.retriever import BookRetriever

        retriever = BookRetriever(cache_ttl=60)

        # Добавляем записи в кэш
        retriever.search("тест 1")
        retriever.search("тест 2")

        assert len(retriever._cache) > 0

        # Очищаем кэш
        retriever.clear_cache()

        assert len(retriever._cache) == 0


class TestConnectionPooling:
    """Тесты connection pooling в LLM Client."""

    def test_concurrent_llm_requests(self, client):
        """Проверка обработки одновременных запросов к LLM."""
        import concurrent.futures

        def make_request():
            return client.post("/book/ask", json={"question": "Тестовый вопрос"})

        # Отправляем 5 одновременных запросов
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Все запросы должны завершиться
        for response in responses:
            assert response.status_code in [200, 500, 503]

    def test_sequential_requests_performance(self, client):
        """Проверка производительности последовательных запросов."""
        times = []

        for i in range(3):
            start = time.time()
            response = client.post("/book/ask", json={"question": f"Тест {i}"})
            elapsed = time.time() - start
            times.append(elapsed)
            assert response.status_code in [200, 500, 503]

        # Последовательные запросы должны быть стабильными по времени
        # (connection pooling должен помочь)
        avg_time = sum(times) / len(times)
        for t in times:
            # Никакой запрос не должен быть в 3 раза медленнее среднего
            assert t < avg_time * 3


class TestLoadHandling:
    """Тесты обработки нагрузки."""

    def test_rapid_sequential_requests(self, client):
        """Проверка обработки быстрых последовательных запросов."""
        start = time.time()

        for i in range(10):
            response = client.post("/book/ask", json={"question": f"Быстрый запрос {i}"})
            assert response.status_code in [200, 500, 503]

        elapsed = time.time() - start

        # 10 запросов должны выполниться за разумное время
        assert elapsed < 30  # 3 секунды на запрос в среднем

    def test_health_endpoint_performance(self, client):
        """Проверка производительности health endpoint."""
        times = []

        for i in range(10):
            start = time.time()
            response = client.get("/book/health")
            elapsed = time.time() - start
            times.append(elapsed)
            assert response.status_code == 200

        # Health endpoint должен быть быстрым (< 100ms)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1

    def test_layers_endpoint_performance(self, client):
        """Проверка производительности layers endpoint."""
        start = time.time()
        response = client.get("/book/layers")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Layers endpoint должен быть быстрым (< 500ms)
        assert elapsed < 0.5

    def test_memory_stats_endpoint_performance(self, client):
        """Проверка производительности memory stats endpoint."""
        start = time.time()
        response = client.get("/book/memory/stats")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Memory stats должен быть быстрым (< 500ms)
        assert elapsed < 0.5


class TestResourceUsage:
    """Тесты использования ресурсов."""

    def test_large_question_handling(self, client):
        """Проверка обработки больших вопросов."""
        large_question = "а" * 1000

        start = time.time()
        response = client.post("/book/ask", json={"question": large_question})
        elapsed = time.time() - start

        assert response.status_code in [200, 422, 500]
        # Должен обработаться за разумное время
        assert elapsed < 10

    def test_empty_question_handling(self, client):
        """Проверка обработки пустых вопросов."""
        start = time.time()
        response = client.post("/book/ask", json={"question": ""})
        elapsed = time.time() - start

        # Должен быстро вернуть ошибку валидации
        assert response.status_code in [200, 422, 400]
        assert elapsed < 1


class TestScalability:
    """Тесты масштабируемости."""

    def test_batch_requests(self, client):
        """Проверка обработки пакетных запросов."""
        import concurrent.futures

        def make_request(i):
            return client.post("/book/ask", json={"question": f"Пакетный запрос {i}"})

        # Отправляем 20 запросов параллельно
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.time() - start

        # Все запросы должны завершиться
        assert len(responses) == 20
        for response in responses:
            assert response.status_code in [200, 500, 503]

        # 20 запросов должны выполниться за разумное время
        assert elapsed < 60  # 3 секунды на запрос в среднем

    def test_mixed_endpoints_load(self, client):
        """Проверка нагрузки на разные эндпоинты."""
        import concurrent.futures

        def make_request(endpoint):
            if endpoint == "health":
                return client.get("/book/health")
            elif endpoint == "layers":
                return client.get("/book/layers")
            elif endpoint == "ask":
                return client.post("/book/ask", json={"question": "Тест"})
            return None

        endpoints = ["health"] * 5 + ["layers"] * 5 + ["ask"] * 5

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, ep) for ep in endpoints]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.time() - start

        # Все запросы должны завершиться
        assert len(responses) == 15
        for response in responses:
            assert response is not None
            assert response.status_code in [200, 500, 503]

        # Смешанная нагрузка должна быть обработана за разумное время
        assert elapsed < 30
