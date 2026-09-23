# Деплой с HTTPS для кликабельных ссылок

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
```

### Шаг 4: Перезапустить сервер
```bash
cd runtime && python -m core.main
```

### Шаг 5: Обновить URL бота в Telegram
```bash
# Установить новый URL для Webhook (если используется)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://abc123.trycloudflare.com/webhook/telegram"
```

**Готово!** Теперь inline keyboard будет работать.

---

## Вариант 2: ngrok (альтернатива)

### Установить
```bash
winget install ngrok.ngrok
```

### Запустить
```bash
ngrok http 3000
```

### Обновить .env
```
FRONTEND_URL=https://abc123.ngrok-free.app
```

---

## Вариант 3: VPS с доменом (продакшн)

### Подготовка
1. Купить домен (например, `arkaim.ai`)
2. Арендовать VPS (2 vCPU, 2GB RAM — достаточно)
3. Настроить DNS: `arkaim.ai` → IP сервера

### На сервере
```bash
# Установить
sudo apt update && sudo apt install nginx certbot python3-certbot-nginx

# Настроить nginx
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

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8642;
    }
}
EOF

# Активировать
sudo ln -s /etc/nginx/sites-available/arkaim /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Получить SSL
sudo certbot --nginx -d arkaim.ai

# Обновить .env
FRONTEND_URL=https://arkaim.ai
PUBLIC_BASE_URL=https://arkaim.ai
```

---

## После деплоя

### Обновить бота
```python
# В .env
FRONTEND_URL=https://ваш-домен.com
```

### Проверить
1. Отправить `/login` боту
2. Inline keyboard появится с кликабельной ссылкой
3. Кнопка "Войти в систему" ведёт на HTTPS URL
