# Security Policy

## Поддерживаемые версии

| Версия | Поддержка |
|--------|-----------|
| 2.0.x  | ✅ |
| 1.0.x  | ✅ |
| < 1.0  | ❌ |

## Как сообщить о уязвимости

Если вы обнаружили уязвимость безопасности, **не создавайте публичный issue**. Напишите напрямую автору через Telegram.

**Никогда не коммитьте секреты в репозиторий.**

### Что считается секретом
- API-ключи LLM-провайдеров (GigaChat, OpenRouter)
- `SESSION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `VK_GROUP_TOKEN`
- SMTP-пароли
- `HERMES_API_KEY`

### Как это проверяется
- `.env` находится в `.gitignore`
- `.env.example` — только шаблон без реальных значений
- `git secrets` / GitHub secret scanning включены

### Автоматическая проверка
CI pipeline не запускает `bandit` или `pip-audit`, но вы можете запустить локально:
```bash
cd runtime
pip install bandit pip-audit
bandit -r .
pip-audit
```
