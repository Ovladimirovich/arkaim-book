"""Auto-override auth dependency for all tests using core.main.app."""
from core.main import app
from auth.rbac import get_current_user

async def _fake_user():
    return {
        "user_id": "test-user",
        "role": "admin",
        "provider": "test",
        "username": "tester",
        "display_name": "Test User",
    }

app.dependency_overrides[get_current_user] = _fake_user
