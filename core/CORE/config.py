"""Config re-export from project core/config.py"""
from pathlib import Path
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "_project_config",
    str(Path(__file__).resolve().parent.parent / 'config.py')
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
config = _mod.config
