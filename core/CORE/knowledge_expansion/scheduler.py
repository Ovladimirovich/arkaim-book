"""
Scheduler — планировщик автоматического обогащения знаний.
"""
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.knowledge_expansion.scheduler")


class KnowledgeScheduler:
    """Планировщик автоматического обогащения знаний."""

    def __init__(self, pipeline):
        self._pipeline = pipeline
        self._last_run: dict[str, float] = {}
        self._source_hashes: dict[str, str] = {}

    async def check_and_run(self):
        """Проверить изменения и запустить обогащение."""
        for module_name, config in self._pipeline._modules.items():
            if self._has_changes(config.get("source_files", [])):
                log.info("changes_detected module=%s", module_name)
                try:
                    await self._pipeline.run_module(module_name)
                    self._last_run[module_name] = time.time()
                    log.info("module_completed module=%s", module_name)
                except Exception as e:
                    log.error("module_failed module=%s error=%s", module_name, e)

    def _has_changes(self, source_files: list) -> bool:
        """Проверить, изменились ли исходные файлы."""
        for f in source_files:
            if isinstance(f, str):
                f = Path(f)
            if not f.exists():
                continue
            current_hash = self._hash_file(f)
            prev_hash = self._source_hashes.get(str(f), "")
            if current_hash != prev_hash:
                self._source_hashes[str(f)] = current_hash
                return True
        return False

    def _hash_file(self, path: Path) -> str:
        """Хеш файла для определения изменений."""
        return hashlib.md5(path.read_bytes()).hexdigest()

    def get_status(self) -> dict:
        """Получить статус планировщика."""
        return {
            "last_run": self._last_run,
            "tracked_files": len(self._source_hashes),
        }
