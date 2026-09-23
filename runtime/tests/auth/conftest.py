"""Фикстуры для тестов auth-пакета."""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from auth.tokens import create_access_token


# ── Настройка окружения для тестов ────────────────────
@pytest.fixture(scope="session", autouse=True)
def _setup_test_env():
    """Устанавливает переменные окружения для тестов."""
    import os
    os.environ.setdefault("SESSION_SECRET", "test-secret-key-not-for-production")
    os.environ.setdefault("AUTH_DB_PATH", ":memory:")
    os.environ.setdefault("HERMES_API_KEY", "test-service-key")
    os.environ.setdefault("GATEWAY_HOST", "127.0.0.1")
    os.environ.setdefault("GATEWAY_PORT", "8080")
    os.environ.setdefault("CORE_HOST", "127.0.0.1")
    os.environ.setdefault("CORE_PORT", "8642")


# ── UserStore in-memory ────────────────────────────────
@pytest_asyncio.fixture
async def user_store():
    """In-memory UserStore для тестов."""
    from auth.users import UserStore
    store = UserStore(db_path=":memory:")
    await store._ensure_db()
    yield store
    await store.close()


# ── Тестовые пользователи ─────────────────────────────
@pytest_asyncio.fixture
async def test_user_reader(user_store) -> dict:
    """Создаёт тестового пользователя с ролью reader."""
    user = await user_store.upsert_user(
        provider="telegram",
        provider_user_id="12345",
        username="test_reader",
        display_name="Test Reader",
        role="reader",
    )
    return user


@pytest_asyncio.fixture
async def test_user_editor(user_store) -> dict:
    """Создаёт тестового пользователя с ролью editor."""
    user = await user_store.upsert_user(
        provider="telegram",
        provider_user_id="67890",
        username="test_editor",
        display_name="Test Editor",
        role="editor",
    )
    return user


@pytest_asyncio.fixture
async def test_user_admin(user_store) -> dict:
    """Создаёт тестового пользователя с ролью admin."""
    user = await user_store.upsert_user(
        provider="google",
        provider_user_id="admin-001",
        username="test_admin",
        display_name="Test Admin",
        role="admin",
    )
    return user


# ── JWT токены ────────────────────────────────────────
@pytest.fixture
def valid_token_reader(test_user_reader: dict) -> str:
    """Валидный JWT токен для пользователя reader."""
    return create_access_token(
        subject=test_user_reader["id"],
        role=test_user_reader["role"],
        provider=test_user_reader["provider"],
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture
def valid_token_admin(test_user_admin: dict) -> str:
    """Валидный JWT токен для пользователя admin."""
    return create_access_token(
        subject=test_user_admin["id"],
        role=test_user_admin["role"],
        provider=test_user_admin["provider"],
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture
def expired_token() -> str:
    """Просроченный JWT токен."""
    return create_access_token(
        subject="any-user",
        role="reader",
        provider="telegram",
        expires_delta=timedelta(hours=-1),  # просрочен на 1 час
    )


@pytest.fixture
def invalid_token() -> str:
    """Невалидный JWT токен (мусорная строка)."""
    return "invalid.token.here"


@pytest.fixture
def tampered_token(valid_token_reader: str) -> str:
    """JWT токен с изменённой подписью."""
    parts = valid_token_reader.split(".")
    if len(parts) == 3:
        parts[2] = "tampered_signature"
    return ".".join(parts)


# ── API-ключи ─────────────────────────────────────────
@pytest.fixture
def test_api_key_hash() -> str:
    """Хэш тестового API-ключа."""
    import hashlib
    return hashlib.sha256("test-api-key-12345".encode()).hexdigest()


@pytest.fixture
def test_api_key_prefix() -> str:
    """Префикс тестового API-ключа."""
    return "key_test"
