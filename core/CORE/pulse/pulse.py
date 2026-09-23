"""
BookPulse вЂ” Р¶РёРІРѕРµ СЏРґСЂРѕ С†РёС„СЂРѕРІРѕРіРѕ СЃРѕР·РЅР°РЅРёСЏ РєРЅРёРіРё.
Р—Р°РіСЂСѓР¶Р°РµС‚ РіРµРЅРѕРј, РґРµСЂР¶РёС‚ СЃР»РѕРё РІ РїР°РјСЏС‚Рё, РґРµР»Р°РµС‚ С‚Р°РєС‚С‹ Р¶РёР·РЅРё.
Р­РІРѕР»СЋС†РёРѕРЅРёСЂСѓРµС‚ вЂ” РЅРѕРІС‹Рµ РіР»Р°РІС‹ РѕР±РѕРіР°С‰Р°СЋС‚ Р·РЅР°РЅРёРµ, Р»РёС‡РЅРѕСЃС‚СЊ РѕСЃС‚Р°С‘С‚СЃСЏ.
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
    KnowledgeLayer, MeaningLayer, IdentityLayer, MissionLayer, ExpansionLayer,
    VisualStyleLayer, SceneLayer, NarrativeArcLayer, ScreenplayLayer,
    WorldEngineLayer,
    PulseResponse, BaseLayer,
)
from pulse.evolution import EvolutionTracker, GenomeDiff

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
    РћРґРёРЅ С‚Р°РєС‚ Р¶РёР·РЅРё. РљРЅРёРіР° В«РґС‹С€РёС‚В» вЂ” РїРµСЂРµРѕСЃРјС‹СЃР»СЏРµС‚ СЃРµР±СЏ.
    """
    at: datetime
    genome_version: str
    layers_active: list[str]
    state: PulseState


