"""
FastAPI роуты для краудфандинг-мониторинга.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth.rbac import require_role
from community.crowdfunding import (
    CrowdfundingMonitor,
    load_config,
)

log = logging.getLogger("hermes.crowdfunding_api")

router = APIRouter(prefix="/book/crowdfunding", tags=["Crowdfunding"])

# Глобальный монитор (инициализируется при первом запросе)
_monitor: Optional[CrowdfundingMonitor] = None


def get_monitor() -> CrowdfundingMonitor:
    """Получить или инициализировать глобальный монитор."""
    global _monitor
    if _monitor is None:
        cfg = load_config()
        _monitor = CrowdfundingMonitor(
            campaigns_config=cfg["campaigns"],
            user_agent=cfg["user_agent"],
        )
    return _monitor


@router.get("/status")
async def crowdfunding_status():
    """
    Получить статус всех кампаний.

    Возвращает список кампаний с текущими данными.
    """
    monitor = get_monitor()
    return {
        "campaigns": monitor.get_all_campaigns(),
        "count": len(monitor.get_all_campaigns()),
    }


@router.get("/campaign/{campaign_id}")
async def crowdfunding_campaign(campaign_id: str):
    """
    Получить статус конкретной кампании.

    Возвращает данные кампании с историей.
    """
    monitor = get_monitor()
    campaign = monitor.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(404, f"Campaign not found: {campaign_id}")
    return campaign


@router.get("/campaign/{campaign_id}/history")
async def crowdfunding_history(campaign_id: str, limit: int = 50):
    """
    Получить историю изменений кампании.

    Args:
        campaign_id: ID кампании
        limit: количество последних снимков
    """
    monitor = get_monitor()
    history = monitor.get_campaign_history(campaign_id)
    return {
        "campaign_id": campaign_id,
        "snapshots": history[-limit:],
        "total": len(history),
    }


@router.post("/check-now")
async def force_check():
    """
    Принудительная проверка всех кампаний.

    Возвращает количество проверенных кампаний и новые майлстоуны.
    (Только для админов)
    """
    monitor = get_monitor()
    alerts = await monitor.check_all()

    # Проверяем майлстоуны
    all_alerts = []
    for cid in monitor.campaigns:
        all_alerts.extend(monitor.check_milestones(cid))

    return {
        "checked": len(monitor.campaigns),
        "alerts": len(all_alerts),
        "milestones": [a.to_dict() for a in all_alerts],
    }


@router.post("/config", dependencies=[Depends(require_role("admin"))])
async def update_crowdfunding_config(urls: list[dict]):
    """
    Обновить конфигурацию кампаний.

    Принимает список кампаний в формате:
    [
      {
        "id": "planeta_arkaim_2025",
        "platform": "planeta",
        "url": "https://planeta.ru/project/...",
        "title": "Название",
        "target_amount": 500000,
        "milestones": [30, 50, 75, 100]
      }
    ]
    """
    global _monitor

    # Валидация
    for cfg in urls:
        required = ["id", "platform", "url", "title", "target_amount"]
        for field_name in required:
            if field_name not in cfg:
                raise HTTPException(
                    400, f"Missing required field: {field_name}"
                )
        if cfg["platform"] not in ("planeta", "boom", "manual"):
            raise HTTPException(
                400, f"Invalid platform: {cfg['platform']}. "
                "Use: planeta, boom, manual"
            )

    # Перезагружаем монитор
    _monitor = CrowdfundingMonitor(
        campaigns_config=urls,
    )

    log.info("crowdfunding_config_updated count=%d", len(urls))

    return {
        "ok": True,
        "campaigns": len(urls),
        "message": "Конфигурация обновлена",
    }


@router.post("/milestones/{campaign_id}/check", dependencies=[Depends(require_role("admin"))])
async def check_milestones(campaign_id: str):
    """
    Проверить майлстоуны для конкретной кампании.

    Возвращает список Newly достигнутых майлстоунов.
    """
    monitor = get_monitor()
    alerts = monitor.check_milestones(campaign_id)

    return {
        "campaign_id": campaign_id,
        "alerts": len(alerts),
        "milestones": [a.to_dict() for a in alerts],
    }


@router.get("/config", dependencies=[Depends(require_role("admin"))])
async def get_crowdfunding_config():
    """Получить текущую конфигурацию (только для админов)."""
    cfg = load_config()
    return {
        "enabled": cfg["enabled"],
        "check_interval": cfg["check_interval"],
        "campaigns": cfg["campaigns"],
        "campaign_count": len(cfg["campaigns"]),
    }
