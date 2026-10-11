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


_CORE_DIR = Path(__file__).resolve().parent.parent
# Каталог на диске называется "genome"; "GENOME" — историческое написание (Windows, регистронезависимая ФС).
_GENOME_DIR = _CORE_DIR / "genome"
if not _GENOME_DIR.exists() and (_CORE_DIR / "GENOME").exists():
    _GENOME_DIR = _CORE_DIR / "GENOME"
GENOME_BACKUP_DIR = _GENOME_DIR / "history"


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
    identity_changed: bool = (
        False  # если True — перезагрузка невозможна без подтверждения
    )
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

    # ── Пути ──────────────────────────────────────

    def _relativize(self, path: Path) -> str:
        """Относительный (переносимый) путь внутри backup-каталога.

        Старые исторические записи хранят абсолютные Windows-пути —
        они остаются как есть и разрешаются через _resolve_path().
        """
        try:
            return path.relative_to(self._backup_dir).as_posix()
        except ValueError:
            return str(path)

    def _resolve_path(self, stored: str) -> Path:
        """Разрешить путь из индекса: относительный → backup-каталог, абсолютный → как есть."""
        p = Path(stored)
        if p.is_absolute():
            return p
        return self._backup_dir / p

    # ── Дедупликация ──────────────────────────────

    def _collect_layer_payloads(self, pulse) -> dict[str, str]:
        """Текущие сводки слоёв, доступных у pulse."""
        payloads: dict[str, str] = {}
        layers = getattr(pulse, "layers", None) or {}
        for name in self.IMMUTABLE_LAYERS | self.MUTABLE_LAYERS:
            layer = layers.get(name)
            if layer and hasattr(layer, "summary"):
                payloads[name] = layer.summary
        return payloads

    def _latest_snapshot(self, version: str) -> Optional[GenomeSnapshot]:
        """Последняя запись индекса для указанной версии."""
        for snap in reversed(self._history):
            if snap.version == version:
                return snap
        return None

    def _is_unchanged(
        self, snap: GenomeSnapshot, payload: str, layer_payloads: dict[str, str]
    ) -> bool:
        """Проверить, совпадает ли содержимое снапшота с текущим геномом и слоями."""
        genome_path = self._resolve_path(snap.path)
        if (
            not genome_path.exists()
            or genome_path.read_text(encoding="utf-8") != payload
        ):
            return False
        for name, text in layer_payloads.items():
            stored = snap.layer_snapshots.get(name)
            if not stored:
                return False
            layer_path = self._resolve_path(stored)
            if (
                not layer_path.exists()
                or layer_path.read_text(encoding="utf-8") != text
            ):
                return False
        return True

    def snapshot(self, genome: dict, pulse) -> GenomeSnapshot:
        """
        Сохранить снимок текущего генома.
        Каждый слой может сохранить своё состояние отдельно.

        Если геном и слои не изменились с последнего снапшота —
        файл и запись индекса НЕ создаются повторно, возвращается
        существующий снапшот.
        """
        version = genome.get("version", "unknown")
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        payload = json.dumps(genome, ensure_ascii=False, indent=2)
        layer_payloads = self._collect_layer_payloads(pulse)

        latest = self._latest_snapshot(version)
        if latest is not None and self._is_unchanged(latest, payload, layer_payloads):
            log.info("evolution_snapshot_skipped version=%s reason=unchanged", version)
            return latest

        filename = f"genome_v{version}_{timestamp[:10]}.json"
        path = self._backup_dir / filename

        # Сохранить полный геном
        path.write_text(payload, encoding="utf-8")

        layer_snapshots = {}
        for name, text in layer_payloads.items():
            ls_path = self._backup_dir / f"layer_{name}_v{version}.txt"
            ls_path.write_text(text, encoding="utf-8")
            layer_snapshots[name] = self._relativize(ls_path)

        snapshot = GenomeSnapshot(
            version=version,
            saved_at=timestamp,
            path=self._relativize(path),
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
            len(diff.new_characters)
            + len(diff.removed_characters)
            + len(diff.new_themes)
            + len(diff.new_symbols)
            + len(diff.new_world_entities)
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
                log.info(
                    "evolution_auto_visuals_created count=%d chars=%s",
                    count,
                    diff.new_characters,
                )
                created.extend(f"character_visual:{ch}" for ch in diff.new_characters)

        return created

    # ── Откат ──────────────────────────────────────

    def get_version(self, version: str) -> Optional[dict]:
        """Получить геном по версии из истории."""
        for snap in reversed(self._history):
            if snap.version == version:
                path = self._resolve_path(snap.path)
                if not path.exists():
                    # Старые абсолютные пути с другой машины → пробуем имя файла в backup-каталоге
                    fallback = self._backup_dir / Path(snap.path).name
                    if fallback.exists():
                        path = fallback
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
