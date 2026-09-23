"""Тесты для краудфандинг-модуля."""
import asyncio
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Триггер lazy import
from core.main import app  # noqa: F401


# ── Модели данных ──────────────────────────────────────────

class TestMilestone:
    """Тесты модели Milestone."""

    def test_to_dict(self):
        from community.crowdfunding import Milestone
        m = Milestone(percent=50, amount=25000, reached=True, reached_at="2025-01-15T10:00:00")
        d = m.to_dict()
        assert d["percent"] == 50
        assert d["amount"] == 25000
        assert d["reached"] is True
        assert d["reached_at"] == "2025-01-15T10:00:00"

    def test_from_dict(self):
        from community.crowdfunding import Milestone
        d = {"percent": 75, "amount": 37500, "reached": False, "reached_at": None}
        m = Milestone.from_dict(d)
        assert m.percent == 75
        assert m.amount == 37500
        assert m.reached is False

    def test_defaults(self):
        from community.crowdfunding import Milestone
        m = Milestone(percent=30, amount=15000)
        assert m.reached is False
        assert m.reached_at is None


class TestSnapshot:
    """Тесты модели Snapshot."""

    def test_to_dict(self):
        from community.crowdfunding import Snapshot
        s = Snapshot(
            timestamp="2025-01-15T10:00:00",
            raised_amount=50000,
            backers_count=100,
            progress_percent=50.0,
        )
        d = s.to_dict()
        assert d["raised_amount"] == 50000
        assert d["backers_count"] == 100
        assert d["progress_percent"] == 50.0


class TestCrowdfundingCampaign:
    """Тесты модели CrowdfundingCampaign."""

    def test_progress_percent(self):
        from community.crowdfunding import CrowdfundingCampaign
        c = CrowdfundingCampaign(
            id="test_1",
            platform="manual",
            url="https://test.com",
            title="Test",
            target_amount=100000,
            raised_amount=50000,
        )
        assert c.progress_percent == 50.0

    def test_progress_percent_zero_target(self):
        from community.crowdfunding import CrowdfundingCampaign
        c = CrowdfundingCampaign(
            id="test_2",
            platform="manual",
            url="https://test.com",
            title="Test",
            target_amount=0,
            raised_amount=100,
        )
        assert c.progress_percent == 0.0

    def test_progress_percent_capped(self):
        from community.crowdfunding import CrowdfundingCampaign
        c = CrowdfundingCampaign(
            id="test_3",
            platform="manual",
            url="https://test.com",
            title="Test",
            target_amount=100000,
            raised_amount=200000,
        )
        assert c.progress_percent == 200.0  # не ограничиваем

    def test_to_dict(self):
        from community.crowdfunding import CrowdfundingCampaign, Milestone
        c = CrowdfundingCampaign(
            id="test_1",
            platform="manual",
            url="https://test.com",
            title="Test",
            target_amount=100000,
            raised_amount=50000,
            backers_count=100,
            milestones=[Milestone(percent=50, amount=50000, reached=True)],
        )
        d = c.to_dict()
        assert d["id"] == "test_1"
        assert d["progress_percent"] == 50.0
        assert len(d["milestones"]) == 1

    def test_from_dict(self):
        from community.crowdfunding import CrowdfundingCampaign
        d = {
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
            "raised_amount": 50000,
            "milestones": [{"percent": 50, "amount": 50000, "reached": True}],
        }
        c = CrowdfundingCampaign.from_dict(d)
        assert c.id == "test_1"
        assert c.progress_percent == 50.0
        assert c.milestones[0].reached is True


class TestMilestoneAlert:
    """Тесты модели MilestoneAlert."""

    def test_to_dict(self):
        from community.crowdfunding import MilestoneAlert
        a = MilestoneAlert(
            campaign_id="planeta_1",
            campaign_title="Тест",
            milestone_percent=50,
            raised_amount=50000,
            target_amount=100000,
        )
        d = a.to_dict()
        assert d["campaign_id"] == "planeta_1"
        assert d["milestone_percent"] == 50
        assert "timestamp" in d

    def test_telegram_message(self):
        from community.crowdfunding import MilestoneAlert
        a = MilestoneAlert(
            campaign_id="test",
            campaign_title="Наследие Аркаима",
            milestone_percent=50,
            raised_amount=50000,
            target_amount=100000,
        )
        msg = a.telegram_message()
        assert "50%" in msg
        assert "50 000" in msg
        assert "100 000" in msg


# ── Парсер ─────────────────────────────────────────────────

class TestCrowdfundingParser:
    """Тесты парсера."""

    def test_parse_manual(self):
        from community.crowdfunding import CrowdfundingParser
        campaign = CrowdfundingParser.parse_manual({
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Тест",
            "target_amount": 100000,
            "raised_amount": 50000,
            "backers_count": 100,
            "milestones": [30, 50, 75, 100],
        })
        assert campaign.id == "test_1"
        assert campaign.progress_percent == 50.0
        assert len(campaign.milestones) == 4
        assert campaign.milestones[1].percent == 50
        assert campaign.milestones[1].amount == 50000

    def test_parse_manual_default_milestones(self):
        from community.crowdfunding import CrowdfundingParser
        campaign = CrowdfundingParser.parse_manual({
            "id": "test_2",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Тест",
            "target_amount": 200000,
        })
        # Должны быть дефолтные [30, 50, 75, 100]
        assert len(campaign.milestones) == 4
        assert campaign.milestones[0].percent == 30
        assert campaign.milestones[0].amount == 60000


