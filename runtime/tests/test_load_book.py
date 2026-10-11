"""Load-тесты для Book Intelligence через TestClient (без внешнего сервера)."""

import time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from core.main import app

    return TestClient(app)


class TestLoadBook:
    def test_sequential_50_health(self, client):
        for _ in range(50):
            r = client.get("/book/health")
            assert r.status_code == 200

    def test_sequential_50_layers(self, client):
        for _ in range(50):
            r = client.get("/book/layers")
            assert r.status_code == 200

    def test_sequential_50_genome(self, client):
        for _ in range(50):
            r = client.get("/book/genome")
            assert r.status_code in (200, 404)

    def test_mixed_100(self, client):
        endpoints = ["/book/health", "/book/layers", "/book/drafts", "/book/memory/stats"]
        t0 = time.perf_counter()
        for i in range(100):
            ep = endpoints[i % len(endpoints)]
            r = client.get(ep)
            assert r.status_code == 200
        elapsed = time.perf_counter() - t0
        print(f"\n  100 mixed requests: {elapsed * 1000:.0f}ms total, {elapsed / 100 * 1000:.0f}ms avg")
