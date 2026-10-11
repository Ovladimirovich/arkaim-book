# M8.1 — Простыми словами

## Цель
Собрать разрозненные temporal-компоненты (M5/M6/M8) в единую цепочку:
**PRESENT → ARKAIM → FUTURE**

## Что было
- M8 работал только как `Arkaim → Future` (без связи с настоящим)
- `temporal_today` (современность) существовал как метод, но не был в графе
- Dва "Аркаима" в графе: один с provenance (орфан), другой без (канонический)
- M8 не маркировал сценарии будущего — они выходили без provenance

## Что сделано

### 1. Present (современность)
- `temporal_today` теперь в графе как методологическая точка отсчёта
- Provenance исправлен: HYPOTHESIS (не AUTHOR_CANON — современность читателя не является канонтом книги)
- Нет relations от today — это не исторический факт

### 2. Present → Arkaim
- Это computed path, НЕ graph relation
- Метод `_trace_backward("temporal_arkaim_era")` строит цепочку назад от якоря
- Никакого ребра в графе не создаётся — это правильно, потому что нет evidence для исторической связи

### 3. Два Аркаима → один
- Канонический: `temporal_arkaim_era` (в chain, с relations)
- Орфан `temporal_arkaim_anchor` удалён
- provenance enriched: AUTHOR_CANON (книга) + EXTERNAL_SOURCE (археология)
- confidence = 0.85

### 4. Future
- Сценарии M8 теперь маркируются `FUTURE_EXTRAPOLATION` (category уже существовал, но не использовался)
- Это явно указывает: "проекция в будущее, не исторический факт"

### 5. Оркестрация
- `WorldEngine.get_full_temporal_pipeline()` собирает всё вместе
- M8 остаётся standalone engine (не менялся алгоритм)

## Тесты
- 32 новых теста M8.1 — все PASS
- 186 temporal-тестов — все PASS
- 2 старых теста исправлены (他们的 assertions проверяли старое поведение)

## Финальный статус
**M8.1 — IMPLEMENTED ✅**
