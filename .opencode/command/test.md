---
description: Линт и тесты backend (ruff + pytest в runtime/)
agent: python-architect
---

Выполните проверку backend-части проекта:

1. Линтер: `cd runtime; ruff check .` (config: runtime/pyproject.toml, line-length 160).
2. Тесты: `cd runtime; python -m pytest tests/ -q` (asyncio_mode=auto).

Если каталог tests отсутствует или тестов нет — сообщите об этом.

Итог: PASS/FAIL, упавшие тесты с причинами и предложением фикса.

Аргументы пользователя (если были): $ARGUMENTS
