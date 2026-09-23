"""
crowdfunding — мониторинг краудфандинг-кампаний.

Поддерживает парсинг Planeta.ru и Boomstarter,
fallback на ручную конфигурацию.

Переменные окружения:
  CROWDFUNDING_ENABLED       = true/false (default: true)
  CROWDFUNDING_URLS          = JSON array кампаний
  CROWDFUNDING_CHECK_INTERVAL = 3600 (сек, default: 1 час)
  CROWDFUNDING_USER_AGENT    = User-Agent для запросов
"""
import json
import logging
import re
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("hermes.crowdfunding")

# ── Модели данных ──────────────────────────────────────────


@dataclass
class Milestone:
    """Майлстоун — пороговое значение прогресса."""
    percent: int                    # 30, 50, 75, 100
    amount: int                     # Сумма в рублях
    reached: bool = False
    reached_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "percent": self.percent,
            "amount": self.amount,
            "reached": self.reached,
            "reached_at": self.reached_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Milestone":
        return cls(
            percent=d["percent"],
            amount=d["amount"],
            reached=d.get("reached", False),
            reached_at=d.get("reached_at"),
        )


@dataclass
class Snapshot:
    """Снимок состояния кампании на момент проверки."""
    timestamp: str
    raised_amount: int
    backers_count: int
    progress_percent: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "raised_amount": self.raised_amount,
            "backers_count": self.backers_count,
            "progress_percent": round(self.progress_percent, 2),
        }


@dataclass
class CrowdfundingCampaign:
    """Модель краудфандинг-кампании."""
    id: str
    platform: str                   # "planeta" | "boom" | "manual"
    url: str
    title: str
    target_amount: int
    raised_amount: int = 0
    backers_count: int = 0
    days_remaining: Optional[int] = None
    status: str = "active"          # "active" | "completed" | "cancelled" | "error"
    last_checked: Optional[str] = None
    milestones: list[Milestone] = field(default_factory=list)
    history: list[Snapshot] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return min((self.raised_amount / self.target_amount) * 100, 999.99)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "url": self.url,
            "title": self.title,
            "target_amount": self.target_amount,
            "raised_amount": self.raised_amount,
            "backers_count": self.backers_count,
            "days_remaining": self.days_remaining,
            "status": self.status,
            "progress_percent": round(self.progress_percent, 2),
            "last_checked": self.last_checked,
            "milestones": [m.to_dict() for m in self.milestones],
            "history": [s.to_dict() for s in self.history[-50:]],  # последние 50
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CrowdfundingCampaign":
        return cls(
            id=d["id"],
            platform=d["platform"],
            url=d["url"],
            title=d["title"],
            target_amount=d["target_amount"],
            raised_amount=d.get("raised_amount", 0),
            backers_count=d.get("backers_count", 0),
            days_remaining=d.get("days_remaining"),
            status=d.get("status", "active"),
            last_checked=d.get("last_checked"),
            milestones=[Milestone.from_dict(m) for m in d.get("milestones", [])],
            history=[Snapshot(**h) for h in d.get("history", [])],
            error=d.get("error"),
        )


@dataclass
class MilestoneAlert:
    """Уведомление о достижении майлстоуна."""
    campaign_id: str
    campaign_title: str
    milestone_percent: int
    raised_amount: int
    target_amount: int

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "campaign_title": self.campaign_title,
            "milestone_percent": self.milestone_percent,
            "raised_amount": self.raised_amount,
            "target_amount": self.target_amount,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def telegram_message(self) -> str:
        return (
            f"🎉 <b>МАЙЛСТОУН:</b> {self.campaign_title}\n"
            f"Достигнут {self.milestone_percent}% "
            f"(собрано: {self.raised_amount:,} руб. "
            f"из {self.target_amount:,} руб.)"
        )


# ── Парсеры ───────────────────────────────────────────────


class ParsingError(Exception):
    """Ошибка парсинга страницы."""
    pass


