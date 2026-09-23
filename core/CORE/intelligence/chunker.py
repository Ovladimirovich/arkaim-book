"""
SemanticChunker — структурный чанкинг книги по абзацам и главам.
Источник: BOOK_DOCUMENT.json (17 глав, 824 параграфа).
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

BASE = Path(__file__).resolve().parents[2]
DOC_PATH = BASE / "KNOWLEDGE" / "BOOK_DOCUMENT.json"


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
            chunks.append({
                "id": f"chunk_{p['id']}_{chunk_id}",
                "text": p["text"],
                "chapter_id": p["chapter_id"],
                "chapter_title": ch.get("title", ""),
                "chapter_number": ch.get("number", -1),
                "paragraph_id": p["id"],
                "char_start": p.get("char_start", 0),
                "char_end": p.get("char_end", 0),
                "source": "book",
            })
        return chunks

    def chunk_by_chapter(self) -> List[Dict]:
        """
        Создаёт чанки по одной главе.
        """
        chunks = []
        for ch in self.get_chapters():
            chunk_id = hashlib.md5(ch["text"].encode()).hexdigest()[:12]
            chunks.append({
                "id": f"chapter_{ch['id']}_{chunk_id}",
                "text": ch["text"],
                "chapter_id": ch["id"],
                "chapter_title": ch.get("title", ""),
                "chapter_number": ch.get("number", -1),
                "paragraph_id": "all",
                "char_start": ch.get("char_start", 0),
                "char_end": ch.get("char_end", 0),
                "source": "book",
            })
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
                chunks.append({
                    "id": f"chunk_{p['id']}_{chunk_id}",
                    "text": text,
                    "chapter_id": p["chapter_id"],
                    "chapter_title": ch.get("title", ""),
                    "chapter_number": ch.get("number", -1),
                    "paragraph_id": p["id"],
                    "char_start": p.get("char_start", 0),
                    "char_end": p.get("char_end", 0),
                    "source": "book",
                })
            else:
                # Split long paragraph into sub-chunks
                for i in range(0, len(text), max_chunk_size):
                    sub_text = text[i:i + max_chunk_size]
                    chunk_id = hashlib.md5(sub_text.encode()).hexdigest()[:12]
                    chunks.append({
                        "id": f"chunk_{p['id']}_sub{i}_{chunk_id}",
                        "text": sub_text,
                        "chapter_id": p["chapter_id"],
                        "chapter_title": ch.get("title", ""),
                        "chapter_number": ch.get("number", -1),
                        "paragraph_id": f"{p['id']}_sub{i // max_chunk_size}",
                        "char_start": p.get("char_start", 0) + i,
                        "char_end": p.get("char_start", 0) + i + len(sub_text),
                        "source": "book",
                    })

        return chunks

    def chunk_by_sliding_window(self, chunk_size: int = 400, overlap: int = 100) -> List[Dict]:
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
                window = text[i:i + chunk_size]
                if len(window) < 50:
                    continue
                chunk_id = hashlib.md5(window.encode()).hexdigest()[:12]
                chunks.append({
                    "id": f"slide_{ch['id']}_{i}_{chunk_id}",
                    "text": window,
                    "chapter_id": ch["id"],
                    "chapter_title": ch.get("title", ""),
                    "chapter_number": ch.get("number", -1),
                    "paragraph_id": f"slide_{i // (chunk_size - overlap)}",
                    "char_start": ch.get("char_start", 0) + i,
                    "char_end": ch.get("char_start", 0) + i + len(window),
                    "source": "book",
                })

        return chunks

    def get_stats(self) -> Dict:
        chapters = self.get_chapters()
        paragraphs = self.get_paragraphs()
        return {
            "total_chapters": len(chapters),
            "total_paragraphs": len(paragraphs),
            "total_chars": self._document.get("source", {}).get("total_chars", 0) if self._document else 0,
            "status": "loaded" if self._document else "no_document",
        }

class ScreenplayChunker:
    """Чанкинг киносценария по сценам (INT/EXT)."""

    def __init__(self, screenplay_path=None):
        from pathlib import Path as _P
        self._screenplay_path = screenplay_path or _P("core/SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md")
        self._text = ""
        self._scenes = []
        if self._screenplay_path.exists():
            self._text = self._screenplay_path.read_text(encoding="utf-8")
            self._scenes = self._parse_scenes()

    def _parse_scenes(self):
        import re
        if not self._text:
            return []
        lines = self._text.split("\n")
        scenes = []
        current_title = ""
        current_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^\d+\.\s+(INT|EXT)", stripped):
                if current_lines and current_title:
                    content = "\n".join(current_lines).strip()
                    if content:
                        scenes.append({
                            "title": current_title,
                            "content": content,
                            "location": self._extract_location(current_title),
                            "type": "INT" if "INT" in current_title else "EXT",
                        })
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines and current_title:
            content = "\n".join(current_lines).strip()
            if content:
                scenes.append({
                    "title": current_title,
                    "content": content,
                    "location": self._extract_location(current_title),
                    "type": "INT" if "INT" in current_title else "EXT",
                })
        return scenes

    def _extract_location(self, title):
        import re
        m = re.match(r"^\d+\.\s+(?:INT|EXT)\.\s+(.+)$", title)
        return m.group(1).strip() if m else title

    def chunk_by_scene(self):
        import hashlib
        chunks = []
        for i, scene in enumerate(self._scenes):
            chunk_id = hashlib.md5(scene["content"].encode()).hexdigest()[:12]
            chunks.append({
                "id": f"scene_{i:03d}_{chunk_id}",
                "text": scene["content"],
                "scene_id": f"scene_{i:03d}",
                "scene_title": scene["title"],
                "location": scene["location"],
                "scene_type": scene["type"],
                "char_start": 0,
                "char_end": len(scene["content"]),
                "source": "screenplay",
            })
        return chunks

    def get_stats(self):
        return {
            "total_scenes": len(self._scenes),
            "text_length": len(self._text),
            "status": "loaded" if self._text else "no_file",
        }