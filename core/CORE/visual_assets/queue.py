"""Background Generation Queue — фоновая генерация ассетов."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .schemas import VisualAsset, AssetType, AssetStatus
from .pipeline import AssetGenerationPipeline

log = logging.getLogger("visual_assets.queue")


class GenerationQueue:
    """Очередь фоновой генерации ассетов с воркерами."""

    def __init__(self, pipeline: AssetGenerationPipeline, max_concurrent: int = 2):
        self._pipeline = pipeline
        self._max_concurrent = max_concurrent
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._results: dict[str, VisualAsset] = {}
        self._running = False

    async def start_workers(self):
        """Запустить воркеров."""
        if self._running:
            return
        self._running = True
        for i in range(self._max_concurrent):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        log.info("generation_queue started workers=%d", self._max_concurrent)

    async def stop_workers(self):
        """Остановить воркеров."""
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()
        log.info("generation_queue stopped")

    async def enqueue(
        self,
        chapter: int,
        scene_id: str,
        asset_type: AssetType = AssetType.IMAGE,
        overrides: dict | None = None,
    ) -> str:
        """Добавить задачу в очередь, вернуть task_id."""
        task_id = f"task_{int(time.time())}_{chapter}_{scene_id}"
        self._queue.put_nowait({
            "task_id": task_id,
            "chapter": chapter,
            "scene_id": scene_id,
            "asset_type": asset_type,
            "overrides": overrides or {},
        })
        log.info("queued task=%s type=%s", task_id, asset_type.value)
        return task_id

    async def enqueue_batch(
        self,
        chapter: int | None = None,
        asset_type: AssetType = AssetType.IMAGE,
        limit: int = 20,
    ) -> list[str]:
        """Пакетная постановка в очередь."""
        task_ids = []
        scenes = self._pipeline._scene_engine.get_scenes_by_chapter(chapter) if chapter else []
        if not chapter:
            for ch in range(1, 20):
                ch_scenes = self._pipeline._scene_engine.get_scenes_by_chapter(ch)
                if not ch_scenes:
                    break
                scenes.extend(ch_scenes)

        for scene in scenes[:limit]:
            task_id = await self.enqueue(
                chapter=scene["chapter"],
                scene_id=scene["scene_id"],
                asset_type=asset_type,
            )
            task_ids.append(task_id)
        return task_ids

    def get_status(self, task_id: str) -> dict:
        """Получить статус задачи."""
        if task_id in self._results:
            asset = self._results[task_id]
            return {
                "task_id": task_id,
                "status": asset.status.value,
                "asset_id": asset.asset_id,
                "error": asset.error,
            }
        return {"task_id": task_id, "status": "queued"}

    def get_queue_stats(self) -> dict:
        """Статистика очереди."""
        return {
            "queue_size": self._queue.qsize(),
            "workers_running": len([w for w in self._workers if not w.done()]),
            "results_count": len(self._results),
            "running": self._running,
        }

    async def _worker_loop(self, worker_id: int):
        """Цикл воркера."""
        log.info("worker_%d started", worker_id)
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            task_id = task["task_id"]
            log.info("worker_%d processing task=%s", worker_id, task_id)

            try:
                if task["asset_type"] == AssetType.IMAGE:
                    asset = await self._pipeline.generate_image(
                        chapter=task["chapter"],
                        scene_id=task["scene_id"],
                        overrides=task["overrides"],
                    )
                else:
                    asset = await self._pipeline.generate_video(
                        chapter=task["chapter"],
                        scene_id=task["scene_id"],
                        overrides=task["overrides"],
                    )
                self._results[task_id] = asset
                log.info("worker_%d completed task=%s asset=%s", worker_id, task_id, asset.asset_id)
            except Exception as e:
                log.error("worker_%d failed task=%s error=%s", worker_id, task_id, e)
                from .storage import generate_asset_id
                failed = VisualAsset(
                    asset_id=generate_asset_id(),
                    asset_type=task["asset_type"],
                    chapter=task["chapter"],
                    scene_id=task["scene_id"],
                    status=AssetStatus.FAILED,
                    error=str(e),
                )
                self._results[task_id] = failed

        log.info("worker_%d stopped", worker_id)