class CrowdfundingParser:
    """Парсер страниц краудфандинг-платформ."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # CSS-селекторы для Planeta.ru
    PLANETA_SELECTORS = {
        "raised": [
            ".js-amount-raised",
            ".planeta-campaign__raised-amount",
            '[class*="raised"]',
        ],
        "target": [
            ".js-amount-target",
            ".planeta-campaign__target-amount",
        ],
        "backers": [
            ".js-backers-count",
            ".planeta-campaign__backers-count",
        ],
        "days": [
            ".js-days-remaining",
            ".planeta-campaign__days-remaining",
        ],
    }

    # CSS-селекторы для Boomstarter
    BOOM_SELECTORS = {
        "raised": [
            ".js-progress-amount",
            ".boom-campaign__raised",
        ],
        "target": [
            ".js-progress-goal",
            ".boom-campaign__goal",
        ],
        "backers": [
            ".js-backers-number",
            ".boom-campaign__backers",
        ],
        "days": [
            ".js-days-left",
            ".boom-campaign__days-left",
        ],
    }

    @classmethod
    async def parse(cls, platform: str, url: str, user_agent: str = "") -> CrowdfundingCampaign:
        """
        Парсить страницу кампании.

        Args:
            platform: "planeta" | "boom"
            url: URL кампании
            user_agent: User-Agent (опционально)

        Returns:
            CrowdfundingCampaign

        Raises:
            ParsingError: если не удалось распарсить
        """
        ua = user_agent or cls.DEFAULT_USER_AGENT

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={"User-Agent": ua},
                follow_redirects=True,
            )
            response.raise_for_status()

        html = response.text

        if platform == "planeta":
            return cls._parse_planeta(html, url)
        elif platform == "boom":
            return cls._parse_boom(html, url)
        else:
            raise ParsingError(f"Unknown platform: {platform}")

    @classmethod
    def _parse_planeta(cls, html: str, url: str) -> CrowdfundingCampaign:
        """Парсинг Planeta.ru через regex (без BeautifulSoup)."""
        # Извлекаем ID из URL
        match = re.search(r"/project/([^/?]+)", url)
        campaign_id = f"planeta_{match.group(1) if match else 'unknown'}"

        # Собираем все цифры из HTML для fallback
        all_numbers = re.findall(r"\d+", html)

        # Ищем собранную сумму
        raised = cls._extract_number(html, [
            r'js-amount-raised[^"]*"[^>]*>\s*([\d\s,]+)',
            r'raised-amount[^>]*>\s*([\d\s,]+)',
            r'([1-9]\d{5,})',  # fallback: большие числа
        ])

        # Ищем целевую сумму
        target = cls._extract_number(html, [
            r'js-amount-target[^"]*"[^>]*>\s*([\d\s,]+)',
            r'target-amount[^>]*>\s*([\d\s,]+)',
            r'goal[^>]*>\s*([\d\s,]+)',
        ])

        # Ищем количество бэкеров
        backers = cls._extract_number(html, [
            r'js-backers-count[^"]*"[^>]*>\s*([\d,]+)',
            r'backers-count[^>]*>\s*([\d,]+)',
            r'backers[^>]*>\s*([\d,]+)',
        ])

        # Ищем оставшиеся дни
        days = cls._extract_number(html, [
            r'js-days-remaining[^"]*"[^>]*>\s*([\d]+)',
            r'days-remaining[^>]*>\s*([\d]+)',
            r'(\d+)\s*дней',
        ])

        # Извлекаем заголовок
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
        title = title_match.group(1).strip() if title_match else "Кампания Planeta.ru"

        # Определяем статус
        status = "active"
        if "campaign--completed" in html or "completed" in html.lower():
            status = "completed"
        elif "campaign--cancelled" in html or "cancelled" in html.lower():
            status = "cancelled"

        return CrowdfundingCampaign(
            id=campaign_id,
            platform="planeta",
            url=url,
            title=title,
            target_amount=target,
            raised_amount=raised,
            backers_count=backers,
            days_remaining=days,
            status=status,
        )

    @classmethod
    def _parse_boom(cls, html: str, url: str) -> CrowdfundingCampaign:
        """Парсинг Boomstarter через regex."""
        match = re.search(r"/project/([^/?]+)", url)
        campaign_id = f"boom_{match.group(1) if match else 'unknown'}"

        all_numbers = re.findall(r"\d+", html)

        raised = cls._extract_number(html, [
            r'js-progress-amount[^"]*"[^>]*>\s*([\d\s,]+)',
            r'progress-amount[^>]*>\s*([\d\s,]+)',
            r'raised[^>]*>\s*([\d\s,]+)',
        ])

        target = cls._extract_number(html, [
            r'js-progress-goal[^"]*"[^>]*>\s*([\d\s,]+)',
            r'progress-goal[^>]*>\s*([\d\s,]+)',
            r'goal[^>]*>\s*([\d\s,]+)',
        ])

        backers = cls._extract_number(html, [
            r'js-backers-number[^"]*"[^>]*>\s*([\d,]+)',
            r'backers-number[^>]*>\s*([\d,]+)',
            r'backers[^>]*>\s*([\d,]+)',
        ])

        days = cls._extract_number(html, [
            r'js-days-left[^"]*"[^>]*>\s*([\d]+)',
            r'days-left[^>]*>\s*([\d]+)',
            r'(\d+)\s*дней',
        ])

        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
        title = title_match.group(1).strip() if title_match else "Кампания Boomstarter"

        status = "active"
        if "completed" in html.lower():
            status = "completed"

        return CrowdfundingCampaign(
            id=campaign_id,
            platform="boom",
            url=url,
            title=title,
            target_amount=target,
            raised_amount=raised,
            backers_count=backers,
            days_remaining=days,
            status=status,
        )

    @classmethod
    def _extract_number(cls, html: str, patterns: list[str]) -> int:
        """Извлечь число из HTML по списку regex-паттернов."""
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                # Убираем пробелы и запятые
                clean = re.sub(r"[,\s]", "", text)
                try:
                    return int(clean)
                except ValueError:
                    continue
        return 0

    @classmethod
    def parse_manual(cls, data: dict) -> CrowdfundingCampaign:
        """
        Создать кампанию из ручной конфигурации.

        Используется когда парсинг недоступен.
        """
        milestones = []
        for pct in data.get("milestones", [30, 50, 75, 100]):
            amount = int(data["target_amount"] * pct / 100)
            milestones.append(Milestone(percent=pct, amount=amount))

        return CrowdfundingCampaign(
            id=data["id"],
            platform=data.get("platform", "manual"),
            url=data["url"],
            title=data["title"],
            target_amount=data["target_amount"],
            raised_amount=data.get("raised_amount", 0),
            backers_count=data.get("backers_count", 0),
            days_remaining=data.get("days_remaining"),
            status=data.get("status", "active"),
            milestones=milestones,
        )


# ── Монитор ────────────────────────────────────────────────


class CrowdfundingMonitor:
    """Мониторинг кампаний и проверка майлстоунов."""

    def __init__(self, campaigns_config: list[dict] | None = None, user_agent: str = ""):
        self.campaigns: dict[str, CrowdfundingCampaign] = {}
        self.user_agent = user_agent or CrowdfundingParser.DEFAULT_USER_AGENT
        self._load_from_config(campaigns_config or [])

    def _load_from_config(self, configs: list[dict]):
        """Загрузить кампании из конфигурации."""
        for cfg in configs:
            campaign = CrowdfundingParser.parse_manual(cfg)
            self.campaigns[campaign.id] = campaign
        log.info("crowdfunding_loaded_campaigns count=%d", len(self.campaigns))

    async def check_all(self) -> list[MilestoneAlert]:
        """
        Проверить все кампании.

        Returns:
            list[MilestoneAlert] — новые достигнутые майлстоуны
        """
        alerts = []
        for cid in list(self.campaigns.keys()):
            try:
                await self._check_campaign(cid)
                alerts.extend(self.check_milestones(cid))
            except Exception as e:
                log.error("crowdfunding_check_error campaign=%s error=%s", cid, e)
                self.campaigns[cid].error = str(e)
                self.campaigns[cid].last_checked = datetime.now(tz=timezone.utc).isoformat()
        return alerts

    async def _check_campaign(self, campaign_id: str) -> CrowdfundingCampaign:
        """Проверить одну кампанию."""
        campaign = self.campaigns[campaign_id]

        if campaign.platform in ("planeta", "boom"):
            # Парсим страницу
            parsed = await CrowdfundingParser.parse(
                campaign.platform,
                campaign.url,
                self.user_agent,
            )
        else:
            # Manual mode — не парсим, просто обновляем timestamp
            parsed = campaign

        # Сохраняем историю
        snapshot = Snapshot(
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            raised_amount=parsed.raised_amount,
            backers_count=parsed.backers_count,
            progress_percent=parsed.progress_percent,
        )
        parsed.history.append(snapshot)
        parsed.last_checked = snapshot.timestamp

        # Обновляем кампанию
        self.campaigns[campaign_id] = parsed

        log.info(
            "crowdfunding_checked id=%s raised=%d/%d (%.1f%%) backers=%d",
            campaign_id,
            parsed.raised_amount,
            parsed.target_amount,
            parsed.progress_percent,
            parsed.backers_count,
        )

        return parsed

    def get_all_campaigns(self) -> list[dict]:
        """Получить статус всех кампаний."""
        return [c.to_dict() for c in self.campaigns.values()]

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Получить статус одной кампании."""
        campaign = self.campaigns.get(campaign_id)
        return campaign.to_dict() if campaign else None

    def get_campaign_history(self, campaign_id: str) -> list[dict]:
        """История изменений кампании."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return []
        return [s.to_dict() for s in campaign.history]

    def check_milestones(self, campaign_id: str) -> list[MilestoneAlert]:
        """Проверить достижение майлстоунов для кампании."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return []

        alerts = []
        progress = campaign.progress_percent

        for milestone in campaign.milestones:
            if not milestone.reached and progress >= milestone.percent:
                milestone.reached = True
                milestone.reached_at = datetime.now(tz=timezone.utc).isoformat()
                alert = MilestoneAlert(
                    campaign_id=campaign.id,
                    campaign_title=campaign.title,
                    milestone_percent=milestone.percent,
                    raised_amount=campaign.raised_amount,
                    target_amount=campaign.target_amount,
                )
                alerts.append(alert)
                log.info(
                    "crowdfunding_milestone_reached campaign=%s percent=%d amount=%d",
                    campaign_id, milestone.percent, campaign.raised_amount,
                )

        return alerts


# ── Конфигурация ──────────────────────────────────────────

def load_config() -> dict:
    """Загрузить конфигурацию из переменных окружения."""
    import os

    enabled = os.getenv("CROWDFUNDING_ENABLED", "true").lower() == "true"
    urls = os.getenv("CROWDFUNDING_URLS", "[]")
    interval = int(os.getenv("CROWDFUNDING_CHECK_INTERVAL", "3600"))
    webhook_url = os.getenv("CROWDFUNDING_WEBHOOK_URL", "")
    user_agent = os.getenv("CROWDFUNDING_USER_AGENT", CrowdfundingParser.DEFAULT_USER_AGENT)

    try:
        campaigns = json.loads(urls)
    except json.JSONDecodeError:
        log.warning("crowdfunding_invalid_urls_config using_empty")
        campaigns = []

    return {
        "enabled": enabled,
        "campaigns": campaigns,
        "check_interval": interval,
        "webhook_url": webhook_url,
        "user_agent": user_agent,
    }
