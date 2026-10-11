# Sprint 2d — Краудфандинг-интеграция (MVP)

## 📋 Текущее состояние
| Фича | Статус |
|------|--------|
| **PDF-загрузка** | ✅ Готово | `pdf_extractor.py` + `IngestionOrchestrator` + `upload.html` |
| **Telegram Presence** | ✅ Готово | `TelegramPresence.process_message()` + wiring в `telegram.py` |
| **Email-рассылка** | ✅ Готово | `email_sender.py` + авто-генерация из Pulse + периодика |
| **Краудфандинг** | ❌ Не начато | Нет ни модулей, ни API, ни UI |

---

## 🎯 Цель
MVP-интеграция с российскими краудфандинг-платформами (Planeta.ru, Boomstarter) для сбора средств на издание книги «Наследие Аркаима».

---

## 🔍 Исследование API

### Planeta.ru
- **Публичное API:** отсутствует (нет official API documentation)
- **Альтернатива:** парсинг страницы кампании через `httpx` + `BeautifulSoup`
- **Данные для сбора:**
  - Собрано / Цель (прогресс-бар)
  - Количество бэкеров
  - Дней до конца
  - Статус (сбор / завершён / отменён)
  - Майлстоуны (30%, 50%, 75%, 100%)

### Boomstarter
- **Публичное API:** отсутствует
- **Альтернатива:** аналогичный парсинг
- **Данные:** те же, что у Planeta.ru

### Вывод
Обе платформы **не имеют публичного API**. Используем **парсинг HTML** с fallback на **ручную конфигурацию**.

---

## 🏗️ Архитектура

```
community/crowdfunding.py       — основной модуль
  ├── CrowdfundingCampaign      — модель кампании
  ├── CrowdfundingMonitor       — парсер + мониторинг
  ├── MilestoneChecker          — проверка майлстоунов
  └── CrowdfundingConfig        — конфигурация

community/crowdfunding_api.py   — FastAPI роуты
  ├── GET /book/crowdfunding/status
  ├── GET /book/crowdfunding/history
  └── POST /book/crowdfunding/config (admin)

templates/crowdfunding.html     — UI-страница
  ├── Прогресс-бар
  ├── Статистика (бэкероы, дни, суммы)
  └── Уведомления о майлстоунах

config.py                       — новые переменные
  ├── CROWDFUNDING_ENABLED      = true/false
  ├── CROWDFUNDING_URLS         = json([...])
  ├── CROWDFUNDING_CHECK_INTERVAL = 3600 (сек)
  └── CROWDFUNDING_WEBHOOK_URL  = для уведомлений

websocket.py                    — расширение
  └── notify_crowdfunding_milestone()
```

---

## 📝 Детальный план реализации

### Шаг 1. Модель данных (`community/crowdfunding.py`)

```python
@dataclass
class CrowdfundingCampaign:
    """Модель краудфандинг-кампании."""
    id: str                          # уникальный ID (planeta_1, boom_1)
    platform: str                    # "planeta" | "boom" | "manual"
    url: str                         # URL кампании
    title: str                       # Название кампании
    target_amount: int               # Целевая сумма (рубли)
    raised_amount: int               # Собрано (рубли)
    backers_count: int               # Количество бэкеров
    days_remaining: int | None       # Дней до конца (None если завершена)
    status: str                      # "active" | "completed" | "cancelled" | "error"
    last_checked: str                # ISO timestamp последней проверки
    milestones: list[Milestone]      # Список майлстоунов
    history: list[Snapshot]          # История изменений

@dataclass
class Milestone:
    """Майлстоун — пороговое значение."""
    percent: int                     # 30, 50, 75, 100
    amount: int                      # Сумма в рублях
    reached: bool                    # Достигнут ли
    reached_at: str | None           # Когда достигнут (ISO)

@dataclass
class Snapshot:
    """Снимок состояния на момент проверки."""
    timestamp: str
    raised_amount: int
    backers_count: int
    progress_percent: float
```

