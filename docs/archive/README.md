# docs/archive/ — Архив документации

> **Создан:** 2026-09-18 (R1 — Post-F4 Rebaseline & Documentation Cleanup)
> **Принцип:** Historical ≠ useless. Каждый документ сохранён с понятной исторической причиной.

---

## Структура архива

```
docs/archive/
├── md-line/          # Media-линейка: MD-1..MD-5, подэтапы M4.x
├── temporal/         # Temporal-линейка: M0..M10.2, все ADR-зависимые отчёты
├── frontend/         # F-линейка: F1..F4 (SPEC, AUDIT, REPORT, FOLLOWUP)
├── historical/       # Sprint-era, устаревшие статусы, internal/*
├── subsystems/       # Устаревшие подсистемные гайды (ComfyUI, World Engine и др.)
│   └── legacy_core_world/   # Legacy граф мира (бывший core/WORLD/) — см. ../../LEGACY_CORE_WORLD.md
└── completed/        # Завершённые аудиты и отчёты (DATA_DISCIPLINE, FORENSIC_*)
```

---

## Почему документы здесь

| Категория | Причина сохранения |
|-----------|-------------------|
| **md-line/** | Полный trace implement→accept для каждого MD-этапа; нужны при ревью архитектуры media-boundary |
| **temporal/** | Детали temporal-модели, provenance, M8.1-решений; reference при работе с world_engine |
| **frontend/** | F1–F4 реализованы и приняты; архив фиксирует что было сделано и почему |
| **historical/** | Sprint-era контекст; объясняет почему проект пришёл к текущей MD-линии |
| **subsystems/** | Исторические гайды; полезны для понимания эволюции архитектуры |
| **subsystems/legacy_core_world/** | Legacy граф мира (46 сущностей, 12 связей, 18 цитат); не используется кодом, сохранён как источник миграции. Детали: [`../../LEGACY_CORE_WORLD.md`](../../LEGACY_CORE_WORLD.md) |
| **completed/** | Аудиты и отчёты — proof-of-work для завершённых этапов |

---

## Ссылки

- Актуальное состояние → [`../CURRENT_DEVELOPMENT_STATE.md`](../CURRENT_DEVELOPMENT_STATE.md)
- Инвентарь всех документов → [`../DOCUMENTATION_INVENTORY.md`](../DOCUMENTATION_INVENTORY.md)
- Итоговый отчёт R1 → [`../POST_F4_REBASELINE.md`](../POST_F4_REBASELINE.md)
