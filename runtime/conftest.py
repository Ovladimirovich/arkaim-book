"""Root conftest.py — shared fixtures for test isolation.

Главная проблема: ProviderRegistry — singleton с class-level state.
Многие тесты мутируют _providers/_frozen/_health_state, что ломает
последующие тесты в полном suite.

Решение: conftest fixture сохраняет/восстанавливает state.
"""

import pytest
from core.provider_registry import ProviderRegistry


@pytest.fixture(autouse=False)
def isolated_provider_registry():
    """Сохраняет и восстанавливает ProviderRegistry state.

    Используется ТОЛЬКО в тестах, которые мутируют registry.
    Не autouse — только явно запрашивается.
    """
    # Save
    saved_providers = dict(ProviderRegistry._providers)
    saved_frozen = ProviderRegistry._frozen
    saved_health = dict(ProviderRegistry._health_state)
    saved_lock = ProviderRegistry._lock

    yield

    # Restore
    ProviderRegistry._providers = saved_providers
    ProviderRegistry._frozen = saved_frozen
    ProviderRegistry._health_state = saved_health
    ProviderRegistry._lock = saved_lock


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Очистить rate limit state между тестами."""
    yield
    try:
        import core.main as _main

        _main._rate_limits.clear()
    except Exception:
        pass
