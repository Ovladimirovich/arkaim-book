"""
HealthMonitor — проверяет доступность сервисов и уведомляет при падениях.
Работает как skill + фоновая периодическая проверка.
"""
import asyncio
import httpx
import logging
from skills.base import Skill, SkillContext, SkillResult
from core.config import settings

log = logging.getLogger("hermes.skills.health_monitor")


def _build_services() -> dict[str, str]:
    """Формирует URLs сервисов из настроек."""
    core_host = settings.CORE_HOST
    core_port = settings.CORE_PORT
    gateway_host = settings.GATEWAY_HOST
    gateway_port = settings.GATEWAY_PORT
    api_host = settings.API_HOST
    api_port = settings.API_PORT
    return {
        "core": f"http://{core_host}:{core_port}/health",
        "gateway": f"http://{gateway_host}:{gateway_port}/health",
        "book_api": f"http://{api_host}:{api_port}/health",
    }

_FAILURE_COUNTER: dict[str, int] = {}
_ALERTED: dict[str, bool] = {}
_THRESHOLD = 3
_CHECK_INTERVAL = 60  # секунд
_HTTP_TIMEOUT = 5.0

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def _send_telegram_alert(message: str):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not token or not chat_id:
        log.warning("health_monitor_alert TELEGRAM_BOT_TOKEN или TELEGRAM_ADMIN_CHAT_ID не заданы")
        return
    url = _TELEGRAM_API.format(token=token)
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(url, json={"chat_id": chat_id, "text": f"⚠️ {message}", "parse_mode": "HTML"})
        except Exception as e:
            log.error("health_monitor_telegram_error %s", e)


async def check_all_services() -> dict[str, bool]:
    """Проверить все сервисы, обновить счётчики, вернуть {name: ok}."""
    services = _build_services()
    statuses = {}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        for name, url in services.items():
            try:
                r = await client.get(url)
                ok = r.status_code == 200
            except Exception:
                ok = False

            statuses[name] = ok
            if ok:
                _FAILURE_COUNTER[name] = 0
                _ALERTED[name] = False
            else:
                _FAILURE_COUNTER[name] = _FAILURE_COUNTER.get(name, 0) + 1

    return statuses


async def periodic_check():
    """Фоновая периодическая проверка (добавляется в lifespan)."""
    while True:
        await asyncio.sleep(_CHECK_INTERVAL)
        try:
            statuses = await check_all_services()
            for name, ok in statuses.items():
                count = _FAILURE_COUNTER.get(name, 0)
                if not ok and count >= _THRESHOLD and not _ALERTED.get(name):
                    _ALERTED[name] = True
                    msg = f"Сервис <b>{name}</b> недоступен ({count} ошибок подряд)"
                    await _send_telegram_alert(msg)
                    log.error("health_monitor_alert service=%s failures=%d", name, count)
                elif ok and _ALERTED.get(name):
                    _ALERTED[name] = False
                    msg = f"Сервис <b>{name}</b> снова доступен"
                    await _send_telegram_alert(msg)
                    log.info("health_monitor_recovered service=%s", name)
        except Exception as e:
            log.error("health_monitor_periodic_error %s", e)


class HealthMonitor(Skill):
    name = "health_monitor"
    priority = 100

    async def execute(self, ctx: SkillContext) -> SkillResult:
        if "health" not in ctx.user_text.lower() and "статус" not in ctx.user_text.lower():
            return SkillResult(handled=False)

        statuses = await check_all_services()
        lines = []
        for name, ok in statuses.items():
            count = _FAILURE_COUNTER.get(name, 0)
            icon = "✓" if ok else f"✗ (сбоев: {count})"
            lines.append(f"{name}: {icon}")
        response = "Статус сервисов:\n" + "\n".join(lines)
        return SkillResult(handled=True, response=response, context="health_check")


skill = HealthMonitor()
