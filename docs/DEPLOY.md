# Деплой «Наследие Аркаима»

## Локальный запуск (разработка)

```bash
cp .env.example .env
# Сгенерируйте секрет: python -c "import secrets; print(secrets.token_urlsafe(48))"
# Вставьте в SESSION_SECRET

docker compose up --build
# Frontend: http://localhost:3000  |  Backend: http://localhost:8642  |  Swagger: http://localhost:8642/docs
```

### Переменные окружения

| Переменная | Обязательна | Описание |
|---|---|---|
| `SESSION_SECRET` | ✅ | JWT-секрет (48+ символов, `secrets.token_urlsafe(48)`) |
| `ALLOWED_ORIGINS` | prod ✅ | CORS origins через запятую (по умолчанию `http://localhost:3000`) |
| `GIGACHAT_TOKEN` | нет | Токен GigaChat (или `GIGACHAT_CLIENT_ID` + `GIGACHAT_CLIENT_SECRET`) |
| `OPENROUTER_API_KEY` | нет | Fallback-провайдер |
| `TELEGRAM_BOT_TOKEN` | нет | Telegram-бот |
| `BACKEND_URL` | нет | URL бэкенда для Next.js rewrites (по умолчанию `http://127.0.0.1:8642`) |
| `RATE_LIMIT_MAX_REQUESTS` | нет | Лимит запросов в окно (по умолчанию 100) |
| `RATE_LIMIT_WINDOW_SECONDS` | нет | Окно rate limit в секундах (по умолчанию 60) |

### Rate Limiting

По умолчанию rate limiter хранится в памяти процесса (сбрасывается при рестарте).
Для production с несколькими репликами используйте Redis:

```python
# Будущая реализация — см. ADR-XXX
# pip install redis
# RATE_LIMIT_BACKEND=redis://localhost:6379
```

---

## Вариант 1: Cloudflare Tunnel (бесплатно, рекомендую)

### Шаг 1: Установить cloudflared
```bash
winget install cloudflare.cloudflared
```

### Шаг 2: Запустить туннель
```bash
cloudflared tunnel --url http://localhost:3000
```
Получите URL вида: `https://abc123.trycloudflare.com`

### Шаг 3: Обновить .env
```
FRONTEND_URL=https://abc123.trycloudflare.com
PUBLIC_BASE_URL=https://abc123.trycloudflare.com
ALLOWED_ORIGINS=https://abc123.trycloudflare.com
```

### Шаг 4: Перезапустить сервер
```bash
docker compose up --build
```

### Шаг 5: Обновить URL бота в Telegram
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://abc123.trycloudflare.com/webhook/telegram"
```

**Готово!** Теперь inline keyboard будет работать.

---

## Вариант 2: ngrok (альтернатива)

```bash
winget install ngrok.ngrok
ngrok http 3000
```

```env
FRONTEND_URL=https://abc123.ngrok-free.app
ALLOWED_ORIGINS=https://abc123.ngrok-free.app
```

---

## Вариант 3: VPS с доменом (продакшн)

### Подготовка
1. Купить домен (например, `arkaim.ai`)
2. Арендовать VPS (2 vCPU, 2GB RAM — достаточно)
3. Настроить DNS: `arkaim.ai` → IP сервера

### На сервере
```bash
sudo apt update && sudo apt install nginx certbot python3-certbot-nginx docker.io docker-compose-plugin

# Склонировать и запустить
git clone https://github.com/Ovladimirovich/arkaim-book.git
cd arkaim-book
cp .env.example .env
# Отредактируйте .env: SESSION_SECRET, ALLOWED_ORIGINS=https://arkaim.ai

docker compose up --build -d

# Настроить nginx (терминирует TLS, проксирует на Docker)
cat > /etc/nginx/sites-available/arkaim << 'EOF'
server {
    listen 80;
    server_name arkaim.ai;
    return 301 https://$server_name$request_uri;
}
server {
    listen 443 ssl http2;
    server_name arkaim.ai;

    ssl_certificate /etc/letsencrypt/live/arkaim.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/arkaim.ai/privkey.pem;

    # Security headers (дублируют Next.js headers для прямого доступа)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    # Прямой доступ к API (если нужен вне Next.js rewrites)
    location ~ ^/(health|auth|book|api|book|xray|v1|analytics|metrics) {
        proxy_pass http://127.0.0.1:8642;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/arkaim /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d arkaim.ai

# Обновить .env
# FRONTEND_URL=https://arkaim.ai
# PUBLIC_BASE_URL=https://arkaim.ai
# ALLOWED_ORIGINS=https://arkaim.ai
```

---

## Проверка после деплоя

1. `curl https://ваш-домен.com/health` → `{"status":"ok"}`
2. `curl https://ваш-домен.com/docs` → Swagger UI
3. Отправить `/login` боту → inline keyboard с кликабельной ссылкой
4. Проверить CORS: `curl -H "Origin: https://evil.com" https://ваш-домен.com/book/ask` → 403/blocked
