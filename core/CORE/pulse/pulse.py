"""
BookPulse — живое ядро цифрового сознания книги.
Загружает геном, держит слои в памяти, делает такты жизни.
Эволюционирует — новые главы обогащают знание, личность остаётся.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import config
from pulse.layers import (
    KnowledgeLayer,
    MeaningLayer,
    IdentityLayer,
    MissionLayer,
    ExpansionLayer,
    VisualStyleLayer,
    SceneLayer,
    NarrativeArcLayer,
    ScreenplayLayer,
    WorldEngineLayer,
    PulseResponse,
    BaseLayer,
)
from pulse.evolution import EvolutionTracker, GenomeDiff
from pulse.layers_world_engine import WorldEngineLayerV2

log = logging.getLogger("hermes.pulse")


@dataclass
class PulseState:
    genome_version: str = ""
    loaded_at: Optional[datetime] = None
    total_responses: int = 0
    responses_by_layer: dict[str, int] = field(default_factory=dict)
    beats_count: int = 0


@dataclass
class PulseBeat:
    """
    Один такт жизни. Книга «дышит» — переосмысляет себя.
    """

    at: datetime
    genome_version: str
    layers_active: list[str]
    state: PulseState


class BookPulse:
    """
    Живое ядро цифрового сознания книги.

    Не «загрузчик генома», а сам геном, получивший способность дышать.
    """

    def __init__(self, genome_path: Optional[Path] = None):
        self._genome_path = (
            genome_path or config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
        )
        self._genome: dict = {}
        self._genome_hash: str = ""
        self._genome_mtime: float = 0.0
        self.layers: dict[str, BaseLayer] = {}
        self.state = PulseState()
        self._evolution = EvolutionTracker()
        self._loaded = False
        self._retriever = None

    def set_retriever(self, retriever):
        """Подключить BookRetriever для RAG-поиска."""
        self._retriever = retriever
        k = self.layers.get("knowledge")
        if k and hasattr(k, "set_retriever"):
            k.set_retriever(retriever)

    # ── Жизненный цикл ──────────────────────────────

    def load(self) -> bool:
        """Загрузить или перезагрузить геном."""
        if not self._genome_path.exists():
            log.warning("pulse_genome_not_found path=%s", self._genome_path)
            return False

        self._genome = json.loads(self._genome_path.read_text(encoding="utf-8"))
        self._genome_hash = self._compute_hash()
        self._genome_mtime = self._genome_path.stat().st_mtime
        self._init_layers()
        self.state.loaded_at = datetime.now(tz=timezone.utc)
        self.state.genome_version = self._genome.get("version", "unknown")
        self._loaded = True

        # Сделать снимок при первой загрузке
        self._evolution.snapshot(self._genome, self)

        log.info(
            "pulse_loaded version=%s entities=%d",
            self.state.genome_version,
            len(self._genome.get("modules", {}).get("characters", [])),
        )
        return True

    def _init_layers(self):
        """Создать или пересоздать слои сознания."""
        self.layers = {
            "knowledge": KnowledgeLayer(self._genome, retriever=self._retriever),
            "meaning": MeaningLayer(self._genome),
            "identity": IdentityLayer(self._genome),
            "mission": MissionLayer(self._genome),
            "visual_style": VisualStyleLayer(self._genome),
            "scene": SceneLayer(self._genome),
            "narrative_arc": NarrativeArcLayer(self._genome),
            "expansion": ExpansionLayer(self._genome),
            "screenplay": ScreenplayLayer(self._genome),
            "world_engine": WorldEngineLayer(self._genome),
            "world_engine_v2": WorldEngineLayerV2(self._genome),
        }

    def reload(self) -> bool:
        """Перезагрузить геном (после обновления файла)."""
        return self.load()

    # ── Live watch ───────────────────────────────────

    def watch(self, interval: float = 2.0) -> Optional[GenomeDiff]:
        """
        Проверить, изменился ли файл генома (по mtime).

        Отличается от check_for_changes() тем, что использует
        более дешёвую проверку mtime вместо чтения всего файла.
        Вызывайте в цикле с interval=2-5 секунд.
        """
        if not self._genome_path.exists():
            return None
        try:
            current_mtime = self._genome_path.stat().st_mtime
        except OSError:
            return None

        if current_mtime == self._genome_mtime:
            return None

        # mtime изменился — проверить хэш
        return self.check_for_changes()

    def auto_evolve(self, max_identity_checks: int = 3) -> Optional[GenomeDiff]:
        """
        Быстрая проверка + авто-эволюция (без изменений иммутабельных слоёв).

        Возвращает diff, если были изменения и они применены.
        Если изменилась идентичность — не применяет, возвращает diff.
        """
        diff = self.check_for_changes()
        if diff is None:
            return None
        if diff.identity_changed:
            log.warning(
                "auto_evolve_blocked identity_changed version=%s", diff.new_version
            )
            return diff
        return self.evolve()

    # ── Такт жизни ──────────────────────────────────

    def beat(self) -> PulseBeat:
        """
        Один такт жизни.

        Книга «дышит»: проверяет, не изменился ли геном,
        пересчитывает своё состояние, логирует метрики.
        """
        # Проверить, не изменился ли геном
        try:
            self.reload_if_changed()
        except Exception as e:
            log.error("pulse_beat_evolution_error %s", e)

        self.state.beats_count += 1
        return PulseBeat(
            at=datetime.now(tz=timezone.utc),
            genome_version=self.state.genome_version,
            layers_active=list(self.layers.keys()),
            state=self.state,
        )

    # ── Слушать и отвечать ─────────────────────────

    def listen(self, query: str) -> Optional[PulseResponse]:
        """
        Выслушать вопрос. Пройти по слоям. Найти ответ.
        Возвращает ответ от первого слоя, который узнал вопрос.
        """
        if not self._loaded:
            if not self.load():
                return None

        # Порядок: знание → смысл → идентичность → миссия
        for layer_name in (
            "knowledge",
            "screenplay",
            "expansion",
            "world_engine",
            "meaning",
            "identity",
            "mission",
        ):
            layer = self.layers.get(layer_name)
            if not layer:
                continue
            try:
                response = layer.respond_to(query)
                if response is not None:
                    self.state.total_responses += 1
                    self.state.responses_by_layer[layer_name] = (
                        self.state.responses_by_layer.get(layer_name, 0) + 1
                    )
                    return response
            except Exception as e:
                log.error("pulse_layer_error layer=%s error=%s", layer_name, e)

        return None

    # ── Эволюция ───────────────────────────────────

    def _compute_hash(self) -> str:
        import hashlib

        return hashlib.sha256(self._genome_path.read_bytes()).hexdigest()[:16]

    @property
    def evolution(self) -> EvolutionTracker:
        return self._evolution

    def check_for_changes(self) -> Optional[GenomeDiff]:
        """
        Проверить, изменился ли файл генома с момента загрузки.
        Возвращает diff, если изменился. Не перезагружает автоматически.
        """
        if not self._genome_path.exists():
            return None

        # Читаем один раз, хэшируем и парсим из буфера
        raw = self._genome_path.read_bytes()
        new_hash = hashlib.sha256(raw).hexdigest()[:16]

        if new_hash == self._genome_hash:
            return None

        # Файл изменился — парсим те же байты, сравниваем
        new_genome = json.loads(raw)
        diff = self._evolution.diff(self._genome, new_genome)
        return diff

    def evolve(self, new_genome_path: Optional[Path] = None) -> GenomeDiff:
        """
        Эволюционировать: загрузить новый геном, обновить мутабельные слои.

        Иммутабельные слои (identity, mission) не меняются без подтверждения.
        """
        path = new_genome_path or self._genome_path
        if not path.exists():
            raise FileNotFoundError(f"Genome not found: {path}")

        new_genome = json.loads(path.read_text(encoding="utf-8"))
        diff = self._evolution.diff(self._genome, new_genome)

        if (
            diff.total_changes == 0
            and not diff.identity_changed
            and not diff.meaning_changed
        ):
            log.info("evolution_no_changes version=%s", diff.new_version)
            return diff

        if diff.identity_changed:
            log.warning("evolution_identity_changed — requires author confirmation")

        # Обновить мутабельные слои
        old_identity_layer = self.layers.get("identity")
        old_mission_layer = self.layers.get("mission")

        # Пересоздать слои из нового генома
        self._genome = new_genome
        self._genome_hash = self._compute_hash()
        self._genome_mtime = path.stat().st_mtime
        self.state.genome_version = new_genome.get("version", "unknown")

        # Сохранить иммутабельные слои
        new_layers = {
            "knowledge": KnowledgeLayer(self._genome, retriever=self._retriever),
            "meaning": MeaningLayer(self._genome),
            "identity": IdentityLayer(self._genome),
            "mission": MissionLayer(self._genome),
            "visual_style": VisualStyleLayer(self._genome),
            "scene": SceneLayer(self._genome),
            "narrative_arc": NarrativeArcLayer(self._genome),
            "expansion": ExpansionLayer(self._genome),
            "screenplay": ScreenplayLayer(self._genome),
            "world_engine": WorldEngineLayer(self._genome),
        }

        # Если идентичность не менялась — восстановить старую
        if not diff.identity_changed and old_identity_layer:
            new_layers["identity"] = old_identity_layer
            new_layers["identity"].load(self._genome)
        if not diff.meaning_changed and old_mission_layer:
            new_layers["mission"] = old_mission_layer
            new_layers["mission"].load(self._genome)
        new_layers["visual_style"] = VisualStyleLayer(self._genome)
        new_layers["scene"] = SceneLayer(self._genome)

        self.layers = new_layers
        self._loaded = True

        # Сделать снимок новой версии
        self._evolution.snapshot(self._genome, self)

        # Auto-fill Visual Genome для новых персонажей
        try:
            auto_created = self._evolution.auto_fill_visuals(diff, self._genome)
            if auto_created:
                log.info("pulse_auto_visuals_created count=%d", len(auto_created))
        except Exception as e:
            log.warning("pulse_auto_visuals_error %s", e)

        log.info(
            "pulse_evolved version=%s changes=%d identity_changed=%s",
            self.state.genome_version,
            diff.total_changes,
            diff.identity_changed,
        )
        return diff

    def rollback(self, version: str) -> bool:
        """
        Откатить геном к предыдущей версии.
        Возвращает True, если откат успешен.
        """
        old_genome = self._evolution.get_version(version)
        if not old_genome:
            log.warning("evolution_rollback_not_found version=%s", version)
            return False

        # Сохранить текущий как снимок
        self._evolution.snapshot(self._genome, self)

        # Восстановить старый геном
        self._genome_path.write_text(
            json.dumps(old_genome, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._genome = old_genome
        self._genome_hash = self._compute_hash()
        self._genome_mtime = self._genome_path.stat().st_mtime
        self._init_layers()
        self.state.genome_version = old_genome.get("version", "unknown")

        log.info("pulse_rollback version=%s", version)
        return True

    def reload_if_changed(self) -> Optional[GenomeDiff]:
        """
        Проверить изменения и применить, если они только в мутабельных слоях.
        Используется в beat() для автоэволюции.
        """
        diff = self.check_for_changes()
        if diff is None:
            return None
        if diff.identity_changed:
            log.info("evolution_detected_identity_change — auto-apply blocked")
            return diff
        self.evolve()
        return diff

    def build_context(self) -> str:
        """Собрать контекст для LLM — из живых слоёв, а не из шаблонов."""
        if not self._loaded:
            return ""

        k = self.layers.get("knowledge")
        m = self.layers.get("meaning")
        i = self.layers.get("identity")
        ms = self.layers.get("mission")
        vs = self.layers.get("visual_style")
        sc = self.layers.get("scene")
        sp = self.layers.get("screenplay")

        parts = []
        if k:
            parts.append(f"<ЗНАНИЕ>\n{k.summary}\n</ЗНАНИЕ>")
        if m:
            parts.append(f"<СМЫСЛ>\n{m.summary}\n</СМЫСЛ>")
        if i:
            parts.append(f"<ЛИЧНОСТЬ>\n{i.summary}\n</ЛИЧНОСТЬ>")
        if ms:
            parts.append(f"<МИССИЯ>\n{ms.summary}\n</МИССИЯ>")
        if sp:
            parts.append(f"<СЦЕНАРИЙ>\n{sp.summary}\n</СЦЕНАРИЙ>")
        if vs:
            parts.append(f"<VISUAL_STYLE>\n{vs.summary}\n</VISUAL_STYLE>")
        if sc:
            parts.append(f"<SCENE>\n{sc.summary}\n</SCENE>")

        parts.append(
            "Твоя задача — озвучить ответ, который уже содержится в ЗНАНИИ. "
            "Не добавляй новых фактов. Не придумывай. "
            "Просто сформулируй красиво и понятно."
        )
        return "\n\n".join(parts)

    # ── Доступ к данным ─────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def genome(self) -> dict:
        return self._genome

    def get_character(self, name: str) -> Optional[dict]:
        for ch in self._genome.get("modules", {}).get("characters", []):
            if ch["name"].lower() == name.lower():
                return ch
            for alias in ch.get("aliases", []):
                if alias.lower() == name.lower():
                    return ch
        return None

    def get_theme(self, name: str) -> Optional[dict]:
        for th in self._genome.get("modules", {}).get("themes", []):
            if th["name"].lower() == name.lower():
                return th
        return None
