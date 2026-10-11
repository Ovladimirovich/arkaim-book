# Правила Python

- Python 3.14+
- Type hints обязательны
- async/await для I/O
- Pydantic для валидации
- snake_case для файлов и переменных
- ruff (line-length: 160) — `ruff check . && ruff format .`
- Один модуль = одна ответственность
- Без `except: pass` — всегда обрабатывайте ошибки
- Секреты только через `.env` / env-переменные

## Тесты
- pytest в `runtime/tests/`
- Для каждого нового модуля — покрытие тестами
