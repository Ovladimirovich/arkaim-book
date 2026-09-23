"""Add runtime/ to path for integration tests."""
import sys
from pathlib import Path

_runtime = str(Path(__file__).resolve().parent.parent.parent)
if _runtime not in sys.path:
    sys.path.insert(0, _runtime)
