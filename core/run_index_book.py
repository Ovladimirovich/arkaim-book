"""Скрипт индексации книги и сценария в ChromaDB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "CORE"))

from intelligence.chunker import ScreenplayChunker
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

    # Индексируем сценарий по сценам.
    # Разбор заголовков делегируется ScreenplayChunker — единый источник правил
    # (синхронизирован с API-парсером в runtime/core/routes/book.py).
    screenplay_path = Path(__file__).parent / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
    if screenplay_path.exists():
        scenes = ScreenplayChunker(screenplay_path=screenplay_path).chunk_by_scene()
        print(f"[Index] Screenplay loaded: {len(scenes)} scenes")
        # Индексируем каждую сцену (id и метаданные согласованы с
        # KnowledgeKernel.index_screenplay)
        for scene in scenes:
            retriever.index_chunk(
                chunk_id=scene["id"],
                text=scene["text"],
                metadata={
                    "source": "screenplay",
                    "type": "screenplay",
                    "title": scene["scene_title"],
                    "scene_id": scene["scene_id"],
                    "location": scene["location"],
                    "scene_type": scene["scene_type"],
                },
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
