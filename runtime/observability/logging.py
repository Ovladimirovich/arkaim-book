import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        msg = super().format(record)
        return f"{ts} {record.levelname:<5} {record.name}: {msg}"


def setup_logger(name: str, level: int = logging.INFO, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(StructuredFormatter())
        logger.addHandler(h)
    if log_file and not any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith(Path(log_file).name) for h in logger.handlers):
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(p), encoding="utf-8")
        fh.setFormatter(StructuredFormatter())
        logger.addHandler(fh)
    return logger


def log_event(logger: logging.Logger, event: str, **fields):
    """Structured log entry: event=<name> key1=val1 key2=val2 ..."""
    parts = [f"event={event}"]
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, float):
            parts.append(f"{k}={v:.2f}")
        else:
            parts.append(f"{k}={v}")
    logger.info(" ".join(parts))
