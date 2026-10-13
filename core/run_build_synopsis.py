"""Штатный генератор производных структур сценария.

Строит KNOWLEDGE/SYNOPSIS_DOCUMENT.json и KNOWLEDGE/SYNOPSIS_PROFILE.json
из исходного киносценария через единый ScreenplayChunker.

Запуск:
    python core/run_build_synopsis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "CORE"))

from intelligence.synopsis_builder import generate


def main():
    print("=" * 60)
    print("SynopsisBuilder — генерация производных структур сценария")
    print("=" * 60)
    result = generate()
    print(f"  Сцен:      {result['scenes']}")
    print(f"  Абзацев:   {result['paragraphs']}")
    for path in result["files"]:
        print(f"  Записан:   {path}")
    print("Готово!")


if __name__ == "__main__":
    main()
