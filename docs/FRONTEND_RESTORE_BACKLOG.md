# FRONTEND_RESTORE_BACKLOG

Единственный список функциональности, которую потенциально можно восстановить в arkaim-web из бывшего arkaim-web-v2.

Архитектурное решение (фиксация):
- arkaim-web - единственный frontend и единственное направление дальнейшей разработки.
- arkaim-web-v2 - удалён из репозитория как рабочее направление.
- Сравнения arkaim-web против arkaim-web-v2 больше не проводятся.

Пункты ниже - не код к копированию, а компактный бэклог полезной функциональности. Каждый пункт проверяется к восстановлению отдельно, по факту нужды. Статус пунктов отражает текущую реализацию; новые пункты начинаются только после отдельного OWNER-GO.

Порядок реализации согласован OWNER (2026-09-30): **B3 → B1 → B2**, каждый пункт начинается только после отдельного OWNER-GO. Статус пункта меняется с TODO на IN PROGRESS исключительно этим GO.

Подтверждено кодом arkaim-web на дату согласования:
- B3: `shared/ui/SourceBadge.tsx` принимает только `sourceType`; контракт `AskAnswer` в arkaim-web уже содержит `source` / `pulse_confidence` / `llm_used`.
- B1: `shared/lib/guards.tsx` экспортирует только `ProtectedRoute` и `RoleGuard` (список ролей), слоя решений по матрице нет.
- B2: `app/reading/page.tsx` — базовая страница (~184 строки), `widgets/reading` отсутствует.

Исключено из бэклога (проверено аудитом): простые дубликаты arkaim-web (client.ts, errors.ts, envelope.ts - только EOL-различие; все contracts; realtime; generated/schema.d.ts), мёртвый код (useStreamingChat - 0 вызовов в обоих), и страницы/функции, которые в arkaim-web уже есть в суперсете.

---

## B1. RBAC / контроль доступа по матрице backend
- Назначение: единая точка решений UI "можно ли пользователю это действие/маршрут" на основе фактической матрицы прав backend, а не хардкода.
- Описание: can(role, path, method) поверх committed-слепка матрицы; roleLevel/hasAnyRole/minRoleFor (reader=0, editor=1, admin=2); реестр backend-дефектов маршрутов; роль-фильтр навигации; гейт RoleGate. В arkaim-web только shared/lib/guards.tsx (ProtectedRoute, RoleGuard по списку ролей) - матрицы прав нет.
- Приоритет: HIGH
- Что восстанавливать в arkaim-web: слой доступа от матрицы (can/minRoleFor/roleLevel + дефекты), роль-фильтр навигации, гейт; генератор матрицы из OpenAPI/RBAC-дампа backend.
- Источник в v2: src/shared/rbac (can.ts, navigation.ts, RoleGate.tsx; rbac/generated/matrix.ts git-игнор, источник contracts/rbac-matrix.json); тесты rbac.test.ts, login-b2.test.ts.
- Статус: TODO

## B2. Слой чтения книги (Reader UX)
- Назначение: полноценный читатель вместо базовой страницы чтения.
- Описание: список глав и читатель с передачей контекста, прогрессом, настройками (шрифт/тема), оглавлением TOC, верхней панелью; хуки навигации и настроек. В arkaim-web базовый app/reading/page.tsx без набора.
- Приоритет: HIGH
- Что восстанавливать в arkaim-web: читатель + список глав + TOC + прогресс + настройки + передача контекста в ask/world/temporal.
- Источник в v2: src/entities/reader (ChapterList, ChapterReader, types); src/widgets/reading (ReadingContextActions, ReadingProgress, ReadingSettings, ReadingTOC, ReadingTopbar); src/shared/reading (useReadingNavigation, useReadingSettings); e2e reading-flow.spec.ts.
- Статус: TODO

## B3. SourceBadge по контракту ответа (source / pulse_confidence / llm_used)
- Назначение: достоверный бейдж источника ответа (Pulse/RAG/тема/LLM-синтез) + уверенность, вместо свёрнутой строки sourceType.
- Описание: бейдж читает реальные поля /book/ask. Аудит подтвердил: backend keeper.act заполняет source (префиксы knowledge:rag, knowledge:theme, pulse, иначе Голос), pulse_confidence, llm_used; DTO AskAnswer (contracts/book.ts, есть и в arkaim-web) описывает поля. В arkaim-web legacy-бейдж по sourceType без уверенности.
- Приоритет: HIGH
- Что восстанавливать в arkaim-web: расширить shared/ui/SourceBadge.tsx на source/confidence/llmUsed; переподключить app/ask, app/book, shared/ui/ChatBubble на поля AskAnswer. Fallback не нужен (поля заполняются на всех путях).
- Источник в v2: src/shared/ui/SourceBadge.tsx.
- Статус: IMPLEMENTED / VERIFIED (B3 завершён; приоритет backlog сохранён для возможных будущих расширений)

