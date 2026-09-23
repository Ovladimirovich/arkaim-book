"""
CLI для запуска Knowledge Expansion Pipeline.

Запуск:
    python -m knowledge_expansion.run --all
    python -m knowledge_expansion.run --module philosophy_deep
    python -m knowledge_expansion.run --status
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Добавляем путь к ядру
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_expansion.pipeline import create_default_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
)
log = logging.getLogger("knowledge_expansion.cli")


async def main():
    parser = argparse.ArgumentParser(description="Knowledge Expansion Pipeline")
    parser.add_argument("--all", action="store_true", help="Запустить все модули")
    parser.add_argument("--module", type=str, help="Запустить конкретный модуль")
    parser.add_argument("--status", action="store_true", help="Показать статус")
    parser.add_argument("--validate-only", action="store_true", help="Только валидация")
    args = parser.parse_args()

    pipeline = create_default_pipeline()

    if args.status:
        status = pipeline.get_status()
        print(f"Modules: {status['module_count']}")
        for name in status['modules']:
            print(f"  - {name}")
        return

    if args.all:
        print("Running all modules...")
        results = await pipeline.run_all()
        print("\nResults:")
        for name, result in results.items():
            status = "OK" if result.success else "FAIL"
            print(f"  {name}: {status} (saved={result.items_saved}, skipped={result.items_skipped})")

    elif args.module:
        print(f"Running module: {args.module}")
        result = await pipeline.run_module(args.module)
        status = "OK" if result.success else "FAIL"
        print(f"Result: {status} (saved={result.items_saved}, skipped={result.items_skipped})")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
