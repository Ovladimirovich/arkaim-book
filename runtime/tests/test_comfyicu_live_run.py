"""OWNER-GO 2026-10-14 (п.8): единственный живой тестовый запуск ComfyICU — LTX 2.5 I2V.

Сквозной путь (по образцу test_agnes_live_run.py):
  POST /book/studio-describe (SceneContext → Video MediaPlan, intent=video_clip)
  → MediaClient.generate_video(preferred_backend="comfyicu")
  → arkaim-media ComfyICUProvider (upload кадра → runs → poll → MP4)
  → AssetStorage.save_file(AssetType.VIDEO) + save (scene_id + provenance)
  → GET /book/assets/{id}/file → 200 video/mp4
  → доказательство прогона: GET /api/v1/workflows/{wid}/runs (номер, статус,
    run_time → оценка расхода кредитов для отчёта COST).

Pre-conditions (GO п.8 — иначе SKIP, без реального вызова):
  - COMFYICU_LIVE=1 (явное разрешение владельца/оператора на платный прогон);
  - arkaim-media запущен и env (COMFYICU_API_KEY/WORKFLOW_ID/INPUT_IMAGE) заданы;
  - до запуска подтверждён free-баланс (см. отчёт): runs=0, billing=null.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_comfyicu_live_run.py -v -s
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
ICU_URL = os.getenv("COMFYICU_URL", "https://comfy.icu").rstrip("/")

TASK = {"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"}

# Стоимость единого теста (контроль п.8): H100 ≈ 32 cr/s; duration 5s ≈ 46s
# вычислений → ~1470 cr < 5000 free-кредитов нового аккаунта.
TEST_DURATION_S = 5.0
TEST_FPS = 24
TEST_SIZE = "1024x576"  # шаблонная 16:9 (ResolutionSelector шаблона)


@pytest.fixture(scope="module")
def services_ready() -> bool:
    if os.getenv("COMFYICU_LIVE") != "1":
        pytest.skip("COMFYICU_LIVE!=1 — платный прогон ComfyICU не разрешён (GO п.8)")

    missing = [k for k in ("COMFYICU_API_KEY", "COMFYICU_WORKFLOW_ID", "COMFYICU_INPUT_IMAGE") if not os.getenv(k)]
    if missing:
        pytest.skip(f"env не заданы: {', '.join(missing)} — live-прогон пропущен")

    if not Path(os.environ["COMFYICU_INPUT_IMAGE"]).exists():
        pytest.skip("COMFYICU_INPUT_IMAGE не найден на диске")

    with httpx.Client(timeout=5) as c:
        try:
            if c.get(f"{MEDIA_URL}/health").status_code != 200:
                pytest.skip(f"arkaim-media ({MEDIA_URL}) не запущен — live-прогон пропущен")
        except httpx.HTTPError:
            pytest.skip(f"arkaim-media ({MEDIA_URL}) не отвечает — live-прогон пропущен")

    # Шаблон в arkaim-media на месте (провайдер откажется до расходов).
    tpl = REPO_ROOT.parent / "arkaim-media" / "workflows" / "comfyicu_ltx25_i2v.json"
    if not tpl.exists():
        pytest.skip(f"нет шаблона workflow: {tpl}")
    return True


def _icu_headers() -> dict:
    return {"authorization": f"Bearer {os.environ['COMFYICU_API_KEY']}", "user-agent": "arkaim-live-test/0.1"}


@pytest.mark.live
def test_comfyicu_end_to_end(services_ready: bool):
    from core.main import app
    from core.media_client import MediaClient
    from fastapi.testclient import TestClient
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import AssetStorage, generate_asset_id

    client = TestClient(app)  # conftest подменяет auth для всех тестов

    # 0. Runs ДО запуска (GO п.8): предыдущие попытки-валидации допустимы;
    #    после теста ожидается РОВНО ОДИН новый прогон (см. шаг 5).
    with httpx.Client(timeout=15) as c:
        runs_before = c.get(f"{ICU_URL}/api/v1/workflows/{os.environ['COMFYICU_WORKFLOW_ID']}/runs", headers=_icu_headers())
    assert runs_before.status_code == 200, runs_before.text
    runs_before_count = len(runs_before.json())

    # 1. Существующая сцена Arkaim → Video MediaPlan (штатный производственный вход).
    resp = client.post("/book/studio-describe", json=TASK)
    assert resp.status_code == 200, resp.text
    plan = resp.json()["video_description"]
    assert plan["media_kind"] == "video"
    prompt = plan.get("prompt") or plan.get("structured_prompt") or ""
    assert prompt, "video MediaPlan без prompt"
    scene_id = plan.get("source_refs", {}).get("scene_id") or TASK["scene_id"]

    # 2. Сквозной вызов: MediaClient → arkaim-media → ComfyICUProvider → MP4.
    #    duration фиксируется 5с — единый и контролируемый по стоимости прогон.
    #    timeout клиента больше суммы run (~50с) + медленного скачивания output
    #    с r2.comfy.icu (~1-2 КБ/с на канал; Range-сборка провайдера, до ~30 мин).
    data = asyncio.run(MediaClient(timeout=1900.0).generate_video(prompt, duration=TEST_DURATION_S, size=TEST_SIZE, fps=TEST_FPS, preferred_backend="comfyicu"))
    assert data[:3] == b"\x00\x00\x00" and data[4:8] == b"ftyp", f"результат не MP4: {data[:16]!r}"
    assert len(data) > 100_000, f"подозрительно малый MP4: {len(data)} байт"

    # 3. Сохранение через AssetStorage: сцена + происхождение задания + провайдер.
    store = AssetStorage()
    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=TASK["chapter"],
        scene_id=scene_id,
        title=f"comfyicu ltx2.5 i2v /book/studio-describe {plan.get('plan_id', '')}".strip(),
        intent=plan.get("intent", "video_clip"),
        style=plan.get("visual_style", "cinematic_fantasy"),
        status=AssetStatus.COMPLETED,
        prompt_used=prompt,
        duration_sec=TEST_DURATION_S,
        fps=TEST_FPS,
        generation=GenerationParams(
            provider="comfyicu",
            model="ltx-2.5-i2v",
            size=TEST_SIZE,
        ),
    )
    rel_path = store.save_file(asset.asset_id, AssetType.VIDEO, data)
    asset.file_path = rel_path
    asyncio.run(store.save(asset))

    # 4. Чтение существующим роутом хранения (штатный API, GO п.6).
    opened = client.get(f"/book/assets/{asset.asset_id}/file")
    assert opened.status_code == 200, opened.text
    assert opened.headers["content-type"].startswith("video/mp4"), opened.headers["content-type"]
    assert opened.content == data, "открытый файл ≠ сгенерированному"

    reloaded = asyncio.run(store.get(asset.asset_id))
    assert reloaded is not None and reloaded.status == AssetStatus.COMPLETED
    assert reloaded.asset_type == AssetType.VIDEO
    assert reloaded.scene_id == scene_id
    assert reloaded.generation.provider == "comfyicu"
    file_path = store.get_file_path(reloaded)
    assert file_path is not None and file_path.exists() and file_path.suffix == ".mp4"

    # 5. Доказательство нового прогона + COST (п.8/п.9): ровно ОДИН новый run,
    #    статус COMPLETED, run_time → оценка расхода кредитов.
    with httpx.Client(timeout=20) as c:
        runs_after = c.get(f"{ICU_URL}/api/v1/workflows/{os.environ['COMFYICU_WORKFLOW_ID']}/runs", headers=_icu_headers())
    assert runs_after.status_code == 200, runs_after.text
    runs = runs_after.json()
    assert len(runs) == runs_before_count + 1, f"ожидался +1 прогон, всего {len(runs)} (было {runs_before_count}): {runs_after.text[:400]}"
    run = runs[0]
    assert run.get("status") == "COMPLETED", json.dumps(run, ensure_ascii=False)[:400]

    run_time_ms = run.get("run_time") or run.get("duration_ms") or 0
    cost_cr = round((run_time_ms / 1000) * 32, 1)  # H100 = 32 cr/s (pricing)
    print(
        f"[comfyicu-e2e] DONE asset_id={asset.asset_id} file={file_path} bytes={len(data)} "
        f"plan_id={plan.get('plan_id', '')} run_id={run.get('id')} run_time={run_time_ms}ms "
        f"~cost={cost_cr}cr(~${round(cost_cr / 10000, 3)}) of 5000 free"
    )