## B10. Унифицированный примитив состояний (StateView)
- Назначение: единый шаблон загрузки/пусто/ошибки вместо ad-hoc спиннеров.
- Описание: StateLoading (скелетоны), StateEmpty, StateError (с кнопкой повтора) + обёртка StateView.
- Приоритет: MEDIUM
- Что восстанавливать в arkaim-web: компонент примитива состояний; внедрение на экранах.
- Источник в v2: src/shared/ui/StateView.tsx.
- Статус: TODO

## B5. Инструмент typed-контрактов из OpenAPI и матрицы RBAC
- Назначение: автопроверка соответствия фронтенда OpenAPI backend и матрице прав; защита от дрейфа контрактов.
- Описание: committed-слепки contracts/openapi.json (290+ путей) и contracts/rbac-matrix.json (298 маршрутов) + пайплайн генерации. В arkaim-web есть schema.d.ts, но нет committed-слепков и скриптов сверки.
- Приоритет: MEDIUM
- Что восстанавливать в arkaim-web: committed-слепки OpenAPI/RBAC + скрипты fetch/generate/verify; шаг CI "контракты не дрейфуют".
- Источник в v2: contracts/openapi.json, contracts/rbac-matrix.json; scripts/contracts.mjs, fetch-contract.mjs, dump_rbac_matrix.py; тест contracts.test.ts.
- Статус: TODO

## B6. Зона предложений (drafts / email / presence) - UI
- Назначение: просмотр и одобрение предложений (черновики писем, presence-подсказки).
- Описание: страницы зоны proposals поверх существующих контрактов. В arkaim-web контракты есть, UI-страниц зоны нет.
- Приоритет: MEDIUM
- Что восстанавливать в arkaim-web: страницы/виджеты зоны proposals поверх контрактов.
- Источник в v2: app/(main)/proposals (drafts, email, presence); тесты drafts/email/presence.
- Статус: TODO

## B7. Модерация контента (admin moderation) - UI
- Назначение: админский экран модерации (одобрение/отклонение).
- Описание: отдельная страница модерации. В arkaim-web есть admin без модерации.
- Приоритет: LOW
- Что восстанавливать в arkaim-web: экран модерации поверх moderation-контрактов.
- Источник в v2: app/(main)/admin/moderation; тест moderation.test.ts.
- Статус: TODO

## B8. Экран графа знаний
- Назначение: навигационный экран графа.
- Описание: отдельная страница. В arkaim-web есть world-engine и related-entities (EntityCard), но отдельного экрана графа нет.
- Приоритет: LOW
- Что восстанавливать в arkaim-web: при нужде - экран графа (поверх /book/graph/stats).
- Источник в v2: app/(main)/graph; тест knowledge.test.ts.
- Статус: TODO

## B9. Экран статуса системы
- Назначение: диагностика состояния системы/провайдеров.
- Описание: страница статуса. Дублирует по смыслу xray/health, низкий приоритет.
- Приоритет: LOW
- Что восстанавливать в arkaim-web: только при нужде, либо покрыть существующим xray.
- Источник в v2: app/(main)/status.
- Статус: TODO

---

## Явно НЕ включено (дублирует или не имеет подтверждённой ценности)
- envelope.ts - идентичен arkaim-web (только CRLF/LF).
- shared/api (client.ts, errors.ts, studio.ts) и все contracts - arkaim-web содержит суперсет.
- shared/realtime (WS/SSE/xray-sse), generated/schema.d.ts - есть в arkaim-web.
- useStreamingChat - мёртвый код (0 вызовов) в обоих; живой стриминг arkaim-web - в app/ask.
- app/(main) upload/analytics/profile/help/community/world/temporal/world-explorer/xray/library/admin - уже в arkaim-web.
- Аудит-скрипты v2 (scripts f2/f3/forensic/live/adr-live-evidence/audit-sse) - разовые инструменты аудита, не функциональность.
