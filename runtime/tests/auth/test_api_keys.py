"""Тесты для auth/api_keys.py — генерация, хэширование и маскирование API-ключей."""

import hashlib

import pytest

from auth.api_keys import generate_api_key, mask_api_key


class TestGenerateApiKey:
    """Тесты генерации API-ключей (возвращает tuple: raw, hash, prefix)."""

    def test_returns_tuple(self):
        """Проверка, что функция возвращает кортеж из 3 элементов."""
        key, key_hash, prefix = generate_api_key()
        assert isinstance(key, str)
        assert isinstance(key_hash, str)
        assert isinstance(prefix, str)

    def test_raw_key_has_valid_length(self):
        """Длина сырого ключа должна быть > 20 символов (base64 url-safe)."""
        key, _, _ = generate_api_key()
        assert len(key) > 20

    def test_hash_is_sha256(self):
        """Хэш должен быть SHA-256 (64 hex символа)."""
        _, key_hash, _ = generate_api_key()
        assert len(key_hash) == 64, "SHA-256 хэш должен быть 64 hex символа"
        int(key_hash, 16)  # проверка, что это hex

    def test_hash_matches_key(self):
        """Хэш должен быть SHA-256 от сырого ключа."""
        key, key_hash, _ = generate_api_key()
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert key_hash == expected

    def test_prefix_is_first_chars(self):
        """Префикс — первые 8 символов сырого ключа."""
        key, _, prefix = generate_api_key()
        assert prefix == key[:8]

    def test_prefix_length(self):
        """Длина префикса — 8 символов."""
        _, _, prefix = generate_api_key()
        assert len(prefix) == 8

    def test_generates_unique_keys(self):
        """Каждый вызов generate_api_key должен возвращать уникальный ключ."""
        keys = {generate_api_key()[0] for _ in range(100)}
        assert len(keys) == 100, "Ключи не уникальны"

    def test_generates_unique_hashes(self):
        """Каждый вызов должен возвращать уникальный хэш."""
        hashes = {generate_api_key()[1] for _ in range(100)}
        assert len(hashes) == 100, "Хэши не уникальны"


class TestMaskApiKey:
    """Тесты маскирования API-ключей (mask_api_key).
    
    Реальная реализация: mask_api_key(key) → первые PREFIX_LEN (8) + ... + последние 4
    Для ключей длиной <= PREFIX_LEN возвращает как есть.
    """

    def test_mask_long_key(self):
        """Маскирование: первые 8 + ... + последние 4."""
        key = "abcdefghijklmnopqrstuvwxyz0123456789"
        masked = mask_api_key(key)
        assert masked.startswith("abcdefgh")
        assert masked.endswith("6789")
        assert "..." in masked

    def test_mask_empty_key(self):
        """Пустой ключ возвращает пустую строку."""
        assert mask_api_key("") == ""
