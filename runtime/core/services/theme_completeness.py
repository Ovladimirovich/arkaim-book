"""M24 — измеримый критерий полноты тем книги в Knowledge Core (read-only).

Определения (зафиксированы 2026-10-15):

- **Тема книги** — запись эталонного реестра ``GENOME_v*.json`` → ``modules.themes``
  (схема ``SCHEMAS/THEME.schema.json``: id ``theme_NNN``, name, description, strength).
  Это авторитетный список: он версионирован, является Source of Truth для
  ``GET /book/genome`` и питает autocomplete/search/ExpansionLayer. Список тем не
  выводится эвристикой или LLM — берётся только реестр.

  Отличия от соседних понятий (не путать):
  - сущность (entity) — узел WorldModel/WorldEngine (``region_arkaim`` …), subject
    Knowledge Card; тема может совпадать по имени с сущностью, но это разные сущности;
  - событие (event) — canonical event (claim→event→epoch→temporal, M17/M18/M21);
  - факт (claim) — утверждение с provenance (``book:chunk_…``, AUTHOR_CANON);
  - связь (link) — подтверждённая пара (screenplay_links / claim_temporal_links);
  - search-match — кандидат скоринга related_entities/retriever, НЕ доказательство
    присутствия (retrieval может не вернуть известную тему — «retrieval trap»).

- **Присутствие темы (presence test)** проверяется только прямым lookup'ом по
  закреплённым данным, без retrieval:
  - book-покрытие: ≥1 чанк ``enriched_catalog.json`` с точным нормализованным
    тегом имени темы (те же теги использует ``BookRetriever._theme_fallback``);
  - expansion-покрытие: ключ в ``ExpansionLoader._knowledge`` (DERIVED).

Статусы (семантика трассировки ``TraceabilityStatus``; MISSING — явный статус
этого критерия, НЕ путать с UNAVAILABLE из evidence: источник данных доступен,
данных по теме нет):

- COMPLETE — доказано book-покрытие (точный тег каталога);
- PARTIAL — книжное покрытие не доказано точно: есть только близкие кандидаты-теги
  (substring / token-subset) и/или только expansion-покрытие (GO-1: путь утверждения
  обрывается честно, без домысливания);
- MISSING — ни точных, ни близких тегов, ни expansion-ключа: данных по теме нет.

Метрики отчёта: total / present / partial / missing / needs_resolution /
percent_complete / problem_topics (PARTIAL + MISSING с причинами).
Read-only: ничего не пишет, не меняет WorldModel/Temporal/API.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("hermes.theme_completeness")

_THEME_ID_RE = re.compile(r"^theme_[0-9]+$")

STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIAL"
STATUS_MISSING = "MISSING"

__all__ = [
    "STATUS_COMPLETE",
    "STATUS_PARTIAL",
    "STATUS_MISSING",
    "ThemeEvaluation",
    "load_reference_themes",
    "build_catalog_theme_index",
    "evaluate_theme",
    "build_theme_completeness_report",
]


@dataclass(frozen=True)
class ThemeEvaluation:
    """Итог проверки одной темы эталонного реестра."""

    theme_id: str
    name: str
    status: str
    exact_chunk_ids: tuple[str, ...] = ()
    near_matches: tuple[str, ...] = ()
    in_expansion: bool = False
    needs_resolution: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "status": self.status,
            "exact_chunk_ids": list(self.exact_chunk_ids),
            "near_matches": list(self.near_matches),
            "in_expansion": self.in_expansion,
            "needs_resolution": self.needs_resolution,
            "reason": self.reason,
        }


def _norm(text: Any) -> str:
    """Детерминированная нормализация имени темы.

    Как у ``BookRetriever._normalize_text`` (casefold + схлопывание пробелов),
    плюс сведение «ё»→«е»: каталог и геном могут писать ё по-разному.
    Эвристик/машинного обучения нет — сравнение точное после нормализации.
    """
    return " ".join(str(text or "").casefold().replace("ё", "е").split())


def load_reference_themes(genome_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Загрузить эталонный реестр тем из генома (authoritative reference list).

    Возвращает ``(themes, invalid)``: ``invalid`` — записи реестра без валидного
    ``id`` (схема ``theme_NNN``) или ``name``; такие записи честно фиксируются,
    но не участвуют в метриках полноты (не падаем и не выдумываем замену).
    """
    data = json.loads(Path(genome_path).read_text(encoding="utf-8"))
    themes = (data.get("modules") or {}).get("themes") or []
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for raw in themes:
        if not isinstance(raw, dict):
            invalid.append({"raw": raw, "reason": "запись не объект"})
            continue
        theme_id = str(raw.get("id") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not _THEME_ID_RE.fullmatch(theme_id):
            invalid.append({"id": theme_id, "name": name, "reason": "id не соответствует схеме theme_NNN"})
            continue
        if not name:
            invalid.append({"id": theme_id, "reason": "пустое name"})
            continue
        valid.append(raw)
    return valid, invalid


def build_catalog_theme_index(catalog_path: Path) -> dict[str, list[str]]:
    """Индекс «нормализованный тег темы → chunk_id» из enriched_catalog.json.

    Прямой file lookup по тому же каталогу, которым владеет
    ``BookRetriever._theme_fallback`` (темы — теги чанков). Порядок chunk_id
    детерминирован (порядок чанков в каталоге), дубли исключены.
    """
    entries = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    index: dict[str, list[str]] = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        chunk_id = str(entry.get("id") or entry.get("chunk_id") or "").strip()
        if not chunk_id:
            continue
        raw_themes = entry.get("themes", [])
        if isinstance(raw_themes, str):
            raw_themes = [part.strip() for part in raw_themes.split(",") if part.strip()]
        for tag in raw_themes if isinstance(raw_themes, list) else []:
            key = _norm(tag)
            if not key:
                continue
            bucket = index.setdefault(key, [])
            if chunk_id not in bucket:
                bucket.append(chunk_id)
    return index


def _near_matches(name_key: str, catalog_keys: set[str]) -> list[str]:
    """Детерминированные близкие теги: substring / token-subset в обе стороны.

    Никакого fuzzy-скоринга: только точные включения строк или включения
    множеств токенов. Результат сортируется для воспроизводимости.
    """
    if not name_key:
        return []
    name_tokens = set(name_key.split())
    matches: list[str] = []
    for tag in catalog_keys:
        if tag == name_key:
            continue
        tag_tokens = set(tag.split())
        if name_key in tag or tag in name_key or (name_tokens and (name_tokens <= tag_tokens or tag_tokens <= name_tokens)):
            matches.append(tag)
    return sorted(matches)


def evaluate_theme(
    theme: dict[str, Any],
    catalog_index: dict[str, list[str]],
    expansion_keys: set[str] | None = None,
) -> ThemeEvaluation:
    """Оценить одну тему по прямым знаниям (без retrieval).

    presence-тест детерминирован: точное совпадение нормализованного имени с
    тегом чанка enriched_catalog (book-покрытие) либо близкие теги / ключ
    ExpansionLayer (частичное покрытие). Retrieval-скоринг не используется и
    не может изменить статус («retrieval trap»).
    """
    theme_id = str(theme.get("id") or "").strip()
    name = str(theme.get("name") or "").strip()
    name_key = _norm(name)
    expansion_keys = expansion_keys or set()
    in_expansion = bool(name_key) and name_key in expansion_keys

    exact = tuple(catalog_index.get(name_key, ())) if name_key else ()
    if exact:
        return ThemeEvaluation(
            theme_id=theme_id,
            name=name,
            status=STATUS_COMPLETE,
            exact_chunk_ids=exact,
            in_expansion=in_expansion,
            reason="точный тег темы в enriched_catalog (book-покрытие доказано)",
        )

    near = tuple(_near_matches(name_key, set(catalog_index)))
    if near or in_expansion:
        reasons = []
        if near:
            reasons.append(f"близкие теги каталога: {len(near)}")
        if in_expansion:
            reasons.append("только ExpansionLayer (DERIVED)")
        return ThemeEvaluation(
            theme_id=theme_id,
            name=name,
            status=STATUS_PARTIAL,
            near_matches=near,
            in_expansion=in_expansion,
            needs_resolution=bool(near),
            reason="; ".join(reasons),
        )

    return ThemeEvaluation(
        theme_id=theme_id,
        name=name,
        status=STATUS_MISSING,
        reason="нет точных/близких тегов каталога и нет ключа ExpansionLayer",
    )


def _expansion_keys_or_empty() -> set[str]:
    """Ключи ExpansionLayer (DERIVED); сбой загрузки не фейлит отчёт."""
    try:
        from knowledge_expansion.expansion_loader import ExpansionLoader

        return {str(key) for key in ExpansionLoader().load()}
    except Exception as exc:  # pragma: no cover - зависит от окружения
        log.warning("theme_completeness_expansion_unavailable error=%s", exc)
        return set()


def build_theme_completeness_report(
    *,
    genome_path: Path,
    catalog_path: Path,
    expansion_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Собрать воспроизводимый отчёт полноты тем книги в Knowledge Core.

    Read-only: читает геном (эталон) и enriched_catalog (book-покрытие);
    ExpansionLayer — опциональный DERIVED-сигнал. Ничего не пишет и не меняет.
    """
    themes, invalid = load_reference_themes(genome_path)
    catalog_index = build_catalog_theme_index(catalog_path)
    if expansion_keys is None:
        expansion_keys = _expansion_keys_or_empty()

    evaluations = [evaluate_theme(theme, catalog_index, expansion_keys) for theme in themes]

    present = [item for item in evaluations if item.status == STATUS_COMPLETE]
    partial = [item for item in evaluations if item.status == STATUS_PARTIAL]
    missing = [item for item in evaluations if item.status == STATUS_MISSING]
    total = len(evaluations)

    problem_topics = [
        item.to_dict()
        for item in sorted(evaluations, key=lambda entry: entry.theme_id)
        if item.status != STATUS_COMPLETE
    ]

    return {
        "reference": {
            "source": str(genome_path),
            "field": "modules.themes",
            "invalid_records": invalid,
        },
        "total": total,
        "present": len(present),
        "partial": len(partial),
        "missing": len(missing),
        "needs_resolution": sum(1 for item in evaluations if item.needs_resolution),
        "percent_complete": round(len(present) * 100.0 / total, 2) if total else 0.0,
        "problem_topics": problem_topics,
    }


if __name__ == "__main__":  # pragma: no cover - ручной прогон на реальных данных
    import sys

    # repo_root/core/CORE — там shared `config` (GENOME_DIR/KNOWLEDGE_DIR),
    # тот же путь, что pythonpath=["core/CORE"] в pytest.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
    from config import config

    report = build_theme_completeness_report(
        genome_path=config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json",
        catalog_path=config.KNOWLEDGE_DIR / "enriched_catalog.json",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))



