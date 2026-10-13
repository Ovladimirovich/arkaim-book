"""M10 — Screenplay→Book link candidate detection (suggest-only gate).

Deterministic candidate detection over the real project data:

- screenplay side: the 119 scenes of ``SYNOPSIS_DOCUMENT.json``
  (the canonical scene source, ids ``scene_###``);
- book side: the 824 chunks of ``enriched_chunks.json``
  (``chunk_p_####_<12hex>`` ids, the same ids used by the
  ``screenplay_links.json`` registry).

Scoring (no LLM, reproducible): word-bigram coverage of the scene text
found inside a chunk, plus a bonus for verbatim scene sentences that occur
in the chunk. This metric ranks all nine M16.1 owner-approved pairs as the
top candidate of their scene on the current data.

The module is **suggest-only** (architectural rule: the system proposes,
the owner decides): it never writes, approves, or mutates
``screenplay_links.json``. Confirmed links are created exclusively through
``knowledge.screenplay_links_provenance.approve_link``.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
SYNOPSIS_DOCUMENT_PATH = KNOWLEDGE_DIR / "SYNOPSIS_DOCUMENT.json"
ENRICHED_CHUNKS_PATH = KNOWLEDGE_DIR / "enriched_chunks.json"

_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?…]+")
# Scene sentences shorter than this are too generic for a verbatim quote.
_VERBATUM_MIN_LEN = 40

# Status of every candidate: proposals only, never a confirmed link.
SUGGEST_STATUS = "suggest"


@dataclass
class LinkCandidate:
    """A suggested screenplay-scene → book-chunk match (not confirmed)."""

    screenplay_scene_id: str
    book_chunk_id: str
    coverage: float
    verbatim_sentences: int
    verbatim_total: int
    score: float
    scene_title: str = ""
    chapter_title: str = ""
    status: str = SUGGEST_STATUS
    notes: str = field(default="")

    def to_dict(self) -> dict:
        """Serializable form (audit output; never written to the registry)."""
        return {
            "screenplay_scene_id": self.screenplay_scene_id,
            "book_chunk_id": self.book_chunk_id,
            "coverage": round(self.coverage, 4),
            "verbatim_sentences": self.verbatim_sentences,
            "verbatim_total": self.verbatim_total,
            "score": round(self.score, 4),
            "scene_title": self.scene_title,
            "chapter_title": self.chapter_title,
            "status": self.status,
            "notes": self.notes,
        }


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _bigrams(text: str) -> list[str]:
    ts = _tokens(text)
    return [f"{a}_{b}" for a, b in zip(ts, ts[1:])]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if len(s.strip()) >= _VERBATUM_MIN_LEN]


def score_scene_chunk(scene_text: str, chunk_text: str) -> tuple[float, int, int]:
    """(coverage, verbatim_matched, verbatim_total) between a scene and a chunk."""
    scene_bigrams = Counter(_bigrams(scene_text))
    chunk_bigram_set = set(_bigrams(chunk_text))
    shared = sum(count for bg, count in scene_bigrams.items() if bg in chunk_bigram_set)
    total = sum(scene_bigrams.values())
    coverage = shared / total if total else 0.0

    norm_chunk = _normalized(chunk_text)
    sentences = _sentences(scene_text)
    matched = sum(1 for sent in sentences if _normalized(sent) in norm_chunk)
    return coverage, matched, len(sentences)


def load_scenes(path: Optional[Path] = None) -> list[dict]:
    """The canonical screenplay scene list (SYNOPSIS_DOCUMENT, 119 scenes)."""
    path = path or SYNOPSIS_DOCUMENT_PATH
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    content = doc.get("content") if isinstance(doc, dict) else None
    scenes = content.get("chapters") if isinstance(content, dict) else None
    if not isinstance(scenes, list):
        return []
    return [scene for scene in scenes if isinstance(scene, dict) and str(scene.get("id") or "").startswith("scene_")]


def load_book_chunks(path: Optional[Path] = None) -> list[dict]:
    """Book chunks with id + text (enriched_chunks.json, the book side of links)."""
    path = path or ENRICHED_CHUNKS_PATH
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [c for c in data if isinstance(c, dict) and str(c.get("id") or "") and str(c.get("text") or "")]


def valid_chunk_ids(path: Optional[Path] = None) -> set[str]:
    """All chunk ids of the book chunk store."""
    return {str(c.get("id")) for c in load_book_chunks(path)}


def _scene_text(scene: dict) -> str:
    """The scored text of a scene: its body only.

    The title (header "14. INT. ...") is not counted: M16.1 approved pairs
    are ranked on the scene body, and header keywords would skew coverage
    towards neighbouring chunks.
    """
    return str(scene.get("text") or "")


def detect_candidates(
    scenes: Optional[Iterable[dict]] = None,
    chunks: Optional[Iterable[dict]] = None,
    top_k: int = 5,
    min_coverage: float = 0.05,
) -> list[LinkCandidate]:
    """Suggest-only candidates for all scenes (top ``top_k`` chunks each).

    The candidate pool is bounded by ``min_coverage`` so deterministic
    top-k selection stays meaningful; below it the scene has no plausible
    book source and no candidate is proposed (honest NO_CANDIDATE).

    Chunk bigram sets and normalized chunk texts are precomputed once, so a
    full 119×824 pass stays a few seconds.

    Ranking is deterministic: primary — bigram coverage, tie-break —
    verbatim sentence count, then chunk id (coverage first keeps the
    M16.1 approved pairs ranked as the owner resolved them, while verbatim
    quotes are surfaced as a secondary signal).
    """
    scene_list = list(scenes) if scenes is not None else load_scenes()
    chunk_list = list(chunks) if chunks is not None else load_book_chunks()
    if not chunk_list:
        return []

    chunk_texts = [str(chunk.get("text") or "") for chunk in chunk_list]
    chunk_bigram_sets = [set(_bigrams(text)) for text in chunk_texts]
    chunk_norms = [_normalized(text) for text in chunk_texts]

    candidates: list[LinkCandidate] = []
    for scene in scene_list:
        scene_id = str(scene.get("id") or "")
        if not scene_id:
            continue
        stext = _scene_text(scene)
        if not stext.strip():
            continue
        scene_bigrams = Counter(_bigrams(stext))
        scene_bigram_total = sum(scene_bigrams.values())
        scene_sentences = _sentences(stext)
        scored: list[tuple[float, int, int, int, dict]] = []
        for index, chunk in enumerate(chunk_list):
            shared = sum(count for bg, count in scene_bigrams.items() if bg in chunk_bigram_sets[index])
            coverage = shared / scene_bigram_total if scene_bigram_total else 0.0
            norm_chunk = chunk_norms[index]
            matched = sum(1 for sent in scene_sentences if _normalized(sent) in norm_chunk)
            if coverage < min_coverage and matched == 0:
                continue
            scored.append((coverage, matched, len(scene_sentences), index, chunk))
        scored.sort(key=lambda item: (-item[0], -item[1], str(item[4].get("id", ""))))
        for coverage, matched, total, index, chunk in scored[:top_k]:
            candidates.append(
                LinkCandidate(
                    screenplay_scene_id=scene_id,
                    book_chunk_id=str(chunk.get("id")),
                    coverage=coverage,
                    verbatim_sentences=matched,
                    verbatim_total=total,
                    score=coverage,
                    scene_title=str(scene.get("title") or ""),
                    chapter_title=str(chunk.get("chapter_title") or ""),
                    notes=(
                        f"Кандидат (suggest-only, M10): покрытие биграммами сцены {coverage:.0%}, "
                        f"дословных совпадений предложений {matched}/{total}; "
                        f"подтверждённой связью не является"
                    ),
                )
            )
    return candidates


def candidates_for_scene(
    scene_id: str,
    scenes: Optional[Iterable[dict]] = None,
    chunks: Optional[Iterable[dict]] = None,
    top_k: int = 5,
    min_coverage: float = 0.05,
) -> list[LinkCandidate]:
    """Suggest-only candidates for a single scene (confirmation input)."""
    scene_list = list(scenes) if scenes is not None else load_scenes()
    scene = next((s for s in scene_list if str(s.get("id") or "") == scene_id), None)
    if scene is None:
        return []
    return detect_candidates([scene], chunks, top_k=top_k, min_coverage=min_coverage)


def valid_scene_ids(path: Optional[Path] = None) -> set[str]:
    """All scene ids of the canonical synopsis document."""
    return {str(s.get("id")) for s in load_scenes(path)}
