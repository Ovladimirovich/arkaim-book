"""Tests for ServiceRegistry — замена @functools.cache."""
import pytest
from core.services.registry import ServiceRegistry


class TestServiceRegistry:
    def test_register_and_get(self):
        reg = ServiceRegistry()
        reg.register("foo", lambda: "bar")
        assert reg.get("foo") == "bar"

    def test_singleton_behavior(self):
        reg = ServiceRegistry()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return call_count

        reg.register("counter", factory)
        assert reg.get("counter") == 1
        assert reg.get("counter") == 1  # same instance
        assert call_count == 1  # factory called once

    def test_missing_service_raises(self):
        reg = ServiceRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get("nonexistent")

    def test_has(self):
        reg = ServiceRegistry()
        reg.register("x", lambda: 42)
        assert reg.has("x")
        assert not reg.has("y")

    def test_close_all_calls_cleanup(self):
        reg = ServiceRegistry()
        cleaned = []

        reg.register("svc", lambda: "instance", cleanup=lambda inst: cleaned.append(inst))
        reg.get("svc")
        reg.close_all()
        assert cleaned == ["instance"]

    def test_close_all_skips_uncalled(self):
        reg = ServiceRegistry()
        cleaned = []
        reg.register("svc", lambda: "instance", cleanup=lambda inst: cleaned.append(inst))
        # never called get()
        reg.close_all()
        assert cleaned == []

    def test_close_all_handles_cleanup_error(self):
        reg = ServiceRegistry()

        def bad_cleanup(inst):
            raise RuntimeError("cleanup failed")

        reg.register("svc", lambda: "instance", cleanup=bad_cleanup)
        reg.get("svc")
        reg.close_all()  # should not raise