### Шаг 2. Парсер (`community/crowdfunding.py`)

```python
class CrowdfundingParser:
    """Парсинг страниц краудфандинг-платформ."""
    
    @staticmethod
    def parse_planeta(url: str) -> CrowdfundingCampaign:
        """Парсинг страницы Planeta.ru."""
        # 1. GET запрос с timeout
        # 2. Парсинг через BeautifulSoup:
        #    - .js-amount-raised (собрано)
        #    - .js-amount-target (цель)
        #    - .js-backers-count (бэкероы)
        #    - .js-days-remaining (дни)
        # 3. Fallback: regex-парсинг если структура изменилась
        # 4. Возврат CrowdfundingCampaign или raise ParsingError
    
    @staticmethod
    def parse_boom(url: str) -> CrowdfundingCampaign:
        """Парсинг страницы Boomstarter."""
        # Аналогично Planeta, но другие CSS-селекторы
    
    @staticmethod
    def parse_manual(data: dict) -> CrowdfundingCampaign:
        """Ручное обновление данных (fallback)."""
        # Используется когда парсинг не работает
```

### Шаг 3. Монитор (`community/crowdfunding.py`)

```python
class CrowdfundingMonitor:
    """Мониторинг кампаний и проверка майлстоунов."""
    
    def __init__(self, campaigns: list[dict]):
        self.campaigns: dict[str, CrowdfundingCampaign] = {}
        self._load_from_config(campaigns)
    
    async def check_all(self) -> list[MilestoneAlert]:
        """Проверить все кампании, вернуть новые майлстоуны."""
        alerts = []
        for cid, campaign in self.campaigns.items():
            try:
                updated = await self._check_campaign(cid)
                alerts.extend(self._check_milestones(cid, updated))
            except Exception as e:
                log.error("crowdfunding_check_error campaign=%s error=%s", cid, e)
        return alerts
    
    async def _check_campaign(self, campaign_id: str) -> CrowdfundingCampaign:
        """Проверить одну кампанию."""
        campaign = self.campaigns[campaign_id]
        if campaign.platform == "planeta":
            parsed = CrowdfundingParser.parse_planeta(campaign.url)
        elif campaign.platform == "boom":
            parsed = CrowdfundingParser.parse_boom(campaign.url)
        else:
            parsed = campaign  # manual
        
        # Сохранить историю
        parsed.history.append(Snapshot(
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            raised_amount=parsed.raised_amount,
            backers_count=parsed.backers_count,
            progress_percent=parsed.target_amount > 0 
                and (parsed.raised_amount / parsed.target_amount * 100),
        ))
        
        self.campaigns[campaign_id] = parsed
        return parsed
    
    def _check_milestones(self, campaign_id: str, campaign: CrowdfundingCampaign) -> list[MilestoneAlert]:
        """Проверить достижение майлстоунов."""
        alerts = []
        progress = campaign.raised_amount / campaign.target_amount * 100
        
        for milestone in campaign.milestones:
            if not milestone.reached and progress >= milestone.percent:
                milestone.reached = True
                milestone.reached_at = datetime.now(tz=timezone.utc).isoformat()
                alerts.append(MilestoneAlert(
                    campaign_id=campaign_id,
                    campaign_title=campaign.title,
                    milestone_percent=milestone.percent,
                    raised_amount=campaign.raised_amount,
                    target_amount=campaign.target_amount,
                ))
        
        return alerts
```

### Шаг 4. Конфигурация (`config.py`)

```python
# ── Crowdfunding ─────────────────────────────────────
CROWDFUNDING_ENABLED: bool = os.getenv("CROWDFUNDING_ENABLED", "true").lower() == "true"
CROWDFUNDING_URLS: str = os.getenv("CROWDFUNDING_URLS", "[]")  # JSON array
CROWDFUNDING_CHECK_INTERVAL: int = int(os.getenv("CROWDFUNDING_CHECK_INTERVAL", "3600"))
CROWDFUNDING_WEBHOOK_URL: str = os.getenv("CROWDFUNDING_WEBHOOK_URL", "")
```

