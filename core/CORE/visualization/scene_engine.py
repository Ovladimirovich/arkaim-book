"""
Scene Engine — извлечение сцены из Genome + Retriever.

Thin wrapper: не генерирует промпт, только возвращает структурированные данные.
"""

from typing import Optional

from knowledge.screenplay_scene_catalog import (
    CATALOG_CHAPTER,
    get_scene as get_catalog_scene,
    list_scenes as list_catalog_scenes,
)


class SceneEngine:
    """Извлекает смысловые сцены из Book Genome."""

    def __init__(self, genome: dict, retriever=None):
        self._genome = genome
        self._retriever = retriever

    def get_scene(self, chapter: int, scene_id: str) -> Optional[dict]:
        """
        Получить сцену из Genome.
        Сначала ищем в genome.modules.scenes, потом через retriever.
        """
        if chapter == CATALOG_CHAPTER or scene_id.startswith("scene_"):
            if chapter != CATALOG_CHAPTER:
                return None
            return get_catalog_scene(scene_id)

        scenes = self._genome.get("modules", {}).get("scenes", [])
        for scene in scenes:
            if scene.get("chapter") == chapter and scene.get("scene_id") == scene_id:
                return scene

        # Fallback: ищем через retriever.
        # RAG-fallback обязан подтверждать принадлежность чанка запрошенной
        # главе: векторный поиск возвращает ближайший чанк для ЛЮБОГО запроса
        # (score неразделим у настоящих и выдуманных сцен), поэтому без проверки
        # chapter_number неизвестная сцена фабриковалась и ломала 404-контракт.
        if self._retriever:
            try:
                results = self._retriever.search(
                    f"глава {chapter} сцена {scene_id}", n_results=1
                )
                for r in results:
                    meta = r.get("metadata") or {}
                    raw_chapter = meta.get("chapter_number")
                    if raw_chapter is None:
                        continue
                    try:
                        rag_chapter = int(raw_chapter)
                    except (TypeError, ValueError):
                        continue
                    if rag_chapter == chapter:
                        return self._parse_scene_from_rag(r)
            except Exception:
                pass

        return None

    def get_scenes_by_chapter(self, chapter: int) -> list[dict]:
        """Все сцены главы."""
        if chapter == CATALOG_CHAPTER:
            return list_catalog_scenes()
        scenes = self._genome.get("modules", {}).get("scenes", [])
        return [s for s in scenes if s.get("chapter") == chapter]

    def get_character_visual(self, character_id: str) -> Optional[dict]:
        """Визуальная спецификация персонажа."""
        visual_chars = self._genome.get("modules", {}).get("character_visuals", [])
        for cv in visual_chars:
            if cv.get("character_id") == character_id:
                return cv

        # Fallback: ищем по characters и строим визуал на основе описания
        chars = self._genome.get("modules", {}).get("characters", [])
        for ch in chars:
            if ch.get("id") == character_id:
                return self._build_visual_from_character(ch)

        return None

    def get_location_visual(self, location_id: str) -> Optional[dict]:
        """Визуальная спецификация локации."""
        visual_locs = self._genome.get("modules", {}).get("location_visuals", [])
        for vl in visual_locs:
            if vl.get("location_id") == location_id:
                return vl

        # Fallback: ищем в world_entities
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == location_id.lower():
                return {
                    "location_id": we.get("name"),
                    "type": "unknown",
                    "architecture": we.get("description", "")[:100],
                    "atmosphere": "",
                    "lighting": "",
                }

        return None

    def _parse_scene_from_rag(self, rag_result: dict) -> dict:
        """Парсим сцену из RAG-результата."""
        text = rag_result.get("text", "")
        return {
            "chapter": 0,
            "scene_id": "rag_" + str(hash(text))[:8],
            "title": text[:50] + "...",
            "characters": [],
            "location": "unknown",
            "emotion": "neutral",
            "meaning_tags": [],
        }

    def _build_visual_from_character(self, character: dict) -> dict:
        """Строим визуаль на основе character description."""
        return {
            "character_id": character.get("id", ""),
            "age": "unknown",
            "clothing": character.get("description", "")[:100],
            "symbols": [],
            "color_palette": ["earth tones"],
            "visual_constants": [],
        }
