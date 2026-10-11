"""Run script for genome extractor - fixes PYTHONPATH issues."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "CORE"))

from genome.extractor import main

if __name__ == "__main__":
    main()