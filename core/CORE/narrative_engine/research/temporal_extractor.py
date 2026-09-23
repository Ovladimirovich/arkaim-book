"""TemporalExtractor — извлечение temporal фактов из текста книги.

M10: словарь temporal маркеров (стиль entity_extractor.KNOWN_ENTITIES).

Provenance-контракт (инварианты M1/M10):
  - Прямая дата/временной факт, явно присутствующий в книге → AUTHOR_CANON
  - Интерпретация/нормализация временного выражения → DERIVED
  - DERIVED никогда не классифицируется как AUTHOR_CANON
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)

log = logging.getLogger("hermes.narrative.temporal_extractor")


# ── Temporal Finding ─────────────────────────────────────────────────

@dataclass
class TemporalFinding:
    """Находка temporal факта из книги.

    kind:
      absolute_date — прямое указание даты ("~4000 лет до н.э.") → AUTHOR_CANON
      relative_period — относительное выражение ("многие века") → DERIVED
    """
    id: str
    kind: str                      # absolute_date | relative_period
    raw_text: str                  # найденный фрагмент
    value: str                     # нормализованное значение
    line_number: int
    context: str = ""              # строка книги для аудита
    category: ProvenanceCategory = ProvenanceCategory.DERIVED
    confidence: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_provenance_tag(self) -> ProvenanceTag:
        return ProvenanceTag(
            source_level=SourceLevel.CANON if self.category == ProvenanceCategory.AUTHOR_CANON else SourceLevel.AUTHOR_INTERPRETATION,
            category=self.category,
            confidence=self.confidence,
            source_title="КНИГА.md",
            notes=f"M10 extraction: {self.raw_text!r} -> {self.value} (line {self.line_number})",
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "raw_text": self.raw_text,
            "value": self.value,
            "line_number": self.line_number,
            "context": self.context[:200],
            "category": self.category.value,
            "confidence": self.confidence,
        }


# ── Словари temporal маркеров ────────────────────────────────────────

# Абсолютные даты — прямые утверждения книги → AUTHOR_CANON
ABSOLUTE_PATTERNS: list[tuple[str, re.Pattern]] = [
    # "~4000 лет до н.э.", "около 7000 до нашей эры"
    (r"(\d{1,5})\s*(?:тысячелети[еи]|лет)\s*(?:до\s*(?:н\.?\s*э\.?|нашей\s+эры))", re.compile(
        r"(\d{1,5})\s*(?:тысячелети[еи]|лет)\s*до\s*(?:н\.?\s*э\.?|нашей\s+эры)", re.IGNORECASE)),
    # "в 4000 году до н.э."
    (r"в\s+(\d{1,5})\s*(?:году|г\.?)\s*до", re.compile(
        r"в\s+(\d{1,5})\s*(?:году|г\.?)\s*до", re.IGNORECASE)),
    # "в эпоху X" / "во время X" / "в эпохе X" — именованная эпоха (1-3 слова, не-жадно)
    (r"(?:в|во)\s+(?:эпоху|эпохе|время)\s+([А-Яа-яЁё\-]+(?:\s+[А-Яа-яЁё\-]+){0,2})", re.compile(
        r"(?:в|во)\s+(?:эпоху|эпохе|время)\s+([А-Яа-яЁё\-]+(?:\s+[А-Яа-яЁё\-]+){0,2})", re.IGNORECASE)),
]

# Относительные выражения — интерпретация/нормализация → DERIVED
RELATIVE_PATTERNS: list[tuple[str, re.Pattern]] = [
    (r"многие\s+век(а|ов)", re.compile(r"многие\s+век(а|ов)", re.IGNORECASE)),
    (r"многие\s+тысячелети(я|й)", re.compile(r"многие\s+тысячелети(я|й)", re.IGNORECASE)),
    (r"спустя\s+тысячелети(я|й)", re.compile(r"спустя\s+тысячелети(я|й)", re.IGNORECASE)),
    (r"несколько\s+(?:веков|тысячелетий|поколений)", re.compile(
        r"несколько\s+(?:веков|тысячелетий|поколений)", re.IGNORECASE)),
    (r"древн(ие|их)\s+времен", re.compile(r"древн(ие|их)\s+времен", re.IGNORECASE)),
]

# Известные эпохи из WorldModel — для матчинга именованных эпох
KNOWN_EPOCH_NAMES = {
    "кали юга": "kali_yuga",
    "сатья юга": "satya_yuga",
    "трета юга": "treta_yuga",
    "двапара юга": "dvapara_yuga",
    "аркаим": "arkaim_era",
    "гиперборея": "hyperborea_era",
    "гардарика": "gardarika_era",
}


class TemporalExtractor:
    """Извлечение temporal фактов из текста книги.

    Read-only по тексту. Graceful: ошибки → пустой список + лог.
    """

    def __init__(self, known_epochs: Optional[dict[str, str]] = None):
        self._known_epochs = known_epochs or KNOWN_EPOCH_NAMES

    def extract(self, text: str) -> list[TemporalFinding]:
        """Извлечь все temporal факты из текста.

        Returns list[TemporalFinding]; при ошибке — [] (graceful).
        """
        findings: list[TemporalFinding] = []
        if not text or not text.strip():
            return findings

        try:
            lines = text.split("\n")
            for line_num, line in enumerate(lines, start=1):
                # Абсолютные даты → AUTHOR_CANON
                for pattern_name, pattern in ABSOLUTE_PATTERNS:
                    for match in pattern.finditer(line):
                        finding = self._make_absolute_finding(
                            match, pattern_name, line, line_num
                        )
                        if finding:
                            findings.append(finding)

                # Относительные выражения → DERIVED
                for pattern_name, pattern in RELATIVE_PATTERNS:
                    for match in pattern.finditer(line):
                        finding = self._make_relative_finding(
                            match, pattern_name, line, line_num
                        )
                        if finding:
                            findings.append(finding)

        except Exception as e:
            log.warning("temporal_extraction_error error=%s", e)
            return []

        # Dedupe: одна и та же строка + паттерн + позиция
        seen: set[str] = set()
        unique: list[TemporalFinding] = []
        for f in findings:
            key = f"{f.kind}:{f.raw_text}:{f.line_number}"
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def _make_absolute_finding(
        self, match: re.Match, pattern_name: str, line: str, line_num: int
    ) -> Optional[TemporalFinding]:
        """Абсолютная дата — прямое утверждение книги → AUTHOR_CANON.

        Именованная эпоха («в эпоху Кали Юги») распознаётся по наличию
        группы с названием и успешному матчингу к KNOWN_EPOCH_NAMES.
        """
        raw = match.group(0)

        # Именованная эпоха: группа с названием + матч к известным эпохам
        if match.groups():
            group_val = match.group(1).strip().lower()
            epoch_id = self._match_known_epoch(group_val)
            if epoch_id:
                return TemporalFinding(
                    id=f"abs_epoch_{epoch_id}_L{line_num}",
                    kind="absolute_date",
                    raw_text=raw,
                    value=f"epoch:{epoch_id}",
                    line_number=line_num,
                    context=line.strip()[:300],
                    category=ProvenanceCategory.AUTHOR_CANON,
                    confidence=0.9,
                )
            # Группа есть, но это не известная эпоха:
            #   - если в группе цифры → числовая дата (паттерны «N лет до н.э.»)
            #   - иначе (напр. «во время этих циклов») → НЕ temporal-факт, skip
            if not any(ch.isdigit() for ch in group_val):
                return None

        # Числовая дата
        value = match.group(0)
        return TemporalFinding(
            id=f"abs_date_L{line_num}_{self._slug(raw)}",
            kind="absolute_date",
            raw_text=raw,
            value=value,
            line_number=line_num,
            context=line.strip()[:300],
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=0.9,
        )

    def _make_relative_finding(
        self, match: re.Match, pattern_name: str, line: str, line_num: int
    ) -> Optional[TemporalFinding]:
        """Относительное выражение — нормализация → DERIVED (не canon!)."""
        raw = match.group(0)
        # Нормализация — это интерпретация, поэтому DERIVED
        normalized = self._normalize_relative(raw)
        return TemporalFinding(
            id=f"rel_{self._slug(raw)}_L{line_num}",
            kind="relative_period",
            raw_text=raw,
            value=normalized,
            line_number=line_num,
            context=line.strip()[:300],
            category=ProvenanceCategory.DERIVED,
            confidence=0.5,
        )

    def _match_known_epoch(self, epoch_name: str) -> Optional[str]:
        """Матчинг именованной эпохи к известной из WorldModel.

        Устойчив к падежным окончаниям («юги»~«юга») и к жадному
        захвату соседних слов («Кали Юги многие» → пробуем префиксы).
        """
        name = epoch_name.lower().strip().rstrip(".,;:!?")
        words = name.split()
        if not words:
            return None

        def _stem(w: str) -> str:
            # грубая основа: снять падежное окончание (последний символ
            # для слов от 3 символов). Безопасно: сравнение только
            # против известного словаря эпох.
            return w[:-1] if len(w) >= 3 else w

        def _try_match(cand_words: list[str]) -> Optional[str]:
            cand = " ".join(cand_words)
            for known, epoch_id in self._known_epochs.items():
                # Прямое вхождение (covers «аркаима» ⊃ «аркаим»)
                if known in cand:
                    return epoch_id
                k_words = known.split()
                if len(k_words) != len(cand_words):
                    continue
                # пословное сравнение основ (covers падежи: «юги»~«юга»)
                if all(_stem(a) == _stem(b) for a, b in zip(cand_words, k_words)):
                    return epoch_id
            return None

        # Пробуем полное имя, затем префиксы (жадный захват соседних слов)
        for n in range(len(words), 0, -1):
            result = _try_match(words[:n])
            if result:
                return result
        return None

    @staticmethod
    def _normalize_relative(raw: str) -> str:
        """Нормализация относительного выражения (интерпретация → DERIVED)."""
        r = raw.lower()
        if "тысячелети" in r:
            return "period:MILLENNIUM"
        if "век" in r:
            return "period:CENTURY"
        if "поколени" in r:
            return "period:GENERATIONS"
        if "древн" in r:
            return "period:ANCIENT"
        return "period:RELATIVE"

    @staticmethod
    def _slug(text: str) -> str:
        import hashlib
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
