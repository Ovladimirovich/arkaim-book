"""ConflictResolver — проверка конфликтов новых фактов с существующими."""

from typing import List

from schemas.fact import Fact
from book_os.provenance_validator import ProvenanceValidator, Conflict


class ConflictResolver:
    """Разрешение конфликтов при добавлении новых фактов."""

    def __init__(self):
        self.validator = ProvenanceValidator()

    def check(self, new_facts: List[Fact],
              existing_facts: List[Fact]) -> List[Conflict]:
        """Проверить новые факты на конфликты с существующими."""
        all_conflicts = []
        for new_fact in new_facts:
            conflicts = self.validator.check_conflicts(new_fact, existing_facts)
            all_conflicts.extend(conflicts)
        return all_conflicts

    def has_high_severity_conflicts(self, conflicts: List[Conflict]) -> bool:
        """Есть ли конфликты высокой серьёзности."""
        return any(c.severity == "high" for c in conflicts)
