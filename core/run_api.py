"""
Entry point for Book Intelligence API — DEPRECATED.

Book Intelligence теперь интегрирован в Core Runtime (порт 8642).
Этот файл оставлен для обратной совместимости.

Для полного запуска (рекомендуется):
  cd runtime && python -m core.main  (порт 8642, book routes + providers + X-Ray + LLM gateway)

Для standalone (только book routes, без X-Ray и provider chain):
  python run_api.py  (порт 9090) — УСТАРЕЛО
"""
import sys
import logging
import warnings
from pathlib import Path

warnings.warn(
    "run_api.py устарел. Используйте 'cd runtime && python -m core.main' (порт 8642).",
    DeprecationWarning,
    stacklevel=2,
)

sys.path.insert(0, str(Path(__file__).parent / "CORE"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "runtime"))

from fastapi import FastAPI
from core.book_routes import router as book_router

LOG_DIR = Path(__file__).resolve().parent.parent / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("book_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(str(LOG_DIR / "book_api.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s book_api: %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s book_api: %(message)s"))
    logger.addHandler(sh)

logger.info("book_api_starting port=9090 (DEPRECATED standalone mode)")

app = FastAPI(title="Arkaim Book Intelligence (DEPRECATED standalone)")
app.include_router(book_router)

if __name__ == "__main__":
    import uvicorn
    logger.warning("Запуск в DEPRECATED standalone режиме. Рекомендуется: cd runtime && python -m core.main")
    uvicorn.run(app, host="127.0.0.1", port=9090, log_level="info")