Пример `CROWDFUNDING_URLS`:
```json
[
  {
    "id": "planeta_arkaim_2025",
    "platform": "planeta",
    "url": "https://planeta.ru/project/arkaim-legacy",
    "title": "Наследие Аркаима — издание 2025",
    "target_amount": 500000,
    "milestones": [30, 50, 75, 100]
  },
  {
    "id": "boom_arkaim_visual",
    "platform": "boom",
    "url": "https://boomstarter.ru/project/arkaim-visual",
    "title": "Визуальный геном Аркаима",
    "target_amount": 300000,
    "milestones": [25, 50, 75, 100]
  }
]
```

### Шаг 5. API роуты (`community/crowdfunding_api.py`)

```python
router = APIRouter(prefix="/book/crowdfunding", tags=["Crowdfunding"])

@router.get("/status")
async def crowdfunding_status():
    """Получить статус всех кампаний."""
    monitor = get_crowdfunding_monitor()
    return await monitor.get_all_campaigns()

@router.get("/history/{campaign_id}")
async def crowdfunding_history(campaign_id: str):
    """История изменений кампании."""
    monitor = get_crowdfunding_monitor()
    return await monitor.get_campaign_history(campaign_id)

@router.post("/config", dependencies=[Depends(require_role("admin"))])
async def update_crowdfunding_config(urls: list[dict]):
    """Обновить конфигурацию кампаний."""
    # Сохранить в config.env или файл
    return {"ok": True}

@router.post("/check-now")
async def force_check():
    """Принудительная проверка всех кампаний."""
    monitor = get_crowdfunding_monitor()
    alerts = await monitor.check_all()
    return {"checked": len(monitor.campaigns), "alerts": len(alerts)}
```

### Шаг 6. UI-страница (`templates/crowdfunding.html`)

```html
{% extends "base.html" %}
{% block title %}Краудфандинг — Наследие Аркаима{% endblock %}
{% block content %}
<div class="crowdfunding-layout">
  <section class="crowdfunding-hero">
    <h1>🎯 Поддержать проект</h1>
    <p>Помогите нам издать книгу «Наследие Аркаима» в печатном виде.</p>
  </section>

  {% for campaign in campaigns %}
  <div class="campaign-card">
    <h2>{{ campaign.title }}</h2>
    <a href="{{ campaign.url }}" target="_blank">Перейти к кампании →</a>
    
    <!-- Прогресс-бар -->
    <div class="progress-bar">
      <div class="progress-fill" style="width: {{ campaign.progress_percent }}%"></div>
    </div>
    <div class="progress-label">
      {{ campaign.raised_amount }} / {{ campaign.target_amount }} руб.
      ({{ campaign.progress_percent|int }}%)
    </div>
    
    <!-- Статистика -->
    <div class="campaign-stats">
      <span>👥 {{ campaign.backers_count }} бэкеров</span>
      <span>📅 {{ campaign.days_remaining }} дней осталось</span>
      <span>📊 {{ campaign.status }}</span>
    </div>
    
    <!-- Майлстоуны -->
    <div class="milestones">
      {% for m in campaign.milestones %}
      <div class="milestone {% if m.reached %}reached{% endif %}">
        {{ m.percent }}% — {{ m.amount }} руб.
        {% if m.reached %}✅ {{ m.reached_at }}{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
```

### Шаг 7. WebSocket-уведомления (`websocket.py`)

```python
async def notify_crowdfunding_milestone(alert: dict):
    """Уведомить о достижении майлстоуна."""
    await manager.broadcast("crowdfunding_milestone", alert)
```

### Шаг 8. Периодическая проверка (`main.py` lifespan)

