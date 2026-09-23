"""FutureExtrapolator — экстраполяция будущего от Аркаима.

M8: генерирует сценарии будущего на основе временной цепочки.
НЕ создаёт новые узлы в temporal graph. Read-only operation.
Использует CompatibilityChecker для фильтрации несовместимых сценариев.
"""

from __future__ import annotations

import logging
from typing import Optional

from narrative_engine.compatibility_checker import CompatibilityChecker
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.temporal.chain import TemporalChain, ChainDirection
from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.future_extrapolator")


class FutureExtrapolator:
    """Экстраполяция возможных вариантов будущего от Аркаима.

    Алгоритм:
    1. Строит FORWARD chain от arkaim_era через TemporalReconstructionEngine
    2. Извлекает паттерны из цепочки (последние узлы = направления развития)
    3. Генерирует сценарии из паттернов (детерминированно, без LLM)
    4. Фильтрует через CompatibilityChecker (6 осей)
    5. Возвращает ранжированный список будущих сценариев
    """

    # Эпохи-направления из FORWARD chain для генерации сценариев
    FUTURE_SCENARIO_TEMPLATES: dict[str, list[str]] = {
        "satya_yuga": [
            "Золотой век продолжается: знания Аркаима распространяются по миру",
            "Цивилизация достигла гармонии: технологии и духовность сосуществуют",
        ],
        "treta_yuga": [
            "Эпоха переходов: старые знания трансформируются в новые формы",
            "Ритуальные практики сохраняют связь с аркаимским наследием",
        ],
        "dvapara_yuga": [
            "Дуальность эпохи: конфликт между сохранением и утратой знаний",
            "Технологический прогресс встречается с духовным регрессом",
        ],
        "kali_yuga": [
            "Эпоха хаоса: утрата связей с аркаимским наследием",
            "Знания скрыты под слоями забвения и мифологизации",
        ],
        "arkaim_era": [
            "Аркаим как вечный символ: наследие влияет на современность",
            "Археологическое открытие пробуждает интерес к древним знаниям",
        ],
    }

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._checker = CompatibilityChecker(world_model)

    def extrapolate(
        self,
        prompt: str = "",
        max_futures: int = 5,
        anchor_id: str = "arkaim_era",
    ) -> dict:
        """Экстраполировать будущие сценарии от якоря.

        Args:
            prompt: пользовательский запрос/контекст для генерации
            max_futures: максимальное количество сценариев
            anchor_id: temporal node ID для начала экстраполяции

        Returns:
            dict с ключами: chain_stats, scenarios, anchor_info
        """
        # 1. Build FORWARD chain from anchor
        chain = self._build_forward_chain(anchor_id)

        # 2. Extract patterns from chain
        patterns = self._extract_patterns(chain) if chain else []

        # 3. Generate scenarios from patterns + prompt
        scenarios_raw = self._generate_scenarios(patterns, prompt)

        # 4. Filter via CompatibilityChecker
        scenarios_filtered = self._filter_by_compatibility(scenarios_raw, max_futures)

        # 5. Build result
        anchor_node = chain.get_node(anchor_id) if chain else None

        # M8.1: Tag scenarios with FUTURE_EXTRAPOLATION provenance
        from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
        future_provenance = [ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
            confidence=0.5,
            notes="future projection from arkaim canon — not historical fact",
        )]

        return {
            "anchor_id": anchor_id,
            "anchor_label": anchor_node.label if anchor_node else anchor_id,
            "chain_stats": {
                "nodes": len(chain.nodes) if chain else 0,
                "relations": len(chain.relations) if chain else 0,
                "direction": chain.direction.value if chain and chain.direction else "FORWARD",
            },
            "patterns_count": len(patterns),
            "scenarios": scenarios_filtered,
            "provenance": future_provenance,
            "provenance_note": "FUTURE_EXTRAPOLATION — projection from canon, not historical fact",
        }

    def _build_forward_chain(self, anchor_id: str) -> Optional[TemporalChain]:
        """Build FORWARD chain from anchor using TemporalReconstructionEngine.

        Uses only outgoing PRECEDES relations (strictly forward direction).
        Normalizes anchor_id to temporal_ prefix if needed.
        """
        # Normalize anchor_id
        if not anchor_id.startswith("temporal_"):
            anchor_id = f"temporal_{anchor_id}"

        engine = TemporalReconstructionEngine.from_world_model(self._wm)

        # Check if anchor exists in graph
        anchor_node = engine.get_node(anchor_id)
        if not anchor_node:
            log.info("anchor_not_in_graph id=%s", anchor_id)
            return None

        # BFS following ONLY outgoing PRECEDES relations (strictly forward)
        visited: set[str] = {anchor_id}
        result: list[str] = [anchor_id]
        queue = [(anchor_id, 0)]

        while queue:
            next_queue = []
            for current_id, depth in queue:
                for rel in engine._graph.get_outgoing(current_id):
                    if rel.relation_type == "PRECEDES":
                        nid = rel.target_id
                        if nid not in visited:
                            visited.add(nid)
                            result.append(nid)
                            next_queue.append((nid, depth + 1))
            queue = next_queue

        if len(result) <= 1:
            # No forward successors found
            return TemporalChain(
                id=f"future_chain_{anchor_id}",
                label=f"Future Chain from {anchor_id}",
                direction=ChainDirection.FORWARD,
                provenance=[],
            )

        # Build chain from traced nodes
        chain = TemporalChain(
            id=f"future_chain_{anchor_id}",
            label=f"Future Chain from {anchor_id}",
            direction=ChainDirection.FORWARD,
            provenance=[],
        )

        # M8.1: Tag forward chain nodes that are AFTER arkaim_era with FUTURE_EXTRAPOLATION
        from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
        future_prov = [ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
            confidence=0.5,
            notes="future epoch node — extrapolated from arkaim canon",
        )]
        # Find arkaim_era position in result list
        try:
            arkaim_idx = result.index(anchor_id)
        except ValueError:
            arkaim_idx = 0
        for nid in result[arkaim_idx + 1:]:
            node = engine.get_node(nid)
            if node and node.id != anchor_id:
                # Add FUTURE_EXTRAPOLATION provenance if not already present
                existing_cats = {p.category for p in node.provenance}
                if ProvenanceCategory.FUTURE_EXTRAPOLATION not in existing_cats:
                    node.provenance.extend(future_prov)

        # Add nodes
        for nid in result:
            node = engine.get_node(nid)
            if node:
                chain.add_node(node)

        # Add relations between consecutive nodes
        for i in range(len(result) - 1):
            src, tgt = result[i], result[i + 1]
            for rel in engine._graph.get_outgoing(src):
                if rel.target_id == tgt:
                    chain.add_relation(rel)
                    break

        return chain

    def _extract_patterns(self, chain: TemporalChain) -> list[dict]:
        """Extract development patterns from chain nodes."""
        patterns = []
        for node in chain.nodes:
            era_id = node.era_id
            pattern = {
                "node_id": node.id,
                "label": node.label,
                "era_id": era_id,
                "confidence": node.confidence,
            }
            # Add epoch context if available
            epoch = self._wm.get_epoch(era_id)
            if epoch:
                pattern["description"] = epoch.description[:100]
                pattern["order"] = epoch.order
            patterns.append(pattern)
        return patterns

    def _generate_scenarios(self, patterns: list[dict], prompt: str) -> list[str]:
        """Generate scenario descriptions from patterns + prompt.

        Deterministic: uses existing epoch data + template mapping.
        No LLM involved.
        """
        scenarios: list[str] = []

        # Base scenario from prompt or default
        if prompt.strip():
            scenarios.append(f"На основе запроса: {prompt.strip()[:200]}")

        # Generate from each pattern node
        for pat in patterns:
            era_id = pat.get("era_id", "")
            label = pat.get("label", "")

            # Use template-based scenarios
            templates = self.FUTURE_SCENARIO_TEMPLATES.get(era_id, [])
            for template in templates:
                scenario = f"{template}. От эпохи: {label}"
                if scenario not in scenarios:
                    scenarios.append(scenario)

            # Also generate from epoch description
            desc = pat.get("description", "")
            if desc and len(desc) > 10:
                scenario = f"Развитие эпохи {label}: {desc[:150]}"
                if scenario not in scenarios:
                    scenarios.append(scenario)

        # Limit to reasonable count
        return scenarios[:20]

    def _filter_by_compatibility(
        self,
        scenarios: list[str],
        max_count: int,
    ) -> list[dict]:
        """Filter and score scenarios via CompatibilityChecker."""
        results = []

        for scenario_text in scenarios:
            request = StoryRequest(prompt=scenario_text)
            try:
                report = self._checker.check(request)
                results.append({
                    "description": scenario_text,
                    "compatibility_score": round(report.overall_score, 3),
                    "is_compatible": report.is_compatible,
                    "risk_level": report.risk_level,
                    "violations_count": len(report.violations),
                    "warnings_count": len(report.warnings),
                })
            except Exception as e:
                log.warning("compatibility_check_failed scenario=%s error=%s", scenario_text[:50], e)
                results.append({
                    "description": scenario_text,
                    "compatibility_score": 0.0,
                    "is_compatible": False,
                    "risk_level": "unknown",
                    "violations_count": 0,
                    "warnings_count": 0,
                    "error": str(e),
                })

        # Sort by compatibility score descending
        results.sort(key=lambda x: x["compatibility_score"], reverse=True)

        # Return top-N
        return results[:max_count]