# ── Монитор ────────────────────────────────────────────────

class TestCrowdfundingMonitor:
    """Тесты монитора."""

    def test_init_with_campaigns(self):
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[{
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
        }])
        assert "test_1" in monitor.campaigns

    def test_get_all_campaigns(self):
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[{
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
        }])
        campaigns = monitor.get_all_campaigns()
        assert len(campaigns) == 1
        assert campaigns[0]["id"] == "test_1"

    def test_get_campaign_not_found(self):
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[])
        result = monitor.get_campaign("nonexistent")
        assert result is None

    def test_get_campaign_history(self):
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[])
        history = monitor.get_campaign_history("nonexistent")
        assert history == []

    @pytest.mark.asyncio
    async def test_check_manual_campaign(self):
        """Проверка manual-кампании (без парсинга)."""
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[{
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
            "raised_amount": 50000,
        }])
        alerts = await monitor.check_all()
        # Нет новых майлстоунов, так как они не настроены
        campaign = monitor.get_campaign("test_1")
        assert campaign is not None
        assert campaign["raised_amount"] == 50000

    def test_check_milestones_triggered(self):
        """Проверка срабатывания майлстоуна."""
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[{
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
            "raised_amount": 60000,  # 60% — должны сработать 30% и 50%
            "milestones": [30, 50, 75, 100],
        }])
        alerts = monitor.check_milestones("test_1")
        assert len(alerts) == 2
        assert alerts[0].milestone_percent == 30
        assert alerts[1].milestone_percent == 50

        # Проверим что milestone отмечены как достигнутые
        campaign = monitor.campaigns["test_1"]
        assert campaign.milestones[0].reached is True
        assert campaign.milestones[1].reached is True

    def test_no_duplicate_milestones(self):
        """Нет дубликатов при повторной проверке."""
        from community.crowdfunding import CrowdfundingMonitor
        monitor = CrowdfundingMonitor(campaigns_config=[{
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
            "raised_amount": 60000,
            "milestones": [30, 50, 75, 100],
        }])
        
        # Первый вызов
        alerts1 = monitor.check_milestones("test_1")
        assert len(alerts1) == 2
        
        # Второй вызов — майлстоуны уже достигнуты
        alerts2 = monitor.check_milestones("test_1")
        assert len(alerts2) == 0  # новых нет


# ── Конфигурация ──────────────────────────────────────────

class TestConfig:
    """Тесты конфигурации."""

    def test_load_config_defaults(self):
        from community.crowdfunding import load_config
        result = load_config()
        assert result["enabled"] is True
        assert result["campaigns"] == []
        assert result["check_interval"] == 3600

    def test_load_config_custom(self):
        os.environ["CROWDFUNDING_ENABLED"] = "false"
        os.environ["CROWDFUNDING_CHECK_INTERVAL"] = "7200"
        
        from community.crowdfunding import load_config
        result = load_config()
        assert result["enabled"] is False
        assert result["check_interval"] == 7200
        
        # Очистка
        os.environ.pop("CROWDFUNDING_ENABLED", None)
        os.environ.pop("CROWDFUNDING_CHECK_INTERVAL", None)

    def test_load_config_invalid_json(self):
        os.environ["CROWDFUNDING_URLS"] = "not valid json"
        
        from community.crowdfunding import load_config
        result = load_config()
        assert result["campaigns"] == []
        
        os.environ.pop("CROWDFUNDING_URLS", None)


# ── API Integration ───────────────────────────────────────

class TestCrowdfundingAPI:
    """Интеграционные тесты API."""

    def test_status_endpoint(self):
        """GET /book/crowdfunding/status."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/book/crowdfunding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "campaigns" in data
        assert "count" in data

    def test_campaign_not_found(self):
        """GET /book/crowdfunding/campaign/{id} — не найдена."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/book/crowdfunding/campaign/nonexistent")
        assert resp.status_code == 404

    def test_config_endpoint_admin(self):
        """GET /book/crowdfunding/config."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/book/crowdfunding/config")
        # Требует роль admin, но conftest даёт admin
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "campaigns" in data

    def test_check_now(self):
        """POST /book/crowdfunding/check-now."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/book/crowdfunding/check-now")
        assert resp.status_code == 200
        data = resp.json()
        assert "checked" in data
        assert "alerts" in data

    def test_update_config(self):
        """POST /book/crowdfunding/config."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        new_config = [{
            "id": "test_new",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test Campaign",
            "target_amount": 100000,
            "milestones": [30, 50, 75, 100],
        }]
        
        resp = client.post("/book/crowdfunding/config", json=new_config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["campaigns"] == 1

    def test_update_config_missing_field(self):
        """POST /book/crowdfunding/config — missing field."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        bad_config = [{
            "id": "test",
            "platform": "invalid",  # invalid platform
            "url": "https://test.com",
            "title": "Test",
            "target_amount": 100000,
        }]
        
        resp = client.post("/book/crowdfunding/config", json=bad_config)
        assert resp.status_code == 400
