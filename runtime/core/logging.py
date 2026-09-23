import logging
from pathlib import Path
from observability.logging import setup_logger, StructuredFormatter

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
log = setup_logger("hermes.core", log_file=str(LOG_DIR / "core.log"))

# Ensure all hermes.* sub-loggers (voice, keeper, pulse_manager, etc.) write to the same log file
_hermes_parent = logging.getLogger("hermes")
if not any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith("core.log") for h in _hermes_parent.handlers):
    log_path = LOG_DIR / "core.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _fh = logging.FileHandler(str(log_path), encoding="utf-8")
    _fh.setFormatter(StructuredFormatter())
    _hermes_parent.addHandler(_fh)
    _hermes_parent.setLevel(logging.INFO)
