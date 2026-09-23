"""ProvenanceValidator — проверка достоверности и конфликтов фактов."""

from typing import List

from schemas.fact import Fact
from schemas.provenance import Provenance

PROVENANCE_PRECEDENCE = {
    "source": 5,
    "derived": 4,
    "interpretation": 3,
    "external": 2,
    "hypothesis": 1,
}


class Conflict:
    """Описание конфликта между фактами."""

    def __init__(self, existing_fact_id: str, new_fact_id: str,
                 reason: str, severity: str):
        self.existing_fact_id = existing_fact_id
        self.new_fact_id = new_fact_id
        self.reason = reason
        self.severity = severity

    def to_dict(self) -> dict:
        return {
            "existing_fact_id": self.existing_fact_id,
            "new_fact_id": self.new_fact_id,
            "reason": self.reason,
            "severity": self.severity,
        }


class ProvenanceValidator:
    """Валидатор происхождения фактов.

    Проверяет:
    - может ли утверждение быть прямым фактом (source)
    - может ли быть выведено из других фактов (derived)
    - есть ли конфликты с существующими фактами
    """

    @staticmethod
    def can_be_direct(statement: str, document_text: str) -> bool:
        """Проверить, содержится ли утверждение в тексте документа.

        Выполняет нормализованное текстовое сравнение.
        """
        norm_stmt = statement.lower().strip()
        norm_doc = document_text.lower()
        return norm_stmt in norm_doc

    @staticmethod
    def can_be_derived(source_facts: List[Fact], derived: Fact) -> bool:
        """Проверить, может ли факт быть выведен из source-фактов.

        Требуется хотя бы один source-факт о той же сущности.
        """
        if not source_facts:
            return False
        for sf in source_facts:
            if sf.entity_id == derived.entity_id:
                return True
        return False

    @staticmethod
    def check_conflicts(new_fact: Fact,
                        existing_facts: List[Fact]) -> List[Conflict]:
        """Найти конфликты между новым фактом и существующими.

        Конфликт = противоречивые утверждения об одной сущности.
        """
        conflicts = []
        for existing in existing_facts:
            if existing.entity_id != new_fact.entity_id:
                continue
            if existing.id == new_fact.id:
                continue
            if _statements_contradict(existing.statement, new_fact.statement):
                severity = _resolve_severity(existing.provenance,
                                             new_fact.provenance)
                conflicts.append(Conflict(
                    existing_fact_id=existing.id,
                    new_fact_id=new_fact.id,
                    reason=_describe_conflict(existing, new_fact),
                    severity=severity,
                ))
        return conflicts

    @staticmethod
    def resolve_conflict(existing: Provenance, new: Provenance) -> str:
        """Какой факт имеет приоритет при конфликте."""
        existing_rank = PROVENANCE_PRECEDENCE.get(existing.type, 0)
        new_rank = PROVENANCE_PRECEDENCE.get(new.type, 0)
        if existing_rank > new_rank:
            return "existing"
        elif new_rank > existing_rank:
            return "new"
        return "flag"  # equal rank — requires human review

    @staticmethod
    def get_stats() -> dict:
        return {
            "provenance_order": PROVENANCE_PRECEDENCE,
        }


# ── Вспомогательные функции ─────────────────


def _statements_contradict(a: str, b: str) -> bool:
    """Эвристика: утверждения противоречат друг другу."""
    a_lower = a.lower()
    b_lower = b.lower()
    negation_words = ["не", "никогда", "нет", "нельзя", "запрещено"]

    for word in negation_words:
        if word in a_lower and word not in b_lower:
            base_a = a_lower.replace(word, "").strip()
            if base_a in b_lower or _words_overlap(base_a, b_lower):
                return True
        if word in b_lower and word not in a_lower:
            base_b = b_lower.replace(word, "").strip()
            if base_b in a_lower or _words_overlap(base_b, a_lower):
                return True
    return False


def _words_overlap(a: str, b: str) -> bool:
    """Проверить пересечение значимых слов."""
    words_a = {w for w in a.split() if len(w) > 3}
    words_b = {w for w in b.split() if len(w) > 3}
    return len(words_a & words_b) > 0


def _describe_conflict(existing: Fact, new_fact: Fact) -> str:
    return (
        f"Существующий факт ({existing.provenance}): '{existing.statement[:60]}' "
        f"противоречит новому ({new_fact.provenance}): '{new_fact.statement[:60]}'"
    )


def _resolve_severity(existing_prov: str, new_prov: str) -> str:
    ranks = PROVENANCE_PRECEDENCE
    existing_rank = ranks.get(existing_prov, 0)
    new_rank = ranks.get(new_prov, 0)
    if existing_rank >= 4 and new_rank >= 4:
        return "high"
    if existing_rank >= 3 or new_rank >= 3:
        return "medium"
    return "low"
