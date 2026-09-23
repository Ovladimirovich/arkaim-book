"""
PresenceSuggester — предлагает автору действия на основе наблюдений.

Книга замечает, что читатели интересуются определёнными темами,
и сохраняет предложение: «автор, возможно, стоит написать пост об X».

Предложения никогда не публикуются автоматически.
Только сохраняются для просмотра и утверждения автором.
(Принцип 11, Принцип 15)
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.presence.suggester")

SUGGESTIONS_DIR = Path(__file__).resolve().parent.parent / "OS_DATA" / "suggestions"


@dataclass
class AuthorSuggestion:
    """
    Предложение автору.

    Никогда не выполняется автоматически.
    Автор смотрит → решает → делает или отклоняет.
    """
    id: str = ""
    topic: str = ""
    reason: str = ""                  # почему эта тема важна
    source: str = ""                  # reader_memory, keyword_trend, pulse_insight
    evidence: dict = field(default_factory=dict)  # цифры: сколько раз спросили, etc.
    suggested_action: str = ""        # "write_post", "expand_chapter", "clarify_topic"
    status: str = "pending"           # pending | viewed | approved | rejected
    created_at: str = ""
    viewed_at: str = ""
    author_comment: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class PresenceSuggester:
    """
    Формирует предложения автору на основе того,
    что заметил PresenceObserver.
    """

    def __init__(self, suggestions_dir: Optional[Path] = None):
        self._dir = suggestions_dir or SUGGESTIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._suggestions: dict[str, AuthorSuggestion] = {}
        self._load()

    # ── Загрузка / сохранение ────────────────────

    def _load(self):
        if not self._dir.exists():
            return
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                s = AuthorSuggestion(**data)
                self._suggestions[s.id] = s
            except Exception as e:
                log.warning("suggester_load_error path=%s error=%s", path, e)

    def _save(self, suggestion: AuthorSuggestion):
        path = self._dir / f"{suggestion.id}.json"
        path.write_text(
            json.dumps(suggestion.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Создание предложений ─────────────────────

    def suggest(self, topic: str, reason: str, suggested_action: str = "write_post", evidence: Optional[dict] = None) -> AuthorSuggestion:
        """
        Создать предложение для автора.

        Не публикует, не отправляет — только сохраняет.
        """
        import uuid
        now = datetime.now(tz=timezone.utc).isoformat()
        sid = f"suggest_{uuid.uuid4().hex[:12]}"

        # Проверить, нет ли уже активного предложения по этой теме
        for existing in self._suggestions.values():
            if existing.topic == topic and existing.status == "pending":
                log.info("suggester_duplicate_suggestion topic=%s existing_id=%s", topic, existing.id)
                return existing

        suggestion = AuthorSuggestion(
            id=sid,
            topic=topic,
            reason=reason,
            suggested_action=suggested_action,
            evidence=evidence or {},
            created_at=now,
        )
        self._suggestions[sid] = suggestion
        self._save(suggestion)
        log.info("suggester_created id=%s topic=%s action=%s", sid, topic, suggested_action)
        return suggestion

    # ── Управление статусом ──────────────────────

    def view(self, suggestion_id: str) -> Optional[AuthorSuggestion]:
        """Автор посмотрел предложение."""
        s = self._suggestions.get(suggestion_id)
        if s and s.status == "pending":
            s.status = "viewed"
            s.viewed_at = datetime.now(tz=timezone.utc).isoformat()
            self._save(s)
        return s

    def approve(self, suggestion_id: str) -> Optional[AuthorSuggestion]:
        """Автор одобрил предложение (будет действовать сам)."""
        s = self._suggestions.get(suggestion_id)
        if s:
            s.status = "approved"
            s.viewed_at = datetime.now(tz=timezone.utc).isoformat()
            self._save(s)
        return s

    def reject(self, suggestion_id: str, comment: str = "") -> Optional[AuthorSuggestion]:
        """Автор отклонил предложение."""
        s = self._suggestions.get(suggestion_id)
        if s:
            s.status = "rejected"
            s.author_comment = comment
            s.viewed_at = datetime.now(tz=timezone.utc).isoformat()
            self._save(s)
        return s

    # ── Чтение ───────────────────────────────────

    def list_pending(self) -> list[AuthorSuggestion]:
        """Все нерассмотренные предложения."""
        return [s for s in self._suggestions.values() if s.status == "pending"]

    def list_all(self, limit: int = 50) -> list[AuthorSuggestion]:
        """Все предложения (от новых к старым)."""
        sorted_sugs = sorted(
            self._suggestions.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )
        return sorted_sugs[:limit]

    def suggest_missing_visual(self, topic: str, reason: str, evidence: dict, example_visual: Optional[dict] = None) -> AuthorSuggestion:
        """Создать предложение о добавлении визуала.

        Используется X-Ray Visual Triggers и EvolutionTracker.
        """
        sug = self.suggest(
            topic=topic,
            reason=reason,
            suggested_action="add_visual",
            evidence=evidence,
        )
        if example_visual and sug:
            sug.evidence["example_visual"] = example_visual
            self._save(sug)
        return sug

    def get_stats(self) -> dict:
        stats = {"total": len(self._suggestions), "by_status": {}}
        for s in self._suggestions.values():
            stats["by_status"][s.status] = stats["by_status"].get(s.status, 0) + 1
        return stats

    # ── Генерация предложений из наблюдений ──────

    async def suggest_from_observations(self, observer) -> list[AuthorSuggestion]:
        """
        Автоматически создать предложения на основе текущих наблюдений.

        Вызывается периодически (например, раз в час).
        """
        if not hasattr(observer, "get_trending_topics"):
            return []

        trending = await observer.get_trending_topics(min_hits=3)

        created = []
        for obs in trending:
            # Определить действие на основе источника
            if "book_ask" in obs.sources:
                action = "write_post"
                reason = f"Читатели задали {obs.hit_count} вопросов о «{obs.keyword}»"
            else:
                action = "clarify_topic"
                reason = f"Тема «{obs.keyword}» упоминается в сообществах ({obs.hit_count} раз)"

            evidence = {
                "hits": obs.hit_count,
                "sources": obs.sources,
                "first_seen": obs.first_seen.isoformat(),
                "last_seen": obs.last_seen.isoformat(),
            }

            s = self.suggest(
                topic=obs.keyword,
                reason=reason,
                suggested_action=action,
                evidence=evidence,
            )
            created.append(s)

        return created
