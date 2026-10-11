# Правила TypeScript/React

- TypeScript 5+ (strict mode)
- FSD архитектура (entities / features / widgets / shared / app)
- React Server Components там, где можно
- ESLint + Tailwind CSS
- Строгая типизация — никогда не используйте `any` без крайней необходимости

## Структура arkaim-web/
- `src/app/` — страницы (34 шт.)
- `src/shared/` — UI-компоненты, хуки, типы, контексты
- `src/widgets/` — виджеты (Sidebar, AdminPanel и др.)
- `src/entities/` — бизнес-сущности
- `src/features/` — фичи
- `tests/unit/` — unit-тесты (vitest)

## API клиент
- `src/shared/lib/api.ts` — HTTP клиент
- `src/shared/lib/ws.ts` — WebSocket клиент
