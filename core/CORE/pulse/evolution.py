"""
Evolution — книга растёт, не теряя себя.

Геном версионируется. Слои делятся на мутабельные (знание, смысл)
и иммутабельные (идентичность, миссия). При обновлении генома
Pulse видит разницу, обновляет что можно, сохраняет что нельзя.

Visual Genome hook: при появлении новых персонажей
автоматически создаются archetype-визуалы.
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from visualization.archetype_visuals import fill_missing_archetype_visuals

log = logging.getLogger("hermes.pulse.evolution")


GENOME_BACKUP_DIR = Path(__file__).resolve().parent.parent / "GENOME" / "history"


@dataclass
class GenomeDiff:
    """Разница между двумя версиями генома."""
    old_version: str = ""
    new_version: str = ""
    new_characters: list[str] = field(default_factory=list)
    removed_characters: list[str] = field(default_factory=list)
    new_themes: list[str] = field(default_factory=list)
    new_symbols: list[str] = field(default_factory=list)
    new_world_entities: list[str] = field(default_factory=list)
    total_changes: int = 0
    identity_changed: bool = False       # если True — перезагрузка невозможна без подтверждения
    meaning_changed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GenomeSnapshot:
    """Снимок генома на момент времени."""
    version: str
    saved_at: str
    path: str
    layer_snapshots: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EvolutionTracker:
    """
    Следит за эволюцией книги.

    Хранит историю геномов. Умеет сравнивать версии.
    Знает, какие слои можно обновлять автоматически,
    а какие требуют подтверждения автора.
    """

    IMMUTABLE_LAYERS = {"identity", "mission"}
    MUTABLE_LAYERS = {"knowledge", "meaning"}

    def __init__(self, backup_dir: Optional[Path] = None):
        self._backup_dir = backup_dir or GENOME_BACKUP_DIR
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._history: list[GenomeSnapshot] = []
        self._load_history()

    # ── История ────────────────────────────────────

    def _load_history(self):
        """Загрузить историю из файлов."""
        idx_path = self._backup_dir / "index.json"
        if idx_path.exists():
            try:
                data = json.loads(idx_path.read_text(encoding="utf-8"))
                self._history = [GenomeSnapshot(**s) for s in data]
            except Exception as e:
                log.warning("evolution_history_load_error %s", e)

    def _save_history(self):
        idx_path = self._backup_dir / "index.json"
        data = [s.to_dict() for s in self._history]
        idx_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def snapshot(self, genome: dict, pulse) -> GenomeSnapshot:
        """
        Сохранить снимок текущего генома.
        Каждый слой может сохранить своё состояние отдельно.
        """
        version = genome.get("version", "unknown")
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        filename = f"genome_v{version}_{timestamp[:10]}.json"
        path = self._backup_dir / filename

        # Сохранить полный геном
        path.write_text(
            json.dumps(genome, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        layer_snapshots = {}
        for name in self.IMMUTABLE_LAYERS | self.MUTABLE_LAYERS:
            layer = pulse.layers.get(name)
            if layer and hasattr(layer, "summary"):
                ls_path = self._backup_dir / f"layer_{name}_v{version}.txt"
                ls_path.write_text(layer.summary, encoding="utf-8")
                layer_snapshots[name] = str(ls_path)

        snapshot = GenomeSnapshot(
            version=version,
            saved_at=timestamp,
            path=str(path),
            layer_snapshots=layer_snapshots,
        )
        self._history.append(snapshot)
        self._save_history()
        log.info("evolution_snapshot_created version=%s path=%s", version, filename)
        return snapshot

    # ── Сравнение ──────────────────────────────────

    def diff(self, old_genome: dict, new_genome: dict) -> GenomeDiff:
        """
        Сравнить старый и новый геном.

        Возвращает, что изменилось, и затрагивает ли это
        иммутабельные слои.
        """
        diff = GenomeDiff(
            old_version=old_genome.get("version", "unknown"),
            new_version=new_genome.get("version", "unknown"),
        )

        old_modules = old_genome.get("modules", {})
        new_modules = new_genome.get("modules", {})

        # Персонажи
        old_chars = {c["name"] for c in old_modules.get("characters", [])}
        new_chars = {c["name"] for c in new_modules.get("characters", [])}
        diff.new_characters = list(new_chars - old_chars)
        diff.removed_characters = list(old_chars - new_chars)

        # Темы
        old_themes = {t["name"] for t in old_modules.get("themes", [])}
        new_themes = {t["name"] for t in new_modules.get("themes", [])}
        diff.new_themes = list(new_themes - old_themes)

        # Символы
        old_symbols = {s["name"] for s in old_modules.get("symbols", [])}
        new_symbols = {s["name"] for s in new_modules.get("symbols", [])}
        diff.new_symbols = list(new_symbols - old_symbols)

        # Сущности мира
        old_we = {w["name"] for w in old_genome.get("world_entities", [])}
        new_we = {w["name"] for w in new_genome.get("world_entities", [])}
        diff.new_world_entities = list(new_we - old_we)

        diff.total_changes = (
            len(diff.new_characters) + len(diff.removed_characters) +
            len(diff.new_themes) + len(diff.new_symbols) +
            len(diff.new_world_entities)
        )

        # Проверить, изменилась ли идентичность
        old_identity = old_genome.get("identity_layer", "")
        new_identity = new_genome.get("identity_layer", "")
        if old_identity and new_identity and old_identity != new_identity:
            diff.identity_changed = True

        # Проверить, изменился ли смысл
        old_ai = old_genome.get("author_intent", {})
        new_ai = new_genome.get("author_intent", {})
        if old_ai.get("main_message") != new_ai.get("main_message"):
            diff.meaning_changed = True

        return diff

    # ── Visual Auto-fill ─────────────────────────

    def auto_fill_visuals(self, diff: GenomeDiff, genome: dict) -> list[str]:
        """
        Авто-заполнение Visual Genome при изменениях в геноме.

        При появлении новых персонажей — создаёт archetype-визуалы.
        Возвращает список созданных visual_id.
        """
        if not diff.new_characters and not diff.new_world_entities:
            return []

        created = []
        if diff.new_characters:
            count = fill_missing_archetype_visuals(genome)
            if count:
                log.info("evolution_auto_visuals_created count=%d chars=%s",
                         count, diff.new_characters)
                created.extend(f"character_visual:{ch}" for ch in diff.new_characters)

        return created

    # ── Откат ──────────────────────────────────────

    def get_version(self, version: str) -> Optional[dict]:
        """Получить геном по версии из истории."""
        for snap in reversed(self._history):
            if snap.version == version:
                path = Path(snap.path)
                if path.exists():
                    return json.loads(path.read_text(encoding="utf-8"))
        return None

    def list_versions(self) -> list[GenomeSnapshot]:
        """Список всех сохранённых версий."""
        return sorted(self._history, key=lambda s: s.saved_at, reverse=True)

    # ── Статистика ─────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "total_snapshots": len(self._history),
            "last_version": self._history[-1].version if self._history else "none",
            "last_saved_at": self._history[-1].saved_at if self._history else "",
            "immutable_layers": list(self.IMMUTABLE_LAYERS),
            "mutable_layers": list(self.MUTABLE_LAYERS),
        }
