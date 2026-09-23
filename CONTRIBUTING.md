# 🤝 Участие в проекте «Наследие Аркаима»

Спасибо за интерес к проекту! Мы рады любой помощи.

---

## 📋 Содержание

- [Кодекс поведения](#кодекс-поведения)
- [Как начать](#как-начать)
- [Структура проекта](#структура-проекта)
- [Правила разработки](#правила-разработки)
- [Процесс PR](#процесс-pr)
- [Стиль кода](#стиль-кода)
- [Тестирование](#тестирование)

---

## Кодекс поведения

- Уважайте автора книги и его замысел
- Книга — первичный источник истины
- Не предлагайте изменения архитектуры без обсуждения
- Все обсуждения ведутся на русском языке (код — на английском)

---

## Как начать

1. Форкните репозиторий
2. Клонируйте форк:
   ```bash
   git clone https://github.com/Ovladimirovich/arkaim.git
   cd arkaim
   ```
3. Создайте ветку для ваших изменений:
   ```bash
   git checkout -b feature/my-feature
   ```
4. Установите зависимости:
   ```bash
   # Backend
   cd runtime
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt

   # Frontend
   cd arkaim-web
   npm install
   ```
5. Запустите проект:
   ```bash
   cd ..
   start_all.bat
   ```

---

## Структура проекта

```
runtime/       — инфраструктура (FastAPI, auth, UI, gateway)
core/CORE/     — логика книги (Pulse, Voice, знания)
arkaim-web/    — фронтенд (Next.js + React)
arkaim-mobile/ — мобильное приложение (React Native + Expo)
docs/          — документация
scripts/       — вспомогательные скрипты
```

**Важно:** `runtime/core/` — точка соединения двух миров.
`core/CORE/pulse/` — сердце системы.

---

## Правила разработки

### Главные принципы

1. **Книга — первичный источник истины.** Никакие решения не принимаются на основе возможностей LLM.
2. **LLM — инструмент, не архитектура.** Личность книги — в Pulse, а не в system prompt.
3. **Pulse знает книгу без LLM.** Каждый слой может ответить на вопрос сам.
4. **Никаких автономных действий.** Система предлагает — автор решает.

### Voice-протокол

1. Pulse слушает вопрос → находит ответ в геноме
2. Если ответ найден с высокой уверенностью — Voice отвечает без LLM
3. Если уверенность низкая — LLM формулирует, Pulse проверяет
4. IdentityLayer.validate() — финальная проверка

### Запреты

❌ Не давай LLM system prompt, который заставляет её «быть книгой»
❌ Не создавай новый модуль, не проверив Pulse/layers/
❌ Не делай автономных действий (публикации, рассылки)
❌ Не удаляй файлы без подтверждения автора
❌ Не читай книгу через код прежде, чем создашь обработчик
❌ Не подключай UI прежде, чем создашь API

### Порядок разработки

```
1. Pulse (живое ядро)
2. Voice (голос книги)
3. Memory (память читателя)
4. Presence (присутствие)
5. Evolution (рост)
```

Любая новая функция должна проходить через Pulse. Не через LLM напрямую.

### Создание нового модуля

1. Проверь, не делает ли Pulse/layers уже это
2. Создай Pydantic-схему в `SCHEMAS/`
3. Создай модуль в `core/CORE/` или `runtime/core/`
4. Добавь Dependency в `runtime/core/adc_deps.py`
5. Если нужно — API эндпоинт в `runtime/core/routes/`
6. Добавь тесты
7. Обнови документацию

---

## Процесс PR

1. Создайте ветку от `develop`:
   ```bash
   git checkout -b feature/description
   ```
2. Внесите изменения
3. Запустите тесты:
   ```bash
   cd runtime && pytest -q
   cd arkaim-web && npx vitest run
   ```
4. Убедитесь, что линтер проходит:
   ```bash
   cd runtime && ruff check .
   cd arkaim-web && npm run lint
   ```
5. Закоммитьте с conventional commit:
   ```
   feat: add new visualization layer
   fix: correct entity search in World Engine
   refactor: simplify Voice protocol
   docs: update API documentation
   test: add tests for ReaderProfile
   ```
6. Откройте PR в `main` с описанием изменений

---

## Стиль кода

### Python
- Python 3.14+ с type hints
- async/await для I/O
- Pydantic для валидации
- snake_case для файлов и переменных
- ruff для линтинга (line-length: 160)
- Один модуль = одна ответственность

### TypeScript / React
- TypeScript 5+ (strict mode)
- FSD архитектура (entities / features / widgets / shared)
- React Server Components где возможно
- ESLint + Tailwind CSS

### Именование
- `snake_case` для Python-файлов, `.json` только для данных
- `.md` только для документации, `.yaml` только для конфигурации
- `UPPER_CASE` для корневых папок проекта
- `snake_case` для подпапок

---

## Тестирование

### Backend
```bash
cd runtime
pytest tests/ -q              # Все тесты
pytest tests/ -k "world" -v  # World Engine тесты
pytest tests/ -k "auth" -v   # Auth тесты
```

### Frontend
```bash
cd arkaim-web
npx vitest run                # Unit-тесты
npx playwright test           # E2E-тесты
```

---

## Вопросы

Если у вас есть вопросы, создайте [issue](https://github.com/Ovladimirovich/arkaim/issues) или свяжитесь с автором через Telegram.

Спасибо за ваш вклад в развитие цифрового сознания книги «Наследие Аркаима»! 📚✨

