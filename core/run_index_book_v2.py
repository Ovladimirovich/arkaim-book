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
    print(f"   Chunker:  {stats['chunker']['total_chapters']} глав, {stats['chunker']['total_paragraphs']} параграфов")
    print(f"   Enricher: {stats['enricher']['themes_count']} тем, {stats['enricher']['characters_count']} персонажей, {stats['enricher']['symbols_count']} символов")
    print(f"   ChromaDB: {stats['chroma']}")

    print("\n2. Очистка старой коллекции ChromaDB...")
    kernel.retriever.clear_collection()

    print("\n3. Индексация с обогащением (hybrid-mode)...")
    result = kernel.index_book(mode="hybrid")

    print(f"\n--- Результат ---")
    print(f"   Всего чанков: {result['chunks_total']}")
    print(f"   Проиндексировано: {result['chunks_indexed']}")
    print(f"   Чанков с темами: {result['enriched_themes']}")
    print(f"   Чанков с персонажами: {result['enriched_characters']}")
    print(f"   Чанков с символами: {result['enriched_symbols']}")
    print(f"   Статус: {result['status']}")

    print("\n4. Тестовый поиск...")
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
