"""CLI-интерфейс для BOOK OS.

Использование:
    python -m book_os.cli search "Велик" [--n 5] [--provenance source]
    python -m book_os.cli ingest file.md
    python -m book_os.cli stats
    python -m book_os.cli entity "Велик"
    python -m book_os.cli resolve "Влад"
    python -m book_os.cli facts entity_id
    python -m book_os.cli index chunks.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from book_os.provider import BookOSProvider


_provider: Optional[BookOSProvider] = None


def _get_provider(data_dir: Optional[Path] = None) -> BookOSProvider:
    global _provider
    if _provider is None:
        _provider = BookOSProvider(data_dir=data_dir)
    return _provider


def cmd_search(args):
    provider = _get_provider(args.data_dir)
    results = provider.search_chunks(
        query=args.query,
        entity_ids=args.entity_ids,
        provenance=args.provenance,
        doc_ids=args.doc_ids,
        n_results=args.n,
    )
    if not results:
        print("No results.")
        return
    for i, r in enumerate(results, 1):
        score = r.metadata.get("_score", "?") if r.metadata else "?"
        print(f"\n--- Result {i} (score={score}) ---")
        print(f"  doc: {r.doc_id}")
        print(f"  text: {r.text[:200]}...")
        if r.metadata:
            meta = {k: v for k, v in r.metadata.items() if not k.startswith("_")}
            if meta:
                print(f"  meta: {json.dumps(meta, ensure_ascii=False, default=str)[:200]}")


def cmd_ingest(args):
    provider = _get_provider(args.data_dir)
    path = Path(args.path)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    result = provider.ingest_document(str(path))
    print(f"Ingested: {json.dumps(result, ensure_ascii=False, indent=2, default=str)}")


def cmd_stats(args):
    provider = _get_provider(args.data_dir)
    stats = provider.get_stats()
    for key, val in stats.items():
        if isinstance(val, dict):
            print(f"\n{key}:")
            for k, v in val.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {val}")


def cmd_entity(args):
    provider = _get_provider(args.data_dir)
    entity = provider.get_entity(args.name)
    if entity is None:
        print(f"Entity not found: {args.name}")
        sys.exit(1)
    print(json.dumps(entity.model_dump(), ensure_ascii=False, indent=2, default=str))


def cmd_resolve(args):
    provider = _get_provider(args.data_dir)
    try:
        resolved = provider.resolve_name(args.name)
        print(f"{args.name} -> {resolved}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_facts(args):
    provider = _get_provider(args.data_dir)
    facts = provider.get_facts(args.entity_id, provenance=args.provenance)
    if not facts:
        print("No facts.")
        return
    for f in facts:
        print(f"  [{f.provenance}] {f.statement[:150]}...")


def cmd_index(args):
    provider = _get_provider(args.data_dir)
    path = Path(args.path)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        chunks = data
    elif isinstance(data, dict) and "chunks" in data:
        chunks = data["chunks"]
    else:
        print("JSON must be an array of chunks or {chunks: [...]}")
        sys.exit(1)
    from schemas.chunk import Chunk
    models = []
    for item in chunks:
        models.append(Chunk(
            id=item.get("id", ""),
            doc_id=item.get("doc_id", ""),
            text=item.get("text", ""),
            position=item.get("position", 0),
            metadata=item.get("metadata", {}),
        ))
    count = provider.index_engine.index_chunks(models, provenance=args.provenance)
    print(f"Indexed {count} chunks.")


def main():
    parser = argparse.ArgumentParser(description="BOOK OS CLI")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Data directory (default: OS_DATA/)")

    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Поиск по тексту")
    p_search.add_argument("query", help="Поисковый запрос")
    p_search.add_argument("-n", type=int, default=5, help="Количество результатов")
    p_search.add_argument("--entity-ids", nargs="*", default=None)
    p_search.add_argument("--provenance", default=None)
    p_search.add_argument("--doc-ids", nargs="*", default=None)

    p_ingest = sub.add_parser("ingest", help="Загрузить документ")
    p_ingest.add_argument("path", help="Путь к файлу")

    sub.add_parser("stats", help="Статистика")

    p_entity = sub.add_parser("entity", help="Информация о сущности")
    p_entity.add_argument("name", help="Имя сущности")

    p_resolve = sub.add_parser("resolve", help="Привести имя к канонической форме")
    p_resolve.add_argument("name", help="Имя или алиас")

    p_facts = sub.add_parser("facts", help="Факты о сущности")
    p_facts.add_argument("entity_id", help="ID сущности")
    p_facts.add_argument("--provenance", default=None)

    p_cross = sub.add_parser("cross-search", help="Поиск по нескольким документам")
    p_cross.add_argument("query", help="Поисковый запрос")
    p_cross.add_argument("-n", type=int, default=20, help="Количество результатов")
    p_cross.add_argument("--doc-ids", nargs="*", default=None)

    p_cross_summary = sub.add_parser("cross-summary", help="Сводка поиска по документам")
    p_cross_summary.add_argument("query", help="Поисковый запрос")
    p_cross_summary.add_argument("--doc-ids", nargs="*", default=None)

    p_index = sub.add_parser("index", help="Индексация чанков из JSON")
    p_index.add_argument("path", help="Путь к JSON-файлу")
    p_index.add_argument("--provenance", default="source")

    args = parser.parse_args()

    if args.command == "cross-search":
        provider = _get_provider(args.data_dir)
        result = provider.cross_document_search(args.query, doc_ids=args.doc_ids, n_results=args.n)
        print(f"Query: {result['query']}")
        print(f"Documents matched: {result['documents_matched']}, Total chunks: {result['total_chunks']}")
        for doc_id, doc_summary in result.get("doc_summaries", {}).items():
            print(f"\n--- {doc_id} (chunks: {doc_summary['chunks_found']}, max_score: {doc_summary['max_score']:.3f}) ---")
            for chunk in result["results"].get(doc_id, [])[:2]:
                print(f"  [{chunk['score']:.3f}] {chunk['text'][:150]}...")
    elif args.command == "cross-summary":
        provider = _get_provider(args.data_dir)
        summary = provider.cross_search_summary(args.query, doc_ids=args.doc_ids)
        print(f"Query: {summary['query']}")
        print(f"Chunks found: {summary['total_chunks']}, Documents: {summary['documents_matched']}")
        for doc in summary.get("documents", []):
            print(f"  {doc['title'] or doc['doc_id']}: {doc['chunks_found']} chunks")
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "entity":
        cmd_entity(args)
    elif args.command == "resolve":
        cmd_resolve(args)
    elif args.command == "facts":
        cmd_facts(args)
    elif args.command == "index":
        cmd_index(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
