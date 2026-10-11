"""Тесты EvolutionTracker: дедупликация снапшотов и переносимые пути."""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

# Add CORE to path for pulse imports
_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from pulse.evolution import EvolutionTracker


class FakeLayer:
    def __init__(self, summary: str):
        self.summary = summary


def make_pulse(summaries: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(layers={k: FakeLayer(v) for k, v in summaries.items()})


DEFAULT_LAYERS = {
    "identity": "Я — книга.",
    "mission": "Показать путь.",
    "knowledge": "Факты о книге.",
    "meaning": "Замысел автора.",
}


def base_genome() -> dict:
    return {
        "version": "1.0.0",
        "modules": {"characters": [{"name": "Велик"}], "themes": [], "symbols": []},
    }


def changed_genome() -> dict:
    genome = base_genome()
    genome["modules"]["characters"].append({"name": "Странник"})
    return genome


def today() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


@pytest.fixture
def backup_dir(tmp_path) -> Path:
    return tmp_path / "history"


class TestFirstSnapshot:
    def test_creates_genome_file_and_index_entry(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        snap = tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        expected_file = backup_dir / f"genome_v1.0.0_{today()}.json"
        assert expected_file.exists()
        assert snap.version == "1.0.0"
        assert snap.path == expected_file.name

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 1
        assert index[0]["path"] == expected_file.name
        assert set(index[0]["layer_snapshots"]) == set(DEFAULT_LAYERS)

    def test_writes_layer_snapshots(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        for name in DEFAULT_LAYERS:
            layer_file = backup_dir / f"layer_{name}_v1.0.0.txt"
            assert layer_file.exists()
            assert layer_file.read_text(encoding="utf-8") == DEFAULT_LAYERS[name]


class TestRepeatWithoutChanges:
    def test_no_duplicate_index_entry(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        first = tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))
        second = tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 1
        assert second.path == first.path
        assert second.saved_at == first.saved_at

    def test_no_duplicate_genome_files(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        genome_files = list(backup_dir.glob("genome_v*.json"))
        assert len(genome_files) == 1

    def test_skips_even_after_restart(self, backup_dir):
        EvolutionTracker(backup_dir=backup_dir).snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        restarted = EvolutionTracker(backup_dir=backup_dir)
        restarted.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 1


class TestGenomeChange:
    def test_appends_new_entry(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))
        tracker.snapshot(changed_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 2

        stored = json.loads((backup_dir / index[-1]["path"]).read_text(encoding="utf-8"))
        names = {c["name"] for c in stored["modules"]["characters"]}
        assert names == {"Велик", "Странник"}

    def test_layer_change_also_creates_entry(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        new_layers = dict(DEFAULT_LAYERS, knowledge="Факты + новое знание.")
        tracker.snapshot(base_genome(), make_pulse(new_layers))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 2
        assert (backup_dir / "layer_knowledge_v1.0.0.txt").read_text(encoding="utf-8") == "Факты + новое знание."


class TestSameDayRepeat:
    def test_repeat_after_change_same_day(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))
        tracker.snapshot(changed_genome(), make_pulse(DEFAULT_LAYERS))
        tracker.snapshot(changed_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 2

    def test_multiple_distinct_changes_same_day_kept(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        second = changed_genome()
        tracker.snapshot(second, make_pulse(DEFAULT_LAYERS))

        third = changed_genome()
        third["modules"]["characters"].append({"name": "Учитель"})
        tracker.snapshot(third, make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 3


class TestPortablePaths:
    def test_new_entries_are_relative(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert not Path(index[0]["path"]).is_absolute()
        assert "\\" not in index[0]["path"]
        for stored in index[0]["layer_snapshots"].values():
            assert not Path(stored).is_absolute()
            assert "\\" not in stored

    def test_get_version_resolves_relative_paths(self, backup_dir):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        loaded = EvolutionTracker(backup_dir=backup_dir).get_version("1.0.0")
        assert loaded is not None
        assert loaded["version"] == "1.0.0"

    def test_history_survives_directory_move(self, backup_dir, tmp_path):
        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(changed_genome(), make_pulse(DEFAULT_LAYERS))

        moved = tmp_path / "relocated" / "history"
        moved.parent.mkdir(parents=True)
        shutil.copytree(backup_dir, moved)

        relocated = EvolutionTracker(backup_dir=moved)
        loaded = relocated.get_version("1.0.0")
        assert loaded is not None
        names = {c["name"] for c in loaded["modules"]["characters"]}
        assert names == {"Велик", "Странник"}


class TestLegacyHistoryPreserved:
    def _seed_legacy(self, backup_dir: Path) -> dict:
        backup_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = backup_dir / "genome_v0.9.0_2026-01-01.json"
        legacy_file.write_text(json.dumps({"version": "0.9.0"}), encoding="utf-8")
        entry = {
            "version": "0.9.0",
            "saved_at": "2026-01-01T00:00:00+00:00",
            "path": str(legacy_file),
            "layer_snapshots": {},
        }
        (backup_dir / "index.json").write_text(json.dumps([entry]), encoding="utf-8")
        return entry

    def test_old_absolute_entries_kept_untouched(self, backup_dir):
        legacy_entry = self._seed_legacy(backup_dir)

        tracker = EvolutionTracker(backup_dir=backup_dir)
        tracker.snapshot(base_genome(), make_pulse(DEFAULT_LAYERS))

        index = json.loads((backup_dir / "index.json").read_text(encoding="utf-8"))
        assert len(index) == 2
        assert index[0] == legacy_entry
        assert Path(index[0]["path"]).is_absolute()

    def test_legacy_absolute_path_still_readable(self, backup_dir):
        self._seed_legacy(backup_dir)

        tracker = EvolutionTracker(backup_dir=backup_dir)
        loaded = tracker.get_version("0.9.0")
        assert loaded == {"version": "0.9.0"}

    def test_stale_absolute_path_falls_back_to_filename(self, backup_dir):
        backup_dir.mkdir(parents=True, exist_ok=True)
        real_file = backup_dir / "genome_v0.9.0_2026-01-01.json"
        real_file.write_text(json.dumps({"version": "0.9.0"}), encoding="utf-8")
        entry = {
            "version": "0.9.0",
            "saved_at": "2026-01-01T00:00:00+00:00",
            "path": "C:\\some\\other\\machine\\genome_v0.9.0_2026-01-01.json",
            "layer_snapshots": {},
        }
        (backup_dir / "index.json").write_text(json.dumps([entry]), encoding="utf-8")

        tracker = EvolutionTracker(backup_dir=backup_dir)
        assert tracker.get_version("0.9.0") == {"version": "0.9.0"}
