"""Скрипт индексации книги и сценария в ChromaDB."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "CORE"))

from intelligence.retriever import BookRetriever


def main():
    retriever = BookRetriever()

    # Индексируем книгу
    book_path = Path(__file__).parent / "SOURCE_OF_TRUTH" / "BOOK" / "КНИГА.md"
    if book_path.exists():
        text = book_path.read_text(encoding="utf-8")
        print(f"[Index] Book loaded: {len(text)} chars")
        retriever.index_text(text, metadata={"source": "КНИГА.md", "type": "book"})
    else:
        print(f"[Index] WARNING: Book file not found at {book_path}")

    # Индексируем сценарий по сценам
    screenplay_path = Path(__file__).parent / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
    if screenplay_path.exists():
        sp_text = screenplay_path.read_text(encoding="utf-8")
        print(f"[Index] Screenplay loaded: {len(sp_text)} chars")
        # Разбиваем по сценам (N. INT/EXT)
        scenes = []
        lines = sp_text.split("\n")
        current_title = ""
        current_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^\d+\.\s+(INT|EXT)", stripped):
                if current_lines and current_title:
                    content = "\n".join(current_lines).strip()
                    if content:
                        scenes.append({"title": current_title, "text": content})
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines and current_title:
            content = "\n".join(current_lines).strip()
            if content:
                scenes.append({"title": current_title, "text": content})

        # Индексируем каждую сцену
        for i, scene in enumerate(scenes):
            doc_id = f"screenplay_{i:03d}"
            retriever.index_chunk(
                chunk_id=doc_id,
                text=scene["text"],
                metadata={"source": "screenplay", "type": "screenplay", "title": scene["title"], "scene_index": i},
            )
        print(f"[Index] Screenplay indexed: {len(scenes)} scenes")
    else:
        print(f"[Index] WARNING: Screenplay not found at {screenplay_path}")

    # Статистика
    stats = retriever.get_collection_stats()
    print(f"[Index] Collection stats: {stats}")
    print("[Index] Done!")


if __name__ == "__main__":
    main()