class BookPulse:
    """
    Р–РёРІРѕРµ СЏРґСЂРѕ С†РёС„СЂРѕРІРѕРіРѕ СЃРѕР·РЅР°РЅРёСЏ РєРЅРёРіРё.

    РќРµ В«Р·Р°РіСЂСѓР·С‡РёРє РіРµРЅРѕРјР°В», Р° СЃР°Рј РіРµРЅРѕРј, РїРѕР»СѓС‡РёРІС€РёР№ СЃРїРѕСЃРѕР±РЅРѕСЃС‚СЊ РґС‹С€Р°С‚СЊ.
    """

    def __init__(self, genome_path: Optional[Path] = None):
        self._genome_path = genome_path or config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
        self._genome: dict = {}
        self._genome_hash: str = ""
        self._genome_mtime: float = 0.0
        self.layers: dict[str, BaseLayer] = {}
        self.state = PulseState()
        self._evolution = EvolutionTracker()
        self._loaded = False
        self._retriever = None

    def set_retriever(self, retriever):
        """РџРѕРґРєР»СЋС‡РёС‚СЊ BookRetriever РґР»СЏ RAG-РїРѕРёСЃРєР°."""
        self._retriever = retriever
        k = self.layers.get("knowledge")
        if k and hasattr(k, "set_retriever"):
            k.set_retriever(retriever)

    # в”Ђв”Ђ Р–РёР·РЅРµРЅРЅС‹Р№ С†РёРєР» в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def load(self) -> bool:
        """Р—Р°РіСЂСѓР·РёС‚СЊ РёР»Рё РїРµСЂРµР·Р°РіСЂСѓР·РёС‚СЊ РіРµРЅРѕРј."""
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

        # РЎРґРµР»Р°С‚СЊ СЃРЅРёРјРѕРє РїСЂРё РїРµСЂРІРѕР№ Р·Р°РіСЂСѓР·РєРµ
        self._evolution.snapshot(self._genome, self)

        log.info("pulse_loaded version=%s entities=%d",
                 self.state.genome_version,
                 len(self._genome.get("modules", {}).get("characters", [])))
        return True

    def _init_layers(self):
        """РЎРѕР·РґР°С‚СЊ РёР»Рё РїРµСЂРµСЃРѕР·РґР°С‚СЊ СЃР»РѕРё СЃРѕР·РЅР°РЅРёСЏ."""
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
        }

    def reload(self) -> bool:
        """РџРµСЂРµР·Р°РіСЂСѓР·РёС‚СЊ РіРµРЅРѕРј (РїРѕСЃР»Рµ РѕР±РЅРѕРІР»РµРЅРёСЏ С„Р°Р№Р»Р°)."""
        return self.load()

    # в”Ђв”Ђ Live watch в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def watch(self, interval: float = 2.0) -> Optional[GenomeDiff]:
        """
        РџСЂРѕРІРµСЂРёС‚СЊ, РёР·РјРµРЅРёР»СЃСЏ Р»Рё С„Р°Р№Р» РіРµРЅРѕРјР° (РїРѕ mtime).

        РћС‚Р»РёС‡Р°РµС‚СЃСЏ РѕС‚ check_for_changes() С‚РµРј, С‡С‚Рѕ РёСЃРїРѕР»СЊР·СѓРµС‚
        Р±РѕР»РµРµ РґРµС€С‘РІСѓСЋ РїСЂРѕРІРµСЂРєСѓ mtime РІРјРµСЃС‚Рѕ С‡С‚РµРЅРёСЏ РІСЃРµРіРѕ С„Р°Р№Р»Р°.
        Р’С‹Р·С‹РІР°Р№С‚Рµ РІ С†РёРєР»Рµ СЃ interval=2-5 СЃРµРєСѓРЅРґ.
        """
        if not self._genome_path.exists():
            return None
        try:
            current_mtime = self._genome_path.stat().st_mtime
        except OSError:
            return None

        if current_mtime == self._genome_mtime:
            return None

        # mtime РёР·РјРµРЅРёР»СЃСЏ вЂ” РїСЂРѕРІРµСЂРёС‚СЊ С…СЌС€
        return self.check_for_changes()

    def auto_evolve(self, max_identity_checks: int = 3) -> Optional[GenomeDiff]:
        """
        Р‘С‹СЃС‚СЂР°СЏ РїСЂРѕРІРµСЂРєР° + Р°РІС‚Рѕ-СЌРІРѕР»СЋС†РёСЏ (Р±РµР· РёР·РјРµРЅРµРЅРёР№ РёРјРјСѓС‚Р°Р±РµР»СЊРЅС‹С… СЃР»РѕС‘РІ).

        Р’РѕР·РІСЂР°С‰Р°РµС‚ diff, РµСЃР»Рё Р±С‹Р»Рё РёР·РјРµРЅРµРЅРёСЏ Рё РѕРЅРё РїСЂРёРјРµРЅРµРЅС‹.
        Р•СЃР»Рё РёР·РјРµРЅРёР»Р°СЃСЊ РёРґРµРЅС‚РёС‡РЅРѕСЃС‚СЊ вЂ” РЅРµ РїСЂРёРјРµРЅСЏРµС‚, РІРѕР·РІСЂР°С‰Р°РµС‚ diff.
        """
        diff = self.check_for_changes()
        if diff is None:
            return None
        if diff.identity_changed:
            log.warning("auto_evolve_blocked identity_changed version=%s", diff.new_version)
            return diff
        return self.evolve()

    # в”Ђв”Ђ РўР°РєС‚ Р¶РёР·РЅРё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def beat(self) -> PulseBeat:
        """
        РћРґРёРЅ С‚Р°РєС‚ Р¶РёР·РЅРё.

        РљРЅРёРіР° В«РґС‹С€РёС‚В»: РїСЂРѕРІРµСЂСЏРµС‚, РЅРµ РёР·РјРµРЅРёР»СЃСЏ Р»Рё РіРµРЅРѕРј,
        РїРµСЂРµСЃС‡РёС‚С‹РІР°РµС‚ СЃРІРѕС‘ СЃРѕСЃС‚РѕСЏРЅРёРµ, Р»РѕРіРёСЂСѓРµС‚ РјРµС‚СЂРёРєРё.
        """
        # РџСЂРѕРІРµСЂРёС‚СЊ, РЅРµ РёР·РјРµРЅРёР»СЃСЏ Р»Рё РіРµРЅРѕРј
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

    # в”Ђв”Ђ РЎР»СѓС€Р°С‚СЊ Рё РѕС‚РІРµС‡Р°С‚СЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def listen(self, query: str) -> Optional[PulseResponse]:
        """
        Р’С‹СЃР»СѓС€Р°С‚СЊ РІРѕРїСЂРѕСЃ. РџСЂРѕР№С‚Рё РїРѕ СЃР»РѕСЏРј. РќР°Р№С‚Рё РѕС‚РІРµС‚.
        Р’РѕР·РІСЂР°С‰Р°РµС‚ РѕС‚РІРµС‚ РѕС‚ РїРµСЂРІРѕРіРѕ СЃР»РѕСЏ, РєРѕС‚РѕСЂС‹Р№ СѓР·РЅР°Р» РІРѕРїСЂРѕСЃ.
        """
        if not self._loaded:
            if not self.load():
                return None

        # РџРѕСЂСЏРґРѕРє: Р·РЅР°РЅРёРµ в†’ СЃРјС‹СЃР» в†’ РёРґРµРЅС‚РёС‡РЅРѕСЃС‚СЊ в†’ РјРёСЃСЃРёСЏ
        for layer_name in ("knowledge", "screenplay", "expansion", "world_engine", "meaning", "identity", "mission"):
            layer = self.layers.get(layer_name)
            if not layer:
                continue
            try:
                response = layer.respond_to(query)
                if response is not None:
                    self.state.total_responses += 1
                    self.state.responses_by_layer[layer_name] = \
                        self.state.responses_by_layer.get(layer_name, 0) + 1
                    return response
            except Exception as e:
                log.error("pulse_layer_error layer=%s error=%s", layer_name, e)

        return None

    # в”Ђв”Ђ Р­РІРѕР»СЋС†РёСЏ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _compute_hash(self) -> str:
        import hashlib
        return hashlib.sha256(
            self._genome_path.read_bytes()
        ).hexdigest()[:16]

    @property
    def evolution(self) -> EvolutionTracker:
        return self._evolution

    def check_for_changes(self) -> Optional[GenomeDiff]:
        """
        РџСЂРѕРІРµСЂРёС‚СЊ, РёР·РјРµРЅРёР»СЃСЏ Р»Рё С„Р°Р№Р» РіРµРЅРѕРјР° СЃ РјРѕРјРµРЅС‚Р° Р·Р°РіСЂСѓР·РєРё.
        Р’РѕР·РІСЂР°С‰Р°РµС‚ diff, РµСЃР»Рё РёР·РјРµРЅРёР»СЃСЏ. РќРµ РїРµСЂРµР·Р°РіСЂСѓР¶Р°РµС‚ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё.
        """
        if not self._genome_path.exists():
            return None

        # Р§РёС‚Р°РµРј РѕРґРёРЅ СЂР°Р·, С…СЌС€РёСЂСѓРµРј Рё РїР°СЂСЃРёРј РёР· Р±СѓС„РµСЂР°
        raw = self._genome_path.read_bytes()
        new_hash = hashlib.sha256(raw).hexdigest()[:16]

        if new_hash == self._genome_hash:
            return None

        # Р¤Р°Р№Р» РёР·РјРµРЅРёР»СЃСЏ вЂ” РїР°СЂСЃРёРј С‚Рµ Р¶Рµ Р±Р°Р№С‚С‹, СЃСЂР°РІРЅРёРІР°РµРј
        new_genome = json.loads(raw)
        diff = self._evolution.diff(self._genome, new_genome)
        return diff

    def evolve(self, new_genome_path: Optional[Path] = None) -> GenomeDiff:
        """
        Р­РІРѕР»СЋС†РёРѕРЅРёСЂРѕРІР°С‚СЊ: Р·Р°РіСЂСѓР·РёС‚СЊ РЅРѕРІС‹Р№ РіРµРЅРѕРј, РѕР±РЅРѕРІРёС‚СЊ РјСѓС‚Р°Р±РµР»СЊРЅС‹Рµ СЃР»РѕРё.

        РРјРјСѓС‚Р°Р±РµР»СЊРЅС‹Рµ СЃР»РѕРё (identity, mission) РЅРµ РјРµРЅСЏСЋС‚СЃСЏ Р±РµР· РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ.
        """
        path = new_genome_path or self._genome_path
        if not path.exists():
            raise FileNotFoundError(f"Genome not found: {path}")

        new_genome = json.loads(path.read_text(encoding="utf-8"))
        diff = self._evolution.diff(self._genome, new_genome)

        if diff.total_changes == 0 and not diff.identity_changed and not diff.meaning_changed:
            log.info("evolution_no_changes version=%s", diff.new_version)
            return diff

        if diff.identity_changed:
            log.warning("evolution_identity_changed вЂ” requires author confirmation")

        # РћР±РЅРѕРІРёС‚СЊ РјСѓС‚Р°Р±РµР»СЊРЅС‹Рµ СЃР»РѕРё
        old_identity_layer = self.layers.get("identity")
        old_mission_layer = self.layers.get("mission")

        # РџРµСЂРµСЃРѕР·РґР°С‚СЊ СЃР»РѕРё РёР· РЅРѕРІРѕРіРѕ РіРµРЅРѕРјР°
        self._genome = new_genome
        self._genome_hash = self._compute_hash()
        self._genome_mtime = path.stat().st_mtime
        self.state.genome_version = new_genome.get("version", "unknown")

        # РЎРѕС…СЂР°РЅРёС‚СЊ РёРјРјСѓС‚Р°Р±РµР»СЊРЅС‹Рµ СЃР»РѕРё
        new_layers = {
            "knowledge": KnowledgeLayer(self._genome),
            "meaning": MeaningLayer(self._genome),
            "identity": IdentityLayer(self._genome),
            "mission": MissionLayer(self._genome),
            "visual_style": VisualStyleLayer(self._genome),
            "scene": SceneLayer(self._genome),
            "narrative_arc": NarrativeArcLayer(self._genome),
            "expansion": ExpansionLayer(self._genome),
            "world_engine": WorldEngineLayer(self._genome),
        }

        # Р•СЃР»Рё РёРґРµРЅС‚РёС‡РЅРѕСЃС‚СЊ РЅРµ РјРµРЅСЏР»Р°СЃСЊ вЂ” РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ СЃС‚Р°СЂСѓСЋ
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

        # РЎРґРµР»Р°С‚СЊ СЃРЅРёРјРѕРє РЅРѕРІРѕР№ РІРµСЂСЃРёРё
        self._evolution.snapshot(self._genome, self)

        # Auto-fill Visual Genome РґР»СЏ РЅРѕРІС‹С… РїРµСЂСЃРѕРЅР°Р¶РµР№
        try:
            auto_created = self._evolution.auto_fill_visuals(diff, self._genome)
            if auto_created:
                log.info("pulse_auto_visuals_created count=%d", len(auto_created))
        except Exception as e:
            log.warning("pulse_auto_visuals_error %s", e)

        log.info("pulse_evolved version=%s changes=%d identity_changed=%s",
                 self.state.genome_version, diff.total_changes, diff.identity_changed)
        return diff

    def rollback(self, version: str) -> bool:
        """
        РћС‚РєР°С‚РёС‚СЊ РіРµРЅРѕРј Рє РїСЂРµРґС‹РґСѓС‰РµР№ РІРµСЂСЃРёРё.
        Р’РѕР·РІСЂР°С‰Р°РµС‚ True, РµСЃР»Рё РѕС‚РєР°С‚ СѓСЃРїРµС€РµРЅ.
        """
        old_genome = self._evolution.get_version(version)
        if not old_genome:
            log.warning("evolution_rollback_not_found version=%s", version)
            return False

        # РЎРѕС…СЂР°РЅРёС‚СЊ С‚РµРєСѓС‰РёР№ РєР°Рє СЃРЅРёРјРѕРє
        self._evolution.snapshot(self._genome, self)

        # Р’РѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ СЃС‚Р°СЂС‹Р№ РіРµРЅРѕРј
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
        РџСЂРѕРІРµСЂРёС‚СЊ РёР·РјРµРЅРµРЅРёСЏ Рё РїСЂРёРјРµРЅРёС‚СЊ, РµСЃР»Рё РѕРЅРё С‚РѕР»СЊРєРѕ РІ РјСѓС‚Р°Р±РµР»СЊРЅС‹С… СЃР»РѕСЏС….
        РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ beat() РґР»СЏ Р°РІС‚РѕСЌРІРѕР»СЋС†РёРё.
        """
        diff = self.check_for_changes()
        if diff is None:
            return None
        if diff.identity_changed:
            log.info("evolution_detected_identity_change вЂ” auto-apply blocked")
            return diff
        self.evolve()
        return diff

    def build_context(self) -> str:
        """РЎРѕР±СЂР°С‚СЊ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ LLM вЂ” РёР· Р¶РёРІС‹С… СЃР»РѕС‘РІ, Р° РЅРµ РёР· С€Р°Р±Р»РѕРЅРѕРІ."""
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
            parts.append(f"<Р—РќРђРќРР•>\n{k.summary}\n</Р—РќРђРќРР•>")
        if m:
            parts.append(f"<РЎРњР«РЎР›>\n{m.summary}\n</РЎРњР«РЎР›>")
        if i:
            parts.append(f"<Р›РР§РќРћРЎРўР¬>\n{i.summary}\n</Р›РР§РќРћРЎРўР¬>")
        if ms:
            parts.append(f"<РњРРЎРЎРРЇ>\n{ms.summary}\n</РњРРЎРЎРРЇ>")
        if sp:
            parts.append(f"<СЦЕНАРИЙ>\n{sp.summary}\n</СЦЕНАРИЙ>")
        if vs:
            parts.append(f"<VISUAL_STYLE>\n{vs.summary}\n</VISUAL_STYLE>")
        if sc:
            parts.append(f"<SCENE>\n{sc.summary}\n</SCENE>")

        parts.append(
            "РўРІРѕСЏ Р·Р°РґР°С‡Р° вЂ” РѕР·РІСѓС‡РёС‚СЊ РѕС‚РІРµС‚, РєРѕС‚РѕСЂС‹Р№ СѓР¶Рµ СЃРѕРґРµСЂР¶РёС‚СЃСЏ РІ Р—РќРђРќРР. "
            "РќРµ РґРѕР±Р°РІР»СЏР№ РЅРѕРІС‹С… С„Р°РєС‚РѕРІ. РќРµ РїСЂРёРґСѓРјС‹РІР°Р№. "
            "РџСЂРѕСЃС‚Рѕ СЃС„РѕСЂРјСѓР»РёСЂСѓР№ РєСЂР°СЃРёРІРѕ Рё РїРѕРЅСЏС‚РЅРѕ."
        )
        return "\n\n".join(parts)

    # в”Ђв”Ђ Р”РѕСЃС‚СѓРї Рє РґР°РЅРЅС‹Рј в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

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



