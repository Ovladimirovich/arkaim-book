# Развертывание (Deployment)

## 1. Cloudflare Tunnel (рекомендуется)

Единственный способ опубликовать систему в интернет **без открытия портов на роутере**.

### 1.1 Установка cloudflared

```powershell
# Скачать cloudflared для Windows
curl.exe -L -o cloudflared.msi https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi
msiexec /i cloudflared.msi
```

### 1.2 Аутентификация и создание туннеля

```powershell
# Войти в аккаунт Cloudflare
cloudflared tunnel login

# Создать туннель
cloudflared tunnel create arkaim-tunnel

# Полученный ID туннеля (далее TUNNEL_ID)
```

### 1.3 Настройка DNS

В панели Cloudflare → DNS → добавить запись:

```
Тип: CNAME
Имя: arkaim (или ваш поддомен)
Цель: TUNNEL_ID.cfargotunnel.com
Proxy status: Proxied (оранжевое облако)
```

### 1.4 Конфигурация туннеля

Создать `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: TUNNEL_ID
credentials-file: C:\Users\1\.cloudflared\TUNNEL_ID.json

ingress:
  - hostname: arkaim.ваш-домен.ru
    service: http://localhost:8080
  - service: http_status:404
```

### 1.5 Запуск туннеля

```powershell
# Тестовый запуск (вручную, окно остаётся открытым)
cloudflared tunnel run arkaim-tunnel

# Запуск как Windows-сервис (через NSSM)
nssm install ArkaimTunnel "C:\Program Files\Cloudflared\cloudflared.exe" "tunnel run arkaim-tunnel"
nssm start ArkaimTunnel
```

### 1.6 Проверка

```powershell
# Из внешнего мира
curl https://arkaim.ваш-домен.ru/health

# Внутренние порты не должны слушать на 0.0.0.0
netstat -ano | findstr ":8080 "  # должен быть 127.0.0.1:8080
netstat -ano | findstr ":8642 "  # должен быть 127.0.0.1:8642
```

---

## 2. Настройка OAuth-приложений

### 2.1 Telegram Login

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Создайте бота или выберите существующего
3. Отправьте `/setdomain` и укажите ваш публичный домен (например `arkaim.ваш-домен.ru`)
4. В `.env` заполните:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   TELEGRAM_BOT_USERNAME=username_бота
   TELEGRAM_ADMIN_CHAT_ID=ваш_chat_id
   ```

### 2.2 Google OAuth

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект → APIs & Services → Credentials
3. Создайте OAuth 2.0 Client ID (Web application)
4. Authorized redirect URIs: `https://arkaim.ваш-домен.ru/auth/google/callback`
5. В `.env` заполните:
   ```
   GOOGLE_CLIENT_ID=ваш_client_id
   GOOGLE_CLIENT_SECRET=ваш_client_secret
   GOOGLE_REDIRECT_URI=https://arkaim.ваш-домен.ru/auth/google/callback
   ```

---

## 3. NSSM — Windows-сервисы

### 3.1 Установка NSSM

```powershell
winget install nssm
# или скачать вручную: https://nssm.cc/download
```

### 3.2 Регистрация сервисов

```powershell
# Gateway
nssm install ArkaimGateway "C:\Python314\python.exe" "-m uvicorn gateway.main:app --host 127.0.0.1 --port 8080"
nssm set ArkaimGateway AppDirectory C:\ПРОЕКТ_Наследие_Аркаима\runtime
nssm set ArkaimGateway AppEnvironmentExtra GATEWAY_HOST=127.0.0.1 GATEWAY_PORT=8080 CORE_HOST=127.0.0.1 CORE_PORT=8642
nssm set ArkaimGateway Start SERVICE_AUTO_START
nssm set ArkaimGateway AppStdout C:\ПРОЕКТ_Наследие_Аркаима\runtime\logs\gateway.log
nssm set ArkaimGateway AppStderr C:\ПРОЕКТ_Наследие_Аркаима\runtime\logs\gateway-error.log

# Core
nssm install ArkaimCore "C:\Python314\python.exe" "-m uvicorn core.main:app --host 127.0.0.1 --port 8642"
nssm set ArkaimCore AppDirectory C:\ПРОЕКТ_Наследие_Аркаима\runtime
nssm set ArkaimCore Start SERVICE_AUTO_START
nssm set ArkaimCore AppStdout C:\ПРОЕКТ_Наследие_Аркаима\runtime\logs\core.log
nssm set ArkaimCore AppStderr C:\ПРОЕКТ_Наследие_Аркаима\runtime\logs\core-error.log
```

---

## 4. Переменные окружения (.env)

Копировать `runtime/.env.template` → `runtime/.env` и заполнить:

| Переменная | Обязательно | Описание |
|---|---|---|
| `PUBLIC_BASE_URL` | Да | `https://arkaim.ваш-домен.ru` |
| `SESSION_SECRET` | Да | Случайная строка (генерация: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `TELEGRAM_BOT_TOKEN` | Для Telegram | Токен от @BotFather |
| `TELEGRAM_BOT_USERNAME` | Для Telegram | Username бота |
| `GOOGLE_CLIENT_ID` | Для Google | ID из Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Для Google | Secret из Google Cloud Console |
| `HERMES_API_KEY` | Рекомендуется | Ключ для service-to-service коммуникации |
| `ALLOWED_ORIGINS` | Рекомендуется | `https://arkaim.ваш-домен.ru` |
| `GIGACHAT_CLIENT_ID/SECRET` | Для GigaChat | От Сбера |

---

## 5. Резервное копирование

```powershell
# Сохранить в скрипт runtime/scripts/backup.ps1
$date = Get-Date -Format "yyyy-MM-dd"
$backup = "C:\backups\arkaim-$date"
New-Item -ItemType Directory -Path $backup -Force | Out-Null

# Базы данных
Copy-Item "$env:RUNTIME_DIR\memory\data\*.db" $backup
Copy-Item "$env:RUNTIME_DIR\.env" $backup

# ChromaDB (векторная база, большая)
# Copy-Item "$env:PROJECT_ROOT\ARKAIM_DIGITAL_CONSCIOUSNESS\CHROMA_DB" $backup -Recurse

# ОС Data
Copy-Item "$env:PROJECT_ROOT\OS_DATA" $backup -Recurse -ErrorAction SilentlyContinue

Compress-Archive -Path $backup\* -DestinationPath "$backup.zip"
Remove-Item $backup -Recurse
```

Добавить в планировщик Windows: ежедневно в 3:00.
