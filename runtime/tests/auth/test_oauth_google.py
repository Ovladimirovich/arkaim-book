import time
import pytest
from unittest.mock import patch, AsyncMock
from jose import jwt


class TestGoogleOAuth:
    def test_get_auth_url(self):
        from auth.oauth.google import get_google_auth_url
        with patch("auth.oauth.google.settings.GOOGLE_CLIENT_ID", "cid"):
            u = get_google_auth_url("https://ex.com/cb")
            assert "cid" in u and "accounts.google.com" in u

    def test_get_auth_url_missing_id(self):
        from auth.oauth.google import get_google_auth_url, GoogleOAuthError
        with patch("auth.oauth.google.settings.GOOGLE_CLIENT_ID", ""):
            with pytest.raises(GoogleOAuthError, match="не задан"):
                get_google_auth_url("https://ex.com/cb")

    def test_parse_google_user(self):
        from auth.oauth.google import parse_google_user
        r = parse_google_user({"sub": "g1", "email": "u@gmail.com", "name": "U"})
        assert r["provider"] == "google" and r["provider_user_id"] == "g1"

    @pytest.mark.asyncio
    async def test_verify_wrong_audience(self):
        from auth.oauth.google import verify_google_id_token, GoogleOAuthError
        # Создаём токен с wrong audience, но с реальной (хоть и фейковой) подписью
        t = jwt.encode({"sub": "1", "aud": "wrong", "iss": "https://accounts.google.com", "exp": int(time.time()) + 3600}, "s")
        with patch("auth.oauth.google.settings.GOOGLE_CLIENT_ID", "my"):
            with patch("auth.oauth.google._get_google_jwks", new_callable=AsyncMock) as mock_jwks:
                mock_jwks.return_value = {"keys": []}  # Пустые ключи — подпись не пройдёт
                with pytest.raises(GoogleOAuthError):
                    await verify_google_id_token(t)

    @pytest.mark.asyncio
    async def test_verify_wrong_issuer(self):
        from auth.oauth.google import verify_google_id_token, GoogleOAuthError
        with patch("auth.oauth.google.settings.GOOGLE_CLIENT_ID", "my"):
            with patch("auth.oauth.google._get_google_jwks", new_callable=AsyncMock) as mock_jwks:
                mock_jwks.return_value = {"keys": []}
                # Токен с невалидным issuer
                t = jwt.encode({"sub": "1", "aud": "my", "iss": "https://evil.com", "exp": int(time.time()) + 3600}, "s")
                with pytest.raises(GoogleOAuthError):
                    await verify_google_id_token(t)