```python
async def _crowdfunding_check_loop():
    from community.crowdfunding import CrowdfundingMonitor
    from config import config
    
    if not config.CROWDFUNDING_ENABLED:
        return
    
    monitor = CrowdfundingMonitor(
        campaigns=json.loads(config.CROWDFUNDING_URLS)
    )
    interval = config.CROWDFUNDING_CHECK_INTERVAL
    
    while True:
        try:
            await asyncio.sleep(interval)
            alerts = await monitor.check_all()
            
            for alert in alerts:
                await notify_crowdfunding_milestone(alert)
                log.info("crowdfunding_milestone_reached %s", alert)
                
                # Отправить в Telegram
                if config.TELEGRAM_ADMIN_CHAT_ID:
                    from community.telegram import TelegramBotStub
                    bot = TelegramBotStub()
                    msg = (
                        f"🎉 МАЙЛСТОУН: {alert['campaign_title']} "
                        f"достиг {alert['milestone_percent']}% "
                        f"(сбор: {alert['raised_amount']} руб.)"
                    )
                    await bot.send_notification(msg)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("crowdfunding_check_error error=%s", e)
            await asyncio.sleep(60)

_crowdfunding_task = asyncio.create_task(_crowdfunding_check_loop())
```

### Шаг 9. Тесты (`runtime/tests/test_crowdfunding.py`)

```python
class TestCrowdfundingParser:
    def test_parse_manual(self):
        """Ручная конфигурация."""
        from community.crowdfunding import CrowdfundingParser
        campaign = CrowdfundingParser.parse_manual({
            "id": "test_1",
            "platform": "manual",
            "url": "https://test.com",
            "title": "Test Campaign",
            "target_amount": 100000,
            "raised_amount": 50000,
            "backers_count": 100,
        })
        assert campaign.progress_percent == 50.0
    
    def test_progress_calculation(self):
        """Расчёт прогресса."""
        ...

class TestMilestoneChecker:
    def test_milestone_triggered(self):
        """Проверка срабатывания майлстоуна."""
        ...
    
    def test_no_duplicate_alert(self):
        """Нет дубликатов уведомлений."""
        ...

class TestCrowdfundingAPI:
    def test_status_endpoint(self):
        """GET /book/crowdfunding/status."""
        ...
```

---

## 📊 Оценка

| Шаг | Задача | Оценка |
|-----|--------|--------|
| 1 | Модель данных | 0.5 дня |
| 2 | Парсер (Planeta + Boom + manual) | 1 день |
| 3 | Монитор + майлстоуны | 0.5 дня |
| 4 | Конфигурация | 0.25 дня |
| 5 | API роуты | 0.5 дня |
| 6 | UI-страница | 0.5 дня |
| 7 | WebSocket-уведомления | 0.25 дня |
| 8 | Периодическая проверка + Telegram | 0.5 дня |
| 9 | Тесты | 0.5 дня |
| **Итого** | | **~4.5 дня** |

---

## ⚠️ Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Planeta.ru изменила HTML-структуру | Высокая | Regex-парсинг + manual fallback |
| CAPTCHA при частых запросах | Средняя | Интервал проверки ≥ 1 час, рандомный User-Agent |
| Нет API — сложно тестировать | Средняя | Mock-парсер для тестов, manual mode |
| Блокировка IP краудфандингом | Низкая | Rate limiting, прокси (опционально) |
| Юридические вопросы парсинга | Низкая | Только публичные данные, robots.txt respect |

---

## ✅ Критерии готовности

1. ✅ Модуль `community/crowdfunding.py` с парсером и монитором
2. ✅ API endpoints: `/book/crowdfunding/status`, `/history`, `/config`
3. ✅ UI-страница `/_ui/crowdfunding` с прогресс-баром
4. ✅ Периодическая проверка (настраиваемый интервал)
5. ✅ WebSocket-уведомления о майлстоунах
6. ✅ Telegram-уведомления о майлстоунах
7. ✅ Ручной режим конфигурации (fallback)
8. ✅ Тесты (mock-парсер + unit-тесты)
9. ✅ Документация в `.env.example`

---

## 🚀 Следующие шаги

1. Утвердить план
2. Выбрать платформу для приоритетной интеграции (Planeta.ru или Boomstarter)
3. Начать реализацию с Шага 1 (модель данных)
