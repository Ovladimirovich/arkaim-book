"""
SemanticChunker — структурный чанкинг книги по абзацам и главам.
Источник: BOOK_DOCUMENT.json (17 глав, 824 параграфа).
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(__file__).resolve().parents[2]
DOC_PATH = BASE / "KNOWLEDGE" / "BOOK_DOCUMENT.json"


# ── Правила разбора заголовков сценария ──────────────────────────────────────
# ВНИМАНИЕ: синхронизировано с runtime/core/routes/book.py
# (_SCENE_HEADER_RE / _UNNUMBERED_SCENE_HEADER_RE и т.д.). Правила обязаны
# совпадать, чтобы индексируемая структура не расходилась со списком сцен в UI.
_SCENE_MARKERS = r"(?:INT|EXT|ВНУТРЕННИЙ|НАРУЖНЫЙ|ВНЕШНИЙ|ИНТ|ЭКСТ|MONTAGE|МОНТАЖ)"
_SCENE_HEADER_RE = re.compile(rf"^\s*\d+(?:\.\s*|\s+){_SCENE_MARKERS}\b", re.IGNORECASE)
_UNNUMBERED_SCENE_HEADER_RE = re.compile(rf"^\s*{_SCENE_MARKERS}\.\s+[А-ЯЁA-Z]{{2,}}")
_NUMBER_ONLY_RE = re.compile(r"^\s*\d+\.\s*$")
_MARKER_ONLY_RE = re.compile(rf"^\s*{_SCENE_MARKERS}\.", re.IGNORECASE)
_SCENE_HEADER_PREFIX_RE = re.compile(
    rf"^\s*(?:\d+\s*\.?\s*)?{_SCENE_MARKERS}\.?\s*(.*)$", re.IGNORECASE
)


def _merge_split_scene_headers(lines: List[str]) -> List[str]:
    """Склеить разорванные заголовки («88.» + «EXT.ДОЛИНА…») в одну строку (копия для разбора)."""
    merged: List[str] = []
    i = 0
    while i < len(lines):
        if _NUMBER_ONLY_RE.match(lines[i].strip()) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if _MARKER_ONLY_RE.match(nxt):
                merged.append(f"{lines[i].strip()} {nxt}")
                i += 2
                continue
        merged.append(lines[i])
        i += 1
    return merged


def _is_screenplay_scene_header(stripped: str) -> bool:
    return bool(
        _SCENE_HEADER_RE.match(stripped) or _UNNUMBERED_SCENE_HEADER_RE.match(stripped)
    )


def _screenplay_location(title: str) -> str:
    m = _SCENE_HEADER_PREFIX_RE.match(title)
    location = m.group(1).strip() if m else ""
    return location or title


def _screenplay_scene_type(title: str) -> str:
    """Тип сцены по маркеру: INT / EXT / MONTAGE (латиница и русские синонимы).

    INT/EXT имеют приоритет: «77.EXT. ПРОСТРАНСТВО - МОНТАЖ» — это EXT-сцена,
    а MONTAGE возвращается только для блоков без явного INT/EXT («42. МОНТАЖ …»).
    """
    t = title.upper()
    if re.search(r"ВНУТРЕННИЙ|INT|ИНТ", t):
        return "INT"
    if re.search(r"НАРУЖНЫЙ|ВНЕШНИЙ|ЭКСТ|EXT", t):
        return "EXT"
    if re.search(r"MONTAGE|МОНТАЖ", t):
        return "MONTAGE"
    return "EXT"


class SemanticChunker:
    def __init__(self, doc_path: Optional[Path] = None):
        self.doc_path = doc_path or DOC_PATH
        self._document = None
        self._load_document()

    def _load_document(self):
        if self.doc_path.exists():
            self._document = json.loads(self.doc_path.read_text(encoding="utf-8"))

    def get_chapters(self) -> List[Dict]:
        if not self._document:
            return []
        return self._document.get("content", {}).get("chapters", [])

    def get_paragraphs(self) -> List[Dict]:
        if not self._document:
            return []
        return self._document.get("content", {}).get("paragraphs", [])

    def chunk_by_paragraph(self) -> List[Dict]:
        """
        Создаёт чанки по одному абзацу из BOOK_DOCUMENT.
        Каждый чанк содержит:
          - id: уникальный идентификатор
          - text: текст абзаца
          - chapter_id: какая глава
          - chapter_title: заголовок главы
          - paragraph_id: номер абзаца
          - char_start/char_end: позиции в исходном тексте
        """
        paragraphs = self.get_paragraphs()
        chapters_map = {ch["id"]: ch for ch in self.get_chapters()}

        chunks = []
        for p in paragraphs:
            ch = chapters_map.get(p["chapter_id"], {})
            chunk_id = hashlib.md5(p["text"].encode()).hexdigest()[:12]
            chunks.append(
                {
                    "id": f"chunk_{p['id']}_{chunk_id}",
                    "text": p["text"],
                    "chapter_id": p["chapter_id"],
                    "chapter_title": ch.get("title", ""),
                    "chapter_number": ch.get("number", -1),
                    "paragraph_id": p["id"],
                    "char_start": p.get("char_start", 0),
                    "char_end": p.get("char_end", 0),
                    "source": "book",
                }
            )
        return chunks

    def chunk_by_chapter(self) -> List[Dict]:
        """
        Создаёт чанки по одной главе.
        """
        chunks = []
        for ch in self.get_chapters():
            chunk_id = hashlib.md5(ch["text"].encode()).hexdigest()[:12]
            chunks.append(
                {
                    "id": f"chapter_{ch['id']}_{chunk_id}",
                    "text": ch["text"],
                    "chapter_id": ch["id"],
                    "chapter_title": ch.get("title", ""),
                    "chapter_number": ch.get("number", -1),
                    "paragraph_id": "all",
                    "char_start": ch.get("char_start", 0),
                    "char_end": ch.get("char_end", 0),
                    "source": "book",
                }
            )
        return chunks

    def chunk_hybrid(self) -> List[Dict]:
        """
        Гибридный чанкинг:
        - Каждый абзац — отдельный чанк (для точного поиска)
        + Каждая глава целиком — отдельный чанк (для контекста)
        """
        return self.chunk_by_paragraph() + self.chunk_by_chapter()

    def chunk_by_subparagraph(self, max_chunk_size: int = 500) -> List[Dict]:
        """
        Разбивает длинные абзацы на подчанки для увеличения индекса.
        Абзацы короче max_chunk_size остаются как есть.
        """
        paragraphs = self.get_paragraphs()
        chapters_map = {ch["id"]: ch for ch in self.get_chapters()}

        chunks = []
        for p in paragraphs:
            text = p["text"]
            ch = chapters_map.get(p["chapter_id"], {})

            if len(text) <= max_chunk_size:
                chunk_id = hashlib.md5(text.encode()).hexdigest()[:12]
                chunks.append(
                    {
                        "id": f"chunk_{p['id']}_{chunk_id}",
                        "text": text,
                        "chapter_id": p["chapter_id"],
                        "chapter_title": ch.get("title", ""),
                        "chapter_number": ch.get("number", -1),
                        "paragraph_id": p["id"],
                        "char_start": p.get("char_start", 0),
                        "char_end": p.get("char_end", 0),
                        "source": "book",
                    }
                )
            else:
                # Split long paragraph into sub-chunks
                for i in range(0, len(text), max_chunk_size):
                    sub_text = text[i : i + max_chunk_size]
                    chunk_id = hashlib.md5(sub_text.encode()).hexdigest()[:12]
                    chunks.append(
                        {
                            "id": f"chunk_{p['id']}_sub{i}_{chunk_id}",
                            "text": sub_text,
                            "chapter_id": p["chapter_id"],
                            "chapter_title": ch.get("title", ""),
                            "chapter_number": ch.get("number", -1),
                            "paragraph_id": f"{p['id']}_sub{i // max_chunk_size}",
                            "char_start": p.get("char_start", 0) + i,
                            "char_end": p.get("char_start", 0) + i + len(sub_text),
                            "source": "book",
                        }
                    )

        return chunks

    def chunk_by_sliding_window(
        self, chunk_size: int = 400, overlap: int = 100
    ) -> List[Dict]:
        """
        Скользящее окно по главам для максимального покрытия.
        Создаёт перекрывающиеся чанки для улучшения поиска.
        """
        chapters = self.get_chapters()
        chunks = []

        for ch in chapters:
            text = ch.get("text", "")
            if not text:
                continue

            for i in range(0, len(text), chunk_size - overlap):
                window = text[i : i + chunk_size]
                if len(window) < 50:
                    continue
                chunk_id = hashlib.md5(window.encode()).hexdigest()[:12]
                chunks.append(
                    {
                        "id": f"slide_{ch['id']}_{i}_{chunk_id}",
                        "text": window,
                        "chapter_id": ch["id"],
                        "chapter_title": ch.get("title", ""),
                        "chapter_number": ch.get("number", -1),
                        "paragraph_id": f"slide_{i // (chunk_size - overlap)}",
                        "char_start": ch.get("char_start", 0) + i,
                        "char_end": ch.get("char_start", 0) + i + len(window),
                        "source": "book",
                    }
                )

        return chunks

    def get_stats(self) -> Dict:
        chapters = self.get_chapters()
        paragraphs = self.get_paragraphs()
        return {
            "total_chapters": len(chapters),
            "total_paragraphs": len(paragraphs),
            "total_chars": self._document.get("source", {}).get("total_chars", 0)
            if self._document
            else 0,
            "status": "loaded" if self._document else "no_document",
        }


class ScreenplayChunker:
    """Чанкинг киносценария по сценам (INT/EXT)."""

    def __init__(self, screenplay_path=None):
        # Путь не зависит от текущей папки: CI запускает переиндексацию из core/,
        # cron — из корня репозитория, а файл обязан находиться одинаково везде.
        self._screenplay_path = screenplay_path or (
            BASE / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
        )
        self._text = ""
        self._scenes = []
        if self._screenplay_path.exists():
            self._text = self._screenplay_path.read_text(encoding="utf-8")
            self._scenes = self._parse_scenes()

    def _parse_scenes(self):
        if not self._text:
            return []
        lines = _merge_split_scene_headers(self._text.split("\n"))
        scenes = []
        current_title = ""
        current_lines = []
        for line in lines:
            stripped = line.strip()
            if _is_screenplay_scene_header(stripped):
                if current_lines and current_title:
                    content = "\n".join(current_lines).strip()
                    if content:
                        scenes.append(self._make_scene(current_title, content))
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines and current_title:
            content = "\n".join(current_lines).strip()
            if content:
                scenes.append(self._make_scene(current_title, content))
        return scenes

    @staticmethod
    def _make_scene(title: str, content: str) -> Dict:
        return {
            "title": title,
            "content": content,
            "location": _screenplay_location(title),
            "type": _screenplay_scene_type(title),
        }

    def _extract_location(self, title):
        return _screenplay_location(title)

    def chunk_by_scene(self):
        import hashlib

        chunks = []
        for i, scene in enumerate(self._scenes):
            chunk_id = hashlib.md5(scene["content"].encode()).hexdigest()[:12]
            chunks.append(
                {
                    "id": f"scene_{i:03d}_{chunk_id}",
                    "text": scene["content"],
                    "scene_id": f"scene_{i:03d}",
                    "scene_title": scene["title"],
                    "location": scene["location"],
                    "scene_type": scene["type"],
                    "char_start": 0,
                    "char_end": len(scene["content"]),
                    "source": "screenplay",
                }
            )
        return chunks

    def get_stats(self):
        return {
            "total_scenes": len(self._scenes),
            "text_length": len(self._text),
            "status": "loaded" if self._text else "no_file",
        }
