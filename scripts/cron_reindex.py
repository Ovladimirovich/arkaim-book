"""
Cron-скрипт для периодической переиндексации enriched_chunks.
"""
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"))
sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cron_reindex.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s cron_reindex: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("cron_reindex")


def send_telegram_alert(text: str):
    import os
    import httpx
    import asyncio
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def _send():
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": f"⚠️ {text}", "parse_mode": "HTML"})
    try:
        asyncio.run(_send())
    except Exception as e:
        log.error("telegram_alert_failed error=%s", e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reindex enriched_chunks")
    parser.add_argument("--mode", default="hybrid", choices=["paragraph", "chapter", "hybrid", "dense"],
                        help="Chunking mode. 'dense' produces 2000+ chunks.")
    args = parser.parse_args()

    start = time.time()
    log.info("reindex_started mode=%s", args.mode)
    try:
        # Добавляем возможные пути для импорта intelligence.kernel
        alt_paths = [
            str(PROJECT_ROOT / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"),
            str(PROJECT_ROOT / "core" / "CORE"),
            str(PROJECT_ROOT),
        ]
        for p in alt_paths:
            if p not in sys.path:
                sys.path.insert(0, p)
        from intelligence.kernel import KnowledgeKernel  # type: ignore
    except Exception as e:
        log.error("import_failed error=%s", e)
        send_telegram_alert(f"Cron reindex: import failed: {e}")
        raise

    try:
        kernel = KnowledgeKernel()
        stats = kernel.get_stats()
        log.info("kernel_initialized chapters=%d", stats["chunker"]["total_chapters"])
    except Exception as e:
        log.error("kernel_init_failed error=%s", e)
        send_telegram_alert(f"Cron reindex: init failed: {e}")
        raise

    try:
        log.info("clearing_old_collection")
        try:
            kernel.retriever.clear_collection()
        except Exception:
            log.warning("clear_collection_failed continuing")

        log.info("indexing_mode mode=%s", args.mode)
        result = kernel.index_book(mode=args.mode)
        elapsed = time.time() - start
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "duration_seconds": round(elapsed, 3),
            "chunks_total": result.get("chunks_total", 0),
            "chunks_indexed": result.get("chunks_indexed", 0),
            "enriched_themes": result.get("enriched_themes", 0),
            "status": result.get("status", "unknown"),
        }
        log.info("reindex_completed result=%s", json.dumps(summary, ensure_ascii=False))
    except Exception as e:
        log.error("reindex_failed error=%s", e, exc_info=True)
        send_telegram_alert(f"Cron reindex: failed: {e}")
        raise


if __name__ == "__main__":
    main()