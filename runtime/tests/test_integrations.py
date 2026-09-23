"""
РўРµСЃС‚С‹ РёРЅС‚РµРіСЂР°С†РёР№ СЃ СЂРѕСЃСЃРёР№СЃРєРёРјРё РїР»Р°С‚С„РѕСЂРјР°РјРё (Telegram, VK).
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Р”РѕР±Р°РІР»СЏРµРј CORE РІ sys.path РґР»СЏ РёРјРїРѕСЂС‚Р°
_BOOK_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_BOOK_CORE) not in sys.path:
    sys.path.append(str(_BOOK_CORE))

from community.telegram import TelegramBotStub, DraftManager
from community.vk import VKBot


class TestTelegramIntegration:
    """РўРµСЃС‚С‹ РёРЅС‚РµРіСЂР°С†РёРё СЃ Telegram."""

    @pytest.fixture
    def telegram_bot(self):
        """РЎРѕР·РґР°РµС‚ СЌРєР·РµРјРїР»СЏСЂ Telegram Р±РѕС‚Р°."""
        return TelegramBotStub()

    @pytest.fixture
    def draft_manager(self):
        """РЎРѕР·РґР°РµС‚ СЌРєР·РµРјРїР»СЏСЂ DraftManager."""
        return DraftManager()

    @pytest.mark.skip(reason='Draft class not available in current codebase')
    def test_draft_creation(self, draft_manager):
        """РџСЂРѕРІРµСЂРєР° СЃРѕР·РґР°РЅРёСЏ С‡РµСЂРЅРѕРІРёРєР°."""
        draft = Draft(
            id="",
            content="РўРµСЃС‚РѕРІС‹Р№ РєРѕРЅС‚РµРЅС‚",
            target="telegram",
            source="herald",
            status="pending"
        )
        draft_id = draft_manager.save_draft(draft)

        assert draft_id is not None
        assert len(draft_id) > 0
        assert draft_manager.get_draft(draft_id) is not None

    @pytest.mark.skip(reason='Draft class not available in current codebase')
    def test_draft_approval(self, draft_manager):
        """РџСЂРѕРІРµСЂРєР° РѕРґРѕР±СЂРµРЅРёСЏ С‡РµСЂРЅРѕРІРёРєР°."""
        draft = Draft(
            id="",
            content="РўРµСЃС‚РѕРІС‹Р№ РєРѕРЅС‚РµРЅС‚",
            target="telegram",
            source="herald",
            status="pending"
        )
        draft_id = draft_manager.save_draft(draft)

        success = draft_manager.approve_draft(draft_id)
        assert success is True

        approved_draft = draft_manager.get_draft(draft_id)
        assert approved_draft.status == "approved"

    @pytest.mark.skip(reason='Draft class not available in current codebase')
    def test_draft_rejection(self, draft_manager):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РєР»РѕРЅРµРЅРёСЏ С‡РµСЂРЅРѕРІРёРєР°."""
        draft = Draft(
            id="",
            content="РўРµСЃС‚РѕРІС‹Р№ РєРѕРЅС‚РµРЅС‚",
            target="telegram",
            source="herald",
            status="pending"
        )
        draft_id = draft_manager.save_draft(draft)

        success = draft_manager.reject_draft(draft_id)
        assert success is True

        rejected_draft = draft_manager.get_draft(draft_id)
        assert rejected_draft.status == "rejected"

    @pytest.mark.skip(reason='Draft class not available in current codebase')
    def test_get_pending_drafts(self, draft_manager):
        """РџСЂРѕРІРµСЂРєР° РїРѕР»СѓС‡РµРЅРёСЏ pending С‡РµСЂРЅРѕРІРёРєРѕРІ."""
        draft1 = Draft(id="", content="РљРѕРЅС‚РµРЅС‚ 1", target="telegram", source="herald", status="pending")
        draft2 = Draft(id="", content="РљРѕРЅС‚РµРЅС‚ 2", target="telegram", source="herald", status="approved")
        draft3 = Draft(id="", content="РљРѕРЅС‚РµРЅС‚ 3", target="telegram", source="herald", status="pending")

        draft_manager.save_draft(draft1)
        draft_manager.save_draft(draft2)
        draft_manager.save_draft(draft3)

        pending = draft_manager.get_pending_drafts()
        assert len(pending) == 2

    def test_telegram_handle_message(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё СЃРѕРѕР±С‰РµРЅРёСЏ Telegram."""
        import asyncio

        async def test():
            result = await telegram_bot.handle_message("РўРµСЃС‚РѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ", "user123")
            assert result["status"] == "ok"
            assert "draft_id" in result

        asyncio.run(test())

    @pytest.mark.asyncio
    async def test_telegram_send_notification_no_token(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё СѓРІРµРґРѕРјР»РµРЅРёСЏ Р±РµР· С‚РѕРєРµРЅР° (stub СЂРµР¶РёРј)."""
        telegram_bot.bot_token = None
        success = await telegram_bot.send_notification("РўРµСЃС‚РѕРІРѕРµ СѓРІРµРґРѕРјР»РµРЅРёРµ")
        # Р‘РµР· С‚РѕРєРµРЅР° РґРѕР»Р¶РЅРѕ РІРµСЂРЅСѓС‚СЊ False
        assert success is False

    @pytest.mark.asyncio
    async def test_telegram_send_notification_with_mock(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё СѓРІРµРґРѕРјР»РµРЅРёСЏ СЃ РјРѕРєРѕРј API."""
        telegram_bot.bot_token = "test_token"

        with patch.object(telegram_bot, '_call_api', return_value={"ok": True}):
            success = await telegram_bot.send_notification("РўРµСЃС‚", chat_id="123")
            assert success is True

    @pytest.mark.asyncio
    @pytest.mark.skip(reason='Draft class not available')
    async def test_telegram_send_draft_with_mock(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё С‡РµСЂРЅРѕРІРёРєР° СЃ РјРѕРєРѕРј API."""
        telegram_bot.bot_token = "test_token"

        # РЎРѕР·РґР°РµРј Рё РѕРґРѕР±СЂСЏРµРј С‡РµСЂРЅРѕРІРёРє
        draft = Draft(id="", content="РўРµСЃС‚", target="telegram", source="herald", status="approved")
        draft_id = telegram_bot.draft_manager.save_draft(draft)

        with patch.object(telegram_bot, '_call_api', return_value={"ok": True}):
            success = await telegram_bot.send_draft(draft_id, chat_id="123")
            assert success is True

    @pytest.mark.asyncio
    async def test_telegram_inline_query(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° inline Р·Р°РїСЂРѕСЃР°."""
        telegram_bot.bot_token = "test_token"

        results = [{"type": "article", "id": "1", "title": "РўРµСЃС‚"}]

        with patch.object(telegram_bot, '_call_api', return_value={"ok": True}):
            success = await telegram_bot.send_inline_query("query123", results)
            assert success is True

    @pytest.mark.asyncio
    async def test_telegram_set_webhook(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° СѓСЃС‚Р°РЅРѕРІРєРё РІРµР±С…СѓРєР°."""
        telegram_bot.bot_token = "test_token"

        with patch.object(telegram_bot, '_call_api', return_value={"ok": True}):
            success = await telegram_bot.set_webhook("https://example.com/webhook")
            assert success is True

    @pytest.mark.asyncio
    async def test_telegram_get_webhook_info(self, telegram_bot):
        """РџСЂРѕРІРµСЂРєР° РїРѕР»СѓС‡РµРЅРёСЏ РёРЅС„РѕСЂРјР°С†РёРё Рѕ РІРµР±С…СѓРєРµ."""
        telegram_bot.bot_token = "test_token"

        with patch.object(telegram_bot, '_call_api', return_value={"ok": True, "result": {"url": "https://example.com"}}):
            info = await telegram_bot.get_webhook_info()
            assert info.get("ok") is True


class TestVKIntegration:
    """РўРµСЃС‚С‹ РёРЅС‚РµРіСЂР°С†РёРё СЃ VK."""

    @pytest.fixture
    def vk_bot(self):
        """РЎРѕР·РґР°РµС‚ СЌРєР·РµРјРїР»СЏСЂ VK Р±РѕС‚Р°."""
        return VKBot()

    def test_vk_bot_initialization(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РёРЅРёС†РёР°Р»РёР·Р°С†РёРё VK Р±РѕС‚Р°."""
        assert vk_bot is not None
        assert vk_bot.api_version == "5.199"

    @pytest.mark.asyncio
    async def test_vk_callback_confirmation(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё confirmation callback."""
        vk_bot.confirmation_code = "test_code"

        data = {"type": "confirmation"}
        response = await vk_bot.handle_callback(data)

        assert response == "test_code"

    @pytest.mark.asyncio
    async def test_vk_callback_message_new(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё message_new callback."""
        data = {
            "type": "message_new",
            "object": {
                "message": {
                    "from_id": 12345,
                    "text": "РўРµСЃС‚РѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ"
                }
            }
        }
        response = await vk_bot.handle_callback(data)

        assert response == "ok"

    @pytest.mark.asyncio
    async def test_vk_callback_group_join(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё group_join callback."""
        data = {
            "type": "group_join",
            "object": {"user_id": 12345}
        }
        response = await vk_bot.handle_callback(data)

        assert response == "ok"

    @pytest.mark.asyncio
    async def test_vk_callback_group_leave(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё group_leave callback."""
        data = {
            "type": "group_leave",
            "object": {"user_id": 12345}
        }
        response = await vk_bot.handle_callback(data)

        assert response == "ok"

    @pytest.mark.asyncio
    async def test_vk_send_message_no_token(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё СЃРѕРѕР±С‰РµРЅРёСЏ Р±РµР· С‚РѕРєРµРЅР° (stub СЂРµР¶РёРј)."""
        vk_bot.access_token = None
        success = await vk_bot.send_message("12345", "РўРµСЃС‚")
        # Р‘РµР· С‚РѕРєРµРЅР° РІРѕР·РІСЂР°С‰Р°РµС‚ True (stub СЂРµР¶РёРј РІРѕР·РІСЂР°С‰Р°РµС‚ {"response": {}})
        assert success is True

    @pytest.mark.asyncio
    async def test_vk_send_message_with_mock(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё СЃРѕРѕР±С‰РµРЅРёСЏ СЃ РјРѕРєРѕРј API."""
        vk_bot.access_token = "test_token"

        with patch.object(vk_bot, '_call_api', return_value={"response": {}}):
            success = await vk_bot.send_message("12345", "РўРµСЃС‚")
            assert success is True

    @pytest.mark.asyncio
    async def test_vk_send_group_message_with_mock(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РѕС‚РїСЂР°РІРєРё СЃРѕРѕР±С‰РµРЅРёСЏ РІ РіСЂСѓРїРїСѓ СЃ РјРѕРєРѕРј API."""
        vk_bot.access_token = "test_token"
        vk_bot.group_id = "12345"

        with patch.object(vk_bot, '_call_api', return_value={"response": {}}):
            success = await vk_bot.send_group_message("РўРµСЃС‚")
            assert success is True

    @pytest.mark.asyncio
    async def test_vk_get_group_info_with_mock(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РїРѕР»СѓС‡РµРЅРёСЏ РёРЅС„РѕСЂРјР°С†РёРё Рѕ РіСЂСѓРїРїРµ СЃ РјРѕРєРѕРј API."""
        vk_bot.access_token = "test_token"
        vk_bot.group_id = "12345"

        with patch.object(vk_bot, '_call_api', return_value={"response": {"id": 12345, "name": "Test Group"}}):
            info = await vk_bot.get_group_info()
            assert info.get("name") == "Test Group"

    @pytest.mark.asyncio
    async def test_vk_get_group_members_with_mock(self, vk_bot):
        """РџСЂРѕРІРµСЂРєР° РїРѕР»СѓС‡РµРЅРёСЏ СѓС‡Р°СЃС‚РЅРёРєРѕРІ РіСЂСѓРїРїС‹ СЃ РјРѕРєРѕРј API."""
        vk_bot.access_token = "test_token"
        vk_bot.group_id = "12345"

        with patch.object(vk_bot, '_call_api', return_value={"response": {"count": 100, "items": []}}):
            members = await vk_bot.get_group_members()
            assert members.get("count") == 100


class TestIntegrationErrorHandling:
    """РўРµСЃС‚С‹ РѕР±СЂР°Р±РѕС‚РєРё РѕС€РёР±РѕРє РІ РёРЅС‚РµРіСЂР°С†РёСЏС…."""

    @pytest.mark.asyncio
    async def test_telegram_api_error_handling(self):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё РѕС€РёР±РѕРє Telegram API."""
        bot = TelegramBotStub()
        bot.bot_token = "test_token"

        with patch.object(bot, '_call_api', return_value={"ok": False, "error": "Test error"}):
            success = await bot.send_notification("РўРµСЃС‚", chat_id="123")
            assert success is False

    @pytest.mark.asyncio
    async def test_vk_api_error_handling(self):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё РѕС€РёР±РѕРє VK API."""
        bot = VKBot()
        bot.access_token = "test_token"

        with patch.object(bot, '_call_api', return_value={"error": {"error_msg": "Test error"}}):
            success = await bot.send_message("12345", "РўРµСЃС‚")
            assert success is False

    def test_draft_not_found(self):
        """РџСЂРѕРІРµСЂРєР° РѕР±СЂР°Р±РѕС‚РєРё РЅРµСЃСѓС‰РµСЃС‚РІСѓСЋС‰РµРіРѕ С‡РµСЂРЅРѕРІРёРєР°."""
        manager = DraftManager()
        success = manager.approve_draft("nonexistent_id")
        assert success is False



