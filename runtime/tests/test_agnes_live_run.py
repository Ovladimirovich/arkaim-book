"""OWNER-GO 2026-10-14: ОДИН сквозной контрольный запуск генерации изображения через Agnes.

Существующая цепочка (второй механизм генерации НЕ создаётся):
  задание Arkaim: POST /book/visualize → MediaPlan (prompt)
    → MediaClient (runtime/core/media_client.py)
    → POST /v1/generate (arkaim-media, preferred_backend="agnes")
    → ComfyUIProvider + workflows/agnes_image.json (AgnesImage → SaveImage)
    → байты → AssetStorage (save_file + save: scene_id + происхождение задания)
    → открытие сохранённого результата: GET /book/assets/{asset_id}/file.

Pre-conditions (GO п.5/п.7) — иначе SKIP (как в live-тестах M4.4):
  - arkaim-media (MEDIA_BACKEND_URL, :8200) и ComfyUI (COMFYUI_URL, :8188) запущены;
  - очередь ComfyUI пуста (ровно один контрольный прогон);
  - нода AgnesImage установлена;
  - шаблон содержит ТОЛЬКО AgnesImage+SaveImage — платные узлы (MagicHour и пр.)
    отсутствуют; бэкенд выбирается ЯВНО preferred_backend="agnes".
    Платность Agnes: пакет ComfyUI-Agnes-AI (apihub.agnes-ai.com) — бесплатный
    image-API по README пакета; успешные прогоны 2026-10-14 прошли без списаний.
  - Доказательство нового прогона (п.5): в /history ComfyUI есть выполненный
    AgnesImage с prompt ЭТОЙ задачи и сохранённым output (не старый PNG).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_agnes_live_run.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MEDIA_URL = os.getenv("MEDIA_BACKEND_URL", "http://127.0.0.1:8200").rstrip("/")
COMFY_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
AGNES_WF_PATH = REPO_ROOT.parent / "arkaim-media" / "workflows" / "agnes_image.json"

TASK = {"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"}
ALLOWED_NODES = {"AgnesImage", "SaveImage"}


@pytest.fixture(scope="module")
def services_ready() -> bool:
    with httpx.Client(timeout=5) as c:
        try:
            if c.get(f"{MEDIA_URL}/health").status_code != 200:
                pytest.skip(f"arkaim-media ({MEDIA_URL}) не запущен — live-прогон пропущен")
        except httpx.HTTPError:
            pytest.skip(f"arkaim-media ({MEDIA_URL}) не отвечает — live-прогон пропущен")
        try:
            if c.get(f"{COMFY_URL}/system_stats").status_code != 200:
                pytest.skip(f"ComfyUI ({COMFY_URL}) не запущен — live-прогон пропущен")
        except httpx.HTTPError:
            pytest.skip(f"ComfyUI ({COMFY_URL}) не отвечает — live-прогон пропущен")

        queue = c.get(f"{COMFY_URL}/queue")
        if queue.status_code == 200:
            q = queue.json()
            if q.get("queue_running") or q.get("queue_pending"):
                pytest.skip("очередь ComfyUI не пуста — контрольный прогон отложен")

        try:
            node_info = c.get(f"{COMFY_URL}/object_info/AgnesImage")
            if node_info.status_code != 200 or "AgnesImage" not in node_info.json():
                pytest.skip("нода AgnesImage не установлена в ComfyUI")
        except httpx.HTTPError:
            pytest.skip("object_info/AgnesImage недоступен")

    # GO п.7: в шаблоне только бесплатные узлы Agnes — платные исполнители исключены.
    wf = json.loads(AGNES_WF_PATH.read_text("utf-8"))
    class_types = {n.get("class_type") for n in wf.values() if isinstance(n, dict)}
    assert class_types <= ALLOWED_NODES, f"потенциально платные узлы в шаблоне: {class_types - ALLOWED_NODES}"
    return True


@pytest.mark.live
def test_agnes_end_to_end(services_ready: bool):
    from core.main import app
    from core.media_client import MediaClient
    from fastapi.testclient import TestClient
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import AssetStorage, generate_asset_id

    client = TestClient(app)  # conftest подменяет auth для всех тестов

    # 1. Существующее задание Arkaim → MediaPlan (без генерации).
    resp = client.post("/book/visualize", json=TASK)
    assert resp.status_code == 200, resp.text
    plan = resp.json()["media_plan"]
    prompt = plan.get("prompt") or plan.get("structured_prompt") or ""
    assert prompt, "задание не содержит prompt"

    # 2. Сквозной вызов: MediaClient → arkaim-media → ComfyUIProvider(agnes).
    data = asyncio.run(MediaClient().generate(prompt, size="1024x1024", preferred_backend="agnes"))
    assert data[:4] == b"\x89PNG", f"результат не PNG: {data[:16]!r}"
    assert len(data) > 50_000, f"подозрительно малый файл: {len(data)} байт"

    # 3. Сохранение через AssetStorage: идентификатор сцены + происхождение задания.
    store = AssetStorage()
    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.IMAGE,
        chapter=TASK["chapter"],
        scene_id=TASK["scene_id"],
        title=f"agnes control run /book/visualize {plan.get('plan_id', '')}".strip(),
        intent=plan.get("intent", "key_frame"),
        style=plan.get("visual_style", "cinematic_fantasy"),
        status=AssetStatus.COMPLETED,
        prompt_used=prompt,
        generation=GenerationParams(
            provider="agnes",
            model="agnes-image-2.5-flash",
            size="1024x1024",
        ),
    )
    rel_path = store.save_file(asset.asset_id, AssetType.IMAGE, data)
    asset.file_path = rel_path
    asyncio.run(store.save(asset))

    # 4. Открыть сохранённый результат существующим роутом хранения.
    opened = client.get(f"/book/assets/{asset.asset_id}/file")
    assert opened.status_code == 200, opened.text
    assert opened.content[:4] == b"\x89PNG"
    assert len(opened.content) == len(data), "открытый файл ≠ сгенерированному"

    reloaded = asyncio.run(store.get(asset.asset_id))
    assert reloaded is not None and reloaded.status == AssetStatus.COMPLETED
    assert reloaded.scene_id == TASK["scene_id"]
    assert reloaded.generation.provider == "agnes"
    file_path = store.get_file_path(reloaded)
    assert file_path is not None and file_path.exists()

    # 5. Доказательство нового прогона (п.5): в /history ComfyUI есть
    #    выполненный AgnesImage с prompt ЭТОЙ задачи и сохранённым output.
    with httpx.Client(timeout=10) as c:
        history = c.get(f"{COMFY_URL}/history")
    assert history.status_code == 200

    def _entry_graph(entry) -> dict | None:
        submitted = entry.get("prompt")
        if isinstance(submitted, dict):
            return submitted
        if isinstance(submitted, list):
            for item in submitted:
                if isinstance(item, dict) and any(isinstance(v, dict) and v.get("class_type") == "AgnesImage" for v in item.values()):
                    return item
        return None

    matched = False
    for entry in history.json().values():
        graph = _entry_graph(entry)
        if not graph:
            continue
        is_ours = any(
            isinstance(node, dict) and node.get("class_type") == "AgnesImage" and node.get("inputs", {}).get("prompt") == prompt for node in graph.values()
        )
        has_output = any(out.get("images") for out in entry.get("outputs", {}).values())
        if is_ours and has_output:
            matched = True
            break
    assert matched, "в /history нет прогона с prompt этой задачи — результат не подтверждён"

    print(f"[agnes-e2e] DONE asset_id={asset.asset_id} file={file_path} bytes={len(data)} plan_id={plan.get('plan_id', '')}")
