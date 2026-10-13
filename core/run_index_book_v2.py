"""
Скрипт переиндексации книги — версия 2.
Использует KnowledgeKernel (semantic chunking + genome enrichment).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "CORE"))

from intelligence.kernel import KnowledgeKernel


def main():
    print("=" * 60)
    print("KnowledgeKernel — Index Book v2")
    print("=" * 60)

    print("\n1. Инициализация KnowledgeKernel...")
    kernel = KnowledgeKernel()
    stats = kernel.get_stats()
    print(
        f"   Chunker:  {stats['chunker']['total_chapters']} глав, {stats['chunker']['total_paragraphs']} параграфов"
    )
    print(
        f"   Enricher: {stats['enricher']['themes_count']} тем, {stats['enricher']['characters_count']} персонажей, {stats['enricher']['symbols_count']} символов"
    )
    print(f"   ChromaDB: {stats['chroma']}")

    print("\n2. Полная переиндексация: очистка → книга (hybrid-mode) → сценарий...")
    result = kernel.reindex_full(mode="hybrid")
    book = result["book"]
    screenplay = result["screenplay"]

    print("\n--- Книга ---")
    print(f"   Всего чанков: {book['chunks_total']}")
    print(f"   Проиндексировано: {book['chunks_indexed']}")
    print(f"   Чанков с темами: {book['enriched_themes']}")
    print(f"   Чанков с персонажами: {book['enriched_characters']}")
    print(f"   Чанков с символами: {book['enriched_symbols']}")
    print(f"   Статус: {book['status']}")

    print("\n--- Сценарий ---")
    print(f"   Сцен: {screenplay['scenes']}")
    print(f"   В индексе: {screenplay['indexed']}")
    print(f"   Статус: {screenplay['status']}")
    print(f"   ChromaDB: {result['chroma']}")

    print("\n3. Тестовый поиск...")
    test_queries = ["Гиперборея", "Архат", "Кали Юга", "Велик", "Аркаим"]
    for q in test_queries:
        results = kernel.search(q, n_results=2)
        print(f"\n   Запрос: «{q}»")
        for r in results:
            themes = ",".join(r.get("themes", [])[:3])
            print(f"     [{r['score']:.2f}] {r['text'][:80]}...")
            if themes:
                print(f"           темы: {themes}")

    print("\n" + "=" * 60)
    print("Индексация завершена!")
    print("=" * 60)


if __name__ == "__main__":
    main()
