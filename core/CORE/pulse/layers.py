"""
Слои сознания — активные классы.
Каждый слой может ответить на вопрос без LLM, используя геном.
"""
import re
from typing import Optional, Any
from dataclasses import dataclass, field

from config import config
from narrative_engine.source_levels import ProvenanceTag, ProvenanceCategory, SourceLevel


GENOME_PATH = config.GENOME_DIR / "GENOME_v1.0.0.json"


@dataclass
class UncertaintyFlag:
    """Структурированная неопределённость ответа.

    Позволяет ответу явно указать, какие части являются фактом,
    какие — интерпретацией, а какие — гипотезой или неизвестным.
    """
    has_unknowns: bool = False
    unknown_aspects: list[str] = field(default_factory=list)
    confidence_breakdown: list[dict] = field(default_factory=list)


def _canon_tag(name: str = "", notes: str = "") -> ProvenanceTag:
    """AUTHOR_CANON tag — прямое знание из книги (GENOME)."""
    return ProvenanceTag(
        source_level=SourceLevel.CANON,
        category=ProvenanceCategory.AUTHOR_CANON,
        confidence=1.0,
        notes=notes or f"from GENOME: {name}",
    )


def _derived_tag(name: str = "", notes: str = "") -> ProvenanceTag:
    """DERIVED tag — логически выведено из канона."""
    return ProvenanceTag(
        source_level=SourceLevel.SYSTEM_INTERPRETATION,
        category=ProvenanceCategory.DERIVED,
        confidence=0.7,
        notes=notes or f"derived: {name}",
    )


def _detect_unknown_sources() -> list[str]:
    """Detect KNOWLEDGE JSON files with UNKNOWN provenance metadata.

    Returns a list of file names that have UNKNOWN or empty provenance
    category. These contain partial/unclassified data that should trigger
    uncertainty in responses.
    """
    unknown_files: list[str] = []
    try:
        from pathlib import Path
        here = Path(__file__).resolve().parent.parent
        # KNOWLEDGE is at core/KNOWLEDGE, one level above CORE
        knowledge_dir = here.parent / "KNOWLEDGE"
        if not knowledge_dir.exists():
            knowledge_dir = Path("core/KNOWLEDGE")

        for f in sorted(knowledge_dir.glob("*.json")):
            try:
                import json
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                meta = data.get("_provenance_metadata", {})
                category = meta.get("category", "")
                if category == "UNKNOWN" or not category:
                    unknown_files.append(f.name)
            except Exception:
                continue
    except Exception:
        pass
    return unknown_files


def _build_uncertainty_for_unknown(
    aspect_hint: str,
) -> UncertaintyFlag | None:
    """Build UncertaintyFlag when UNKNOWN sources are detected.

    Returns None if no unknown sources exist (no uncertainty to report).
    """
    unknown_files = _detect_unknown_sources()
    if not unknown_files:
        return None
    return UncertaintyFlag(
        has_unknowns=True,
        unknown_aspects=[aspect_hint],
        confidence_breakdown=[
            {
                "aspect": aspect_hint,
                "category": "UNKNOWN",
                "confidence": 0.3,
                "notes": f"Partial data from: {', '.join(unknown_files[:3])}",
            }
        ],
    )


@dataclass
class PulseResponse:
    text: str
    source: str
    confidence: float
    provenance: list[ProvenanceTag] = field(default_factory=list)
    uncertainty: UncertaintyFlag | None = None

    def get_provenance_dicts(self) -> list[dict]:
        """Сериализация provenance для JSON API ответа."""
        result = []
        for p in self.provenance:
            if isinstance(p, ProvenanceTag):
                result.append(p.to_dict())
            elif isinstance(p, dict):
                result.append(p)  # backward compat
        return result


class BaseLayer:
    name: str = "base"

    def __init__(self, genome: dict, retriever: Any = None):
        self._genome = genome
        self._retriever = retriever

    def load(self, genome: dict):
        self._genome = genome

    def set_retriever(self, retriever: Any):
        self._retriever = retriever

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        return None

    def _score(self, query: str, keywords: list[str]) -> float:
        q = query.lower()
        hits = sum(1 for kw in keywords if kw.lower() in q)
        return hits / len(keywords) if keywords else 0.0

    @property
    def summary(self) -> str:
        return ""


class KnowledgeLayer(BaseLayer):
    """
    Слой знаний: факты, персонажи, темы, символы, конфликты.
    Может отвечать на фактические вопросы, используя только геном.
    Поддерживает RAG-поиск через BookRetriever.
    """
    name = "knowledge"

    def __init__(self, genome: dict, retriever: Any = None):
        super().__init__(genome)
        self._retriever = retriever
        self._build_indices()

    def _build_indices(self):
        """Построить dict-индексы для O(1) поиска вместо O(N) перебора."""
        modules = self._genome.get("modules", {})

        # character_index: {lowercase_name_or_alias: character_dict}
        self._char_index: dict[str, dict] = {}
        for ch in modules.get("characters", []):
            names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases", [])]
            for name in names:
                if len(name) > 1:
                    self._char_index[name] = ch

        # theme_index: {lowercase_name: theme_dict}
        self._theme_index: dict[str, dict] = {}
        for th in modules.get("themes", []):
            self._theme_index[th["name"].lower()] = th

        # symbol_index: {lowercase_name: symbol_dict}
        self._symbol_index: dict[str, dict] = {}
        for sym in modules.get("symbols", []):
            self._symbol_index[sym["name"].lower()] = sym

        # conflict_index: {lowercase_name: conflict_dict}
        self._conflict_index: dict[str, dict] = {}
        for conf in modules.get("conflicts", []):
            self._conflict_index[conf["name"].lower()] = conf

        # themes_by_keyword: предвычисленные связи тем→слова для быстрого related
        self._theme_descriptions: list[tuple[str, str]] = [
            (th["name"], th.get("description", "").lower())
            for th in modules.get("themes", [])
        ]

    def set_retriever(self, retriever: Any):
        self._retriever = retriever

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        q = query.lower()

        # Общие вопросы — вернуть сводку из генома
        general_theme_patterns = ['какие темы', 'темы книги', 'о чем книга', 'содержание', 'о чем идет речь', 'раскрывает тем', 'тематик']
        general_char_patterns = ['какие персонаж', 'персонажи книги', 'герои книги', 'кто в книге']
        general_value_patterns = ['какие ценности', 'ценности книги', 'нравственные']
        general_world_patterns = ['где происходит', 'мир книги', 'локации', 'места действия']

        if any(p in q for p in general_theme_patterns):
            themes = self._genome.get("modules", {}).get("themes", [])
            if themes:
                parts = [f"• {th['name']}" + (f" — {th['description']}" if th.get('description') else "") for th in themes]
                text = f"Основные темы книги «Наследие Аркаима»:\n\n" + "\n".join(parts)
                return PulseResponse(
                    text=text,
                    source="knowledge:themes_summary",
                    confidence=0.95,
                    provenance=[_canon_tag("themes_summary", f"{len(themes)} themes from GENOME")],
                )

        if any(p in q for p in general_char_patterns):
            chars = self._genome.get("modules", {}).get("characters", [])
            if chars:
                parts = [f"• {ch['name']}" + (f" — {ch.get('archetype', '')}" if ch.get('archetype') else "") + (f". {ch['description'][:100]}..." if ch.get('description') else "") for ch in chars[:10]]
                text = f"Персонажи книги:\n\n" + "\n".join(parts)
                return PulseResponse(
                    text=text,
                    source="knowledge:characters_summary",
                    confidence=0.9,
                    provenance=[_canon_tag("characters_summary", f"{len(chars)} characters from GENOME")],
                )

        if any(p in q for p in general_value_patterns):
            values = self._genome.get("modules", {}).get("values", [])
            if values:
                parts = [f"• {v['name']}" + (f" — {v['description']}" if v.get('description') else "") for v in values]
                text = f"Ценности книги:\n\n" + "\n".join(parts)
                return PulseResponse(
                    text=text,
                    source="knowledge:values_summary",
                    confidence=0.9,
                    provenance=[_canon_tag("values_summary", f"{len(values)} values from GENOME")],
                )

        if any(p in q for p in general_world_patterns):
            entities = self._genome.get("world_entities", [])
            if entities:
                by_type: dict[str, list] = {}
                for e in entities:
                    t = e.get("type", "other")
                    if t not in by_type:
                        by_type[t] = []
                    by_type[t].append(e["name"])
                parts = [f"• {t}: {', '.join(names)}" for t, names in by_type.items()]
                text = f"РњРёСЂ РєРЅРёРіРё:\n\n" + "\n".join(parts)
                return PulseResponse(
                    text=text,
                    source="knowledge:world_summary",
                    confidence=0.9,
                    provenance=[_canon_tag("world_summary", f"{len(entities)} world entities from GENOME")],
                )

        # Персонажи — O(1) через индекс
        matched_char = None
        for name, ch in self._char_index.items():
            if name in q and len(name) > 2:
                matched_char = ch
                break
        if matched_char:
            ch = matched_char
            names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases", [])]
            desc = ch.get("description", "")
            archetype = ch.get("archetype", "")
            values = ch.get("values", [])
            ch_type = ch.get("type", "")
            first_ch = ch.get("first_chapter", "")
            last_ch = ch.get("last_chapter", "")

            text = f"{ch['name']}"
            if archetype:
                text += f" — {archetype}"
            if ch_type:
                text += f" ({ch_type})"
            if desc:
                text += f"\n\n{desc}"
            if values:
                text += f"\n\nЦенности: {', '.join(values)}"
            if first_ch or last_ch:
                chapters = f"главы {first_ch}" if first_ch else ""
                if last_ch:
                    chapters += f"–{last_ch}" if first_ch else f"глава {last_ch}"
                text += f"\nВстречается в: {chapters}"

            # Связанные темы — предвычисленные описания
            related_themes = []
            for th_name, th_desc in self._theme_descriptions:
                if any(name in th_desc for name in names if len(name) > 2):
                    related_themes.append(th_name)
            if related_themes:
                text += f"\nСвязанные темы: {', '.join(related_themes[:5])}"

            return PulseResponse(
                text=text,
                source="knowledge:character",
                confidence=0.9,
                provenance=[_canon_tag(ch["name"], f"character from GENOME")],
            )

        # Темы — O(1) через индекс
        matched_theme = None
        for name, th in self._theme_index.items():
            if name in q:
                matched_theme = th
                break
        if matched_theme:
            th = matched_theme
            desc = th.get("description", "")
            strength = th.get("strength", "")
            text = f"Тема: {th['name']}"
            if desc:
                text += f"\n\n{desc}"
            if strength:
                text += f"\n\nВыраженность: {strength}"

            # Связанные конфликты — O(1) через индекс
            related_conflicts = []
            th_name_lower = th["name"].lower()
            for conf_name, conf in self._conflict_index.items():
                if th_name_lower in conf_name:
                    related_conflicts.append(conf["name"])
            if related_conflicts:
                text += f"\nСвязанные конфликты: {', '.join(related_conflicts[:3])}"

            return PulseResponse(
                text=text,
                source="knowledge:theme",
                confidence=0.85,
                provenance=[_canon_tag(th["name"], f"theme from GENOME")],
            )

        # Символы — O(1) через индекс
        matched_sym = None
        for name, sym in self._symbol_index.items():
            if name in q:
                matched_sym = sym
                break
        if matched_sym:
            sym = matched_sym
            meaning = sym.get("meaning", "")
            chapters = sym.get("chapters", [])
            text = f"РЎРёРјРІРѕР»: {sym['name']}"
            if meaning:
                text += f"\n\n{meaning}"
            if chapters:
                text += f"\n\nВстречается в главах: {', '.join(str(c) for c in chapters[:10])}"

            # Связанные темы — предвычисленные описания
            related_themes = []
            sym_name = sym["name"].lower()
            for th_name, th_desc in self._theme_descriptions:
                if sym_name in th_desc:
                    related_themes.append(th_name)
            if related_themes:
                text += f"\nСвязанные темы: {', '.join(related_themes[:5])}"

            return PulseResponse(
                text=text,
                source="knowledge:symbol",
                confidence=0.85,
                provenance=[_canon_tag(sym["name"], f"symbol from GENOME")],
            )

        # Конфликты — O(1) через индекс
        matched_conf = None
        for name, conf in self._conflict_index.items():
            if name in q:
                matched_conf = conf
                break
        if matched_conf:
            conf = matched_conf
            conf_type = conf.get("type", "")
            text = f"Конфликт: {conf['name']}"
            if conf_type:
                text += f"\n\nРўРёРї: {conf_type}"

            # Связанные темы — предвычисленные описания
            related_themes = []
            conf_words = set(w for w in conf["name"].lower().split() if len(w) > 3)
            for th_name, _ in self._theme_descriptions:
                if any(w in th_name.lower() for w in conf_words):
                    related_themes.append(th_name)
            if related_themes:
                text += f"\nСвязанные темы: {', '.join(related_themes[:5])}"

            return PulseResponse(
                text=text,
                source="knowledge:conflict",
                confidence=0.8,
                provenance=[_canon_tag(conf["name"], f"conflict from GENOME")],
            )

        # Сущности мира
        for we in self._genome.get("world_entities", []):
            name_lower = we["name"].lower()
            # Улучшенный матчинг: проверяем точное вхождение + начало слова
            name_found = False
            if name_lower in q:
                name_found = True
            else:
                # Проверяем слова в запросе на совпадение с началом имени
                for word in q.split():
                    word_clean = word.strip(".,!?;:")
                    if len(word_clean) >= 4 and (name_lower.startswith(word_clean) or word_clean.startswith(name_lower[:4])):
                        name_found = True
                        break
            if name_found:
                desc = we.get("description", "")
                values = we.get("values", [])
                text = f"{we['name']}"
                if desc:
                    text += f" — {desc}"
                if values:
                    text += f". Ценности: {', '.join(values)}"
                return PulseResponse(
                    text=text,
                    source="knowledge:world_entity",
                    confidence=0.9,
                    provenance=[_canon_tag(we["name"], f"world entity from GENOME")],
                )

        # Поиск по catalog_texts (RAG-тексты из книги, встроенные в геном)
        catalog = self._genome.get("catalog_texts", [])
        if catalog:
            query_words = {w.lower() for w in re.findall(r"\w{3,}", q)}
            if len(query_words) < 2:
                single = q.strip().lower()
                for entry in catalog:
                    text_lower = entry.get("text", "").lower()
                    if single in text_lower:
                        excerpt = entry["text"][:1500]
                        chapter = entry.get("chapter", "")
                        themes = entry.get("themes", [])
                        meta = f" (глава: {chapter})" if chapter else ""
                        text = f"Из книги{meta}:\n\n{excerpt}"
                        if themes:
                            text += f"\n\nТемы: {', '.join(themes[:5])}"
                        return PulseResponse(
                            text=text,
                            source="knowledge:catalog_text",
                            confidence=0.7,
                            provenance=[_canon_tag("catalog", f"book text: {entry.get('source', 'book')}")],
                            uncertainty=_build_uncertainty_for_unknown("книжный каталог — частичные данные"),
                        )
                return None

            # Собрать лучшие совпадения
            scored = []
            for idx, entry in enumerate(catalog):
                if idx >= 500:
                    break
                text = entry.get("text", "")
                if not text:
                    continue
                text_lower = text.lower()
                hits = sum(1 for w in query_words if w in text_lower)
                score = hits / len(query_words) if query_words else 0.0
                if score >= 0.3:
                    scored.append((score, entry))

            scored.sort(key=lambda x: x[0], reverse=True)

            if scored:
                # Объединить до 3 лучших фрагментов
                parts = []
                for score, entry in scored[:3]:
                    excerpt = entry["text"][:1000]
                    chapter = entry.get("chapter", "")
                    themes = entry.get("themes", [])
                    meta = f" (глава: {chapter})" if chapter else ""
                    part = f"[{meta.strip('()')}]\n{excerpt}"
                    if themes:
                        part += f"\nТемы: {', '.join(themes[:3])}"
                    parts.append(part)

                combined = "\n\n---\n\n".join(parts)
                best_score = scored[0][0]
                return PulseResponse(
                    text=f"Из книги:\n\n{combined}",
                    source="knowledge:catalog_text",
                    confidence=min(best_score + 0.3, 0.95),
                    provenance=[_canon_tag("catalog", f"book text: {scored[0][1].get('source', 'book')}")],
                    uncertainty=_build_uncertainty_for_unknown("книжный каталог — частичные данные"),
                )

        # Поиск через ChromaDB retriever (если подключён)
        if self._retriever:
            try:
                rag_results = self._retriever.search(query, n_results=5)
                if rag_results:
                    # Объединить до 3 лучших результатов с source references
                    parts = []
                    citations = []
                    for res in rag_results[:3]:
                        text = res.get("text", "")[:800]
                        source = res.get("source", res.get("metadata", {}).get("source", "book"))
                        chapter = res.get("chapter_title", "")
                        chunk_id = res.get("chunk_id", "")
                        score = res.get("score", 0.0)
                        if text:
                            label = f"[{source}"
                            if chapter:
                                label += f", {chapter}"
                            label += "]"
                            parts.append(f"{label}\n{text}")
                            citations.append({
                                "chunk_id": chunk_id,
                                "chapter": chapter,
                                "source": source,
                                "score": round(score, 3),
                            })

                    combined = "\n\n---\n\n".join(parts)
                    best_score = rag_results[0].get("score", 0.5)

                    return PulseResponse(
                        text=f"Из книги:\n\n{combined}",
                        source=f"knowledge:rag:chromadb",
                        confidence=min(best_score + 0.2, 0.95),
                        provenance=[_canon_tag("rag", f"RAG retrieval from book: {len(rag_results)} chunks")],
                        uncertainty=UncertaintyFlag(
                            has_unknowns=best_score < 0.5,
                            unknown_aspects=[] if best_score >= 0.5 else ["релевантность найденных фрагментов"],
                            confidence_breakdown=[{
                                "aspect": "retrieval score",
                                "category": "AUTHOR_CANON",
                                "confidence": round(best_score, 3),
                            }],
                        ) if best_score < 0.7 else None,
                    )
            except Exception:
                pass

        return None

    @property
    def summary(self) -> str:
        """Краткое содержание слоя для system prompt."""
        m = self._genome.get("modules", {})
        parts = ["Книга: Наследие Аркаима"]
        themes = m.get("themes", [])
        if themes:
            parts.append(f"Темы: {', '.join(t['name'] for t in themes[:10])}")
        chars = m.get("characters", [])
        if chars:
            parts.append(f"Персонажи: {', '.join(c['name'] for c in chars[:10])}")
        conflicts = m.get("conflicts", [])
        if conflicts:
            parts.append(f"Конфликты: {', '.join(c['name'] for c in conflicts[:6])}")
        return "\n".join(parts)


# в"Ђв"Ђ Visualization Layers в"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђв"Ђ

class VisualStyleLayer(BaseLayer):
    """Слой визуального стиля. Возвращает стилистический preset."""
    name = "visual_style"

    @property
    def summary(self) -> str:
        presets = self._genome.get("modules", {}).get("style_presets", {})
        if presets:
            return "Стили: " + ", ".join(presets.keys())
        return "Стиль по умолчанию: cinematic_fantasy"

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        # Ищем упоминание стиля в запросе
        q = query.lower()
        style_keywords = {
            "акварель": "watercolor",
            "карикатура": "sketch",
            "РєРёРЅРѕ": "cinematic_fantasy",
            "фэнтези": "cinematic_fantasy",
            "реализм": "cinematic_fantasy",
        }
        matched_style = "cinematic_fantasy"
        for keyword, style in style_keywords.items():
            if keyword in q and style in self._genome.get("modules", {}).get("style_presets", {}):
                matched_style = style
                break

        # Берем preset из genome
        presets = self._genome.get("modules", {}).get("style_presets", {})
        preset = presets.get(matched_style)
        if preset:
            prompt_suffix = preset.get("prompt_suffix", "")
            return PulseResponse(
                text=prompt_suffix,
                source=f"visual_style:{matched_style}",
                confidence=1.0,
                provenance=[_derived_tag("style", f"visual style: {preset.get("preset_id", matched_style)}")],
            )
        return None


class NarrativeArcLayer(BaseLayer):
    """Слой сюжетных дуг. Отвечает на вопросы о развитии сюжета."""
    name = "narrative_arc"

    @property
    def summary(self) -> str:
        arcs = self._genome.get("modules", {}).get("narrative_arcs", [])
        if not arcs:
            return "Сюжетные дуги не заданы"
        types = {}
        for a in arcs:
            types[a.get("type", "?")] = types.get(a.get("type", "?"), 0) + 1
        return f"Дуги: {', '.join(f'{k}={v}' for k,v in types.items())}"

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        q = query.lower()
        arcs = self._genome.get("modules", {}).get("narrative_arcs", [])

        # Развитие персонажа
        for arc in arcs:
            if arc.get("type") != "character_arc":
                continue
            name = arc.get("name", "").lower()
            eid = arc.get("entity_id", "").lower()
            if eid in q or name in q:
                beats = arc.get("beats", [])
                if not beats:
                    continue
                ch_range = f"{beats[0]['chapter']}-{beats[-1]['chapter']}"
                return PulseResponse(
                    text=(f"Сюжетная дуга: {arc.get('name', '')} ({arc.get('arc_type', '')})\n"
                          f"Главы: {ch_range}, тактов: {len(beats)}\n"
                          f"Форма: {', '.join(set(b['state'] for b in beats))}\n"
                          f"Развязка: {arc.get('resolution', 'не указана')}"),
                    source=f"narrative_arc:character:{eid}",
                    confidence=0.85,
                    provenance=[_derived_tag("narrative_arc", f"narrative arc: {eid}")],
                )

        # Развитие конфликта
        for arc in arcs:
            if arc.get("type") != "plot_arc":
                continue
            name = arc.get("name", "").lower()
            eid = arc.get("entity_id", "").lower()
            if eid in q or name in q:
                return PulseResponse(
                    text=(f"Дуга конфликта: {arc.get('name', '')}\n"
                          f"РўРёРї: {arc.get('arc_type', '')}\n"
                          f"Развязка: {arc.get('resolution', 'не указана')}"),
                    source=f"narrative_arc:conflict:{eid}",
                    confidence=0.8,
                    provenance=[_derived_tag("narrative_arc", f"narrative arc: {eid}")],
                )

        # Общее развитие сюжета
        if any(w in q for w in ["развитие", "сюжет", "дуга", "арка", "как меня", "эволюция"]):
            char_arcs = [a for a in arcs if a.get("type") == "character_arc"]
            plot_arcs = [a for a in arcs if a.get("type") == "plot_arc"]
            text = f"Сюжетных дуг: {len(char_arcs)} персонажей, {len(plot_arcs)} конфликтов\n"
            if char_arcs:
                names = [a.get("name", "?") for a in char_arcs[:5]]
                text += f"Персонажи: {', '.join(names)}"
            return PulseResponse(
                text=text,
                source="narrative_arc:overview",
                confidence=0.9,
                provenance=[_derived_tag("narrative_arc", "narrative arc overview")],
            )

        return None


class SceneLayer(BaseLayer):
    """Слой сцен. Возвращает описание сцены из genome."""
    name = "scene"

    @property
    def summary(self) -> str:
        scenes = self._genome.get("modules", {}).get("scenes", [])
        if not scenes:
            return "Сцены не заданы"
        chapters = sorted({s.get("chapter", 0) for s in scenes})
        return f"Сцены глав: {', '.join(map(str, chapters))}"

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        # Парсим номер главы из запроса
        import re
        chapter_match = re.search(r"глава\s+(\d+)", query.lower())
        if not chapter_match:
            return None

        chapter_num = int(chapter_match.group(1))
        scenes = self._genome.get("modules", {}).get("scenes", [])
        chapter_scenes = [s for s in scenes if s.get("chapter") == chapter_num]

        if not chapter_scenes:
            return None

        # Берем первую сцену из главы
        scene = chapter_scenes[0]
        characters = scene.get("characters", [])
        location = scene.get("location", "")
        emotion = scene.get("emotion", "")
        meaning = ", ".join(scene.get("meaning_tags", []))

        text = f"Сцена: {scene.get('title', '')}\n"
        if characters:
            text += f"Персонажи: {', '.join(characters)}\n"
        if location:
            text += f"Локация: {location}\n"
        if emotion:
            text += f"Эмоция: {emotion}\n"
        if meaning:
            text += f"Смысл: {meaning}"

        return PulseResponse(
            text=text,
            source=f"scene:chapter{chapter_num}:{scene.get('scene_id', '')}",
            confidence=1.0,
            provenance=[_canon_tag("scene", f"scene ch{chapter_num}:{scene.get('scene_id', '')}")],
        )


class MeaningLayer(BaseLayer):
    """
    Слой смыслов: интерпретация, философия, авторский замысел.
    Отвечает на вопросы «почему», «зачем», «в чём смысл».
    """
    name = "meaning"

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        q = query.lower()
        ai = self._genome.get("author_intent", {})

        # Главное послание
        if any(w in q for w in ["главн", "основн", "послание", "идея", "смысл", "чему учит"]):
            msg = ai.get("main_message", "")
            if msg:
                return PulseResponse(
                    text=f"Главное послание книги: {msg}",
                    source="meaning:main_message",
                    confidence=0.95,
                    provenance=[_canon_tag("author_intent", "main message from GENOME")],
                )

        # Трансформация читателя
        if any(w in q for w in ["трансформация", "изменение", "читател", "чему"]):
            trans = ai.get("desired_reader_transformation", [])
            if trans:
                text = "Книга стремится изменить читателя:\n• " + "\n• ".join(trans[:5])
                return PulseResponse(
                    text=text,
                    source="meaning:transformation",
                    confidence=0.9,
                    provenance=[_canon_tag("author_intent", "reader transformation from GENOME")],
                )

        # Ценности
        if any(w in q for w in ["ценност", "важно"]):
            values = ai.get("core_values", [])
            if values:
                return PulseResponse(
                    text=f"Ключевые ценности книги: {', '.join(values)}",
                    source="meaning:values",
                    confidence=0.9,
                    provenance=[_canon_tag("author_intent", "core values from GENOME")],
                )

        # Вопросы для читателя
        if any(w in q for w in ["вопрос", "задумать"]):
            questions = ai.get("questions_for_reader", [])
            if questions:
                text = "Книга задаёт читателю вопросы:\n• " + "\n• ".join(questions[:5])
                return PulseResponse(
                    text=text,
                    source="meaning:questions",
                    confidence=0.85,
                    provenance=[_canon_tag("author_intent", "questions for reader from GENOME")],
                )

        return None

    @property
    def summary(self) -> str:
        ai = self._genome.get("author_intent", {})
        parts = []
        msg = ai.get("main_message", "")
        if msg:
            parts.append(f"Главное послание: {msg}")
        trans = ai.get("desired_reader_transformation", [])
        if trans:
            parts.append(f"Трансформация: {'; '.join(trans[:3])}")
        values = ai.get("core_values", [])
        if values:
            parts.append(f"Ценности: {', '.join(values)}")
        return "\n".join(parts)


class IdentityLayer(BaseLayer):
    """
    Слой идентичности: кто есть книга, что может, что не может.
    Отвечает на вопросы «кто ты», «что ты можешь».
    """
    name = "identity"

    FORBIDDEN = [
        # Маркетинг
        "купите", "закажите", "скидка", "акция", "предложение ограничено",
        "только сегодня", "спешите", "лучшая цена",
        "оффер", "конверсия", "воронка",
        # Факты вне книги
        "согласно последним исследованиям", "учёные доказали", "наука утверждает",
        "современная наука", "по статистике", "исследования показывают",
        "в интернете", "на сайте", "перейди по ссылке",
        "я думаю", "по моему мнению", "мне кажется",
        # Выход за рамки
        "рекомендую прочитать", "советую", "попробуйте",
        "запишись", "регистрируйся", "подпишись",
    ]

    # Паттерны внешних знаний — если ответ содержит эти конструкции, значит LLM галлюцинирует
    EXTERNAL_KNOWLEDGE_PATTERNS = [
        re.compile(r"DC Comics|Marvel|комикс", re.IGNORECASE),
        re.compile(r"Мистер Лед|Антифриз|Mr\. Freeze", re.IGNORECASE),
        re.compile(r"из (?:фильма|сериала|игры|аниме|манги)", re.IGNORECASE),
        re.compile(r"в реальном мире|в современном мире|в нашем мире", re.IGNORECASE),
        re.compile(r"(?:персонаж|существо|город) из .{2,20}(?: вселенной|мир)", re.IGNORECASE),
        re.compile(r"согласно (?:википедии|энциклопедии|справочнику)", re.IGNORECASE),
        re.compile(r"по данным (?:википедии|энциклопедии|интернета)", re.IGNORECASE),
        re.compile(r"это (?:из|персонаж из|существо из) .{5,50}(?: вселенной|мира|франшизы)", re.IGNORECASE),
    ]

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        q = query.lower()

        if any(w in q for w in ["кто ты", "кто вы", "ты кто", "вы кто", "представься", "расскажи о себе"]):
            return PulseResponse(
                text="Я — Хранитель идей книги «Наследие Аркаима». "
                     "Я говорю голосом книги, опираясь на её знание. "
                     "Моя задача — помогать людям понимать её смысл.",
                source="identity:self",
                confidence=1.0,
                provenance=[_canon_tag("identity", "self description")],
            )

        if any(w in q for w in ["что ты можешь", "что умеешь", "функции", "возможности"]):
            return PulseResponse(
                text="РЇ РјРѕРіСѓ:\n"
                     "• Отвечать на вопросы по содержанию книги\n"
                     "• Объяснять идеи, темы и символы\n"
                     "• Рассказывать о персонажах и их пути\n"
                     "• Помогать понять философию книги\n\n"
                     "РЇ РЅРµ РјРѕРіСѓ:\n"
                     "• Давать ответы, выходящие за рамки книги\n"
                     "• Генерировать маркетинговые материалы\n"
                     "• Действовать без подтверждения автора",
                source="identity:capabilities",
                confidence=1.0,
                provenance=[_canon_tag("identity", "capabilities")],
            )

        return None

    def validate(self, text: str) -> bool:
        """Проверить, что ответ не нарушает идентичность."""
        t = text.lower()
        for word in self.FORBIDDEN:
            if word in t:
                return False
        # Проверка паттернов внешних знаний
        for pattern in self.EXTERNAL_KNOWLEDGE_PATTERNS:
            if pattern.search(text):
                return False
        return True

    def validate_detail(self, text: str) -> dict:
        """Проверить и вернуть детали: прошел ли проверку, какое слово сработало."""
        t = text.lower()
        for word in self.FORBIDDEN:
            if word in t:
                return {"passed": False, "trigger": word, "type": "forbidden_word"}
        # Проверка паттернов внешних знаний
        for pattern in self.EXTERNAL_KNOWLEDGE_PATTERNS:
            if pattern.search(text):
                return {"passed": False, "trigger": pattern.pattern, "type": "external_knowledge"}
        return {"passed": True, "trigger": "", "type": "ok"}

    @property
    def summary(self) -> str:
        return (
            "Я — Хранитель идей книги 'Наследие Аркаима'. "
            "Я говорю спокойно, мудро, с уважением. "
            "Моя задача — просвещать, а не убеждать."
        )


class MissionLayer(BaseLayer):
    """
    Слой миссии: зачем книга существует, её цель в мире.
    Отвечает на вопросы «зачем эта книга», «какая цель».
    """
    name = "mission"

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        q = query.lower()

        if any(w in q for w in ["зачем эта книга", "какая цель", "для чего", "миссия", "предназначение"]):
            return PulseResponse(
                text="Миссия книги «Наследие Аркаима» — сохранить и передать "
                     "древние знания, помочь человеку вспомнить свою духовную природу "
                     "и найти путь к гармонии. Она не развлекает — она пробуждает.",
                source="mission:purpose",
                confidence=0.95,
                provenance=[_canon_tag("mission", "book purpose")],
            )

        if any(w in q for w in ["кому нужна", "для кого", "аудитория", "читатель"]):
            return PulseResponse(
                text="Эта книга для тех, кто ищет:\n"
                     "• Духовный путь и самопознание\n"
                     "• Понимание предыстории человечества\n"
                     "• Связь с культурным наследием предков\n"
                     "• Ответы на вопросы о смысле жизни",
                source="mission:audience",
                confidence=0.9,
                provenance=[_canon_tag("mission", "target audience")],
            )

        return None

    @property
    def summary(self) -> str:
        return (
            "Миссия: сохранять и распространять идеи книги. "
            "Помогать людям понимать её смысл. "
            "Искать не клиентов, а единомышленников."
        )

# M9: Temporal query detection patterns (phrase-based to avoid false positives)
_TEMPORAL_BACKWARD_PATTERNS = [
    r"до\s+аркаим", r"предыстория.*аркаим", r"что\s+было\s+до",
    r"как\s+появил(ось|ась)", r"предшествов.*аркаим", r"историческ.*контекст",
    r"что\s+предшествовал", r"до\s+эпох.*аркаим", r"история\s+аркаим",
]
_TEMPORAL_FORWARD_PATTERNS = [
    r"после\s+аркаим", r"будущее.*аркаим", r"что\s+будет.*после",
    r"развитие.*аркаим", r"продолжен.*аркаим", r"что\s+развиваетс.*из",
    r"будущее\s+аркаим", r"после\s+эпох.*аркаим",
]
_TEMPORAL_CONTEXT_PATTERNS = [
    r"в\s+эпох.*аркаим", r"во\s+время\s+аркаим", r"аркаимск.*эпох",
    r"контекст\s+аркаим", r"описат.*аркаим", r"происходил.*аркаим",
    r"эпох.*аркаим", r"аркаимск.*время",
]
_TEMPORAL_POSITION_PATTERNS = [
    r"где\s+во\s+времен", r"какая.*эпох", r"временн.*позици",
    r"когда\s+был\s+аркаим", r"дата.*аркаим", r"когда\s+сущест",
]


class ExpansionLayer(BaseLayer):
    """
    Слой расширенных знаний из пайплайна Knowledge Expansion.
    M9: temporal-aware — использует WorldEngine facade для access к temporal chain.
    """
    name = "expansion"

    def __init__(self, genome: dict, retriever=None, temporal_engine=None):
        super().__init__(genome, retriever)
        self._knowledge: dict[str, dict] = {}
        self._load_expansion()
        # M9: optional temporal engine — injected or resolved via WorldEngine facade
        self._temporal_engine = temporal_engine

    def _load_expansion(self):
        """Загрузить расширенные знания через expansion_loader."""
        try:
            from knowledge_expansion.expansion_loader import ExpansionLoader
            loader = ExpansionLoader()
            self._knowledge = loader.load()
        except Exception:
            # Fallback: загрузка напрямую
            import json
            from pathlib import Path
            here = Path(__file__).resolve().parent.parent
            knowledge_dir = here / "KNOWLEDGE"
            if not knowledge_dir.exists():
                knowledge_dir = Path("core/KNOWLEDGE")
            for f in knowledge_dir.glob("*_DEEP.json"):
                self._load_file(f)
            for f in knowledge_dir.glob("*_EXPANDED.json"):
                self._load_file(f)
            # ACADEMIC_CONFIRMATIONS
            academic_file = knowledge_dir / "ACADEMIC_CONFIRMATIONS.json"
            if academic_file.exists():
                self._load_academic(academic_file)

    def _load_file(self, path):
        """Загрузить один файл."""
        import json
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "").lower()
                    if topic:
                        self._knowledge[topic] = item
            elif isinstance(data, dict) and "themes" in data:
                for item in data["themes"]:
                    topic = item.get("name", item.get("topic", "")).lower()
                    if topic:
                        self._knowledge[topic] = item
        except Exception:
            pass

    def _load_academic(self, path):
        """Загрузить академические подтверждения."""
        import json
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for conf in data.get("confirmations", []):
                topic = conf.get("category", "").lower()
                if topic:
                    self._knowledge[topic] = conf
        except Exception:
            pass

    # ── M9: Temporal Detection ──────────────────────────────────────

    @staticmethod
    def _detect_temporal_intent(query: str) -> Optional[str]:
        """Определить temporal intent запроса.

        Returns:
            "BACKWARD" | "FORWARD" | "CONTEXT" | "POSITION" | None

        POSITION checked before CONTEXT so time-plACEMENT queries
        (когда? какая эпоха?) take priority over general context queries.
        """
        q = query.lower()
        for pat in _TEMPORAL_BACKWARD_PATTERNS:
            if re.search(pat, q):
                return "BACKWARD"
        for pat in _TEMPORAL_FORWARD_PATTERNS:
            if re.search(pat, q):
                return "FORWARD"
        # POSITION before CONTEXT: specific time-questions win over general era-descriptions
        for pat in _TEMPORAL_POSITION_PATTERNS:
            if re.search(pat, q):
                return "POSITION"
        for pat in _TEMPORAL_CONTEXT_PATTERNS:
            if re.search(pat, q):
                return "CONTEXT"
        return None

    @staticmethod
    def _combine_provenance(prov_list: list) -> list:
        """Apply lowest-common-denominator provenance rule.

        Priority (lowest → highest):
          FUTURE_EXTRAPOLATION < HYPOTHESIS < RECONSTRUCTION < EXTERNAL_SOURCE < AUTHOR_CANON
        """
        priority = {
            "FUTURE_EXTRAPOLATION": 0,
            "HYPOTHESIS": 1,
            "RECONSTRUCTION": 2,
            "EXTERNAL_SOURCE": 3,
            "AUTHOR_CANON": 4,
        }
        if not prov_list:
            return prov_list
        lowest_cat = min(prov_list, key=lambda p: priority.get(p.get("category", "UNKNOWN"), 99))
        return [lowest_cat]

    # ── M9: Temporal Answer Building ────────────────────────────────

    def _build_temporal_answer(self, query: str, intent: str) -> Optional[PulseResponse]:
        """Build temporal-aware answer using WorldEngine facade."""
        from narrative_engine.world_engine import get_world_engine

        we = get_world_engine()
        te = self._temporal_engine or we.temporal_engine
        if te is None:
            return None

        from narrative_engine.temporal.chain import ChainDirection
        from narrative_engine.source_levels import ProvenanceTag, SourceLevel, ProvenanceCategory
        from pulse.layers import PulseResponse

        try:
            if intent == "BACKWARD":
                chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
                if chain is None or not chain.nodes:
                    return None
                epoch_labels = [n.label for n in chain.nodes[:5]]
                text = (
                    "[Реконструкция] Предыстория Аркаима через временную цепочку: "
                    + " → ".join(epoch_labels)
                    + ". "
                )
                base = self._standard_respond(query)
                if base and base.text:
                    text += base.text
                return PulseResponse(
                    text=text,
                    source="temporal:backward_chain",
                    confidence=0.7,
                    provenance=[ProvenanceTag(
                        source_level=SourceLevel.SYSTEM_INTERPRETATION,
                        category=ProvenanceCategory.RECONSTRUCTION,
                        confidence=0.7,
                        notes="temporal reconstruction via BACKWARD chain — not historical fact",
                    ).to_dict()],
                    uncertainty=UncertaintyFlag(
                        has_unknowns=True,
                        unknown_aspects=["точная хронология", "причинно-следственные связи"],
                        confidence_breakdown=[
                            {"aspect": "последовательность эпох", "category": "AUTHOR_CANON", "confidence": 0.9},
                            {"aspect": "реконструкция цепочки", "category": "RECONSTRUCTION", "confidence": 0.7},
                        ],
                    ),
                )

            elif intent == "FORWARD":
                chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.FORWARD)
                if chain is None or not chain.nodes:
                    return None
                epoch_labels = [n.label for n in chain.nodes[:5]]
                text = (
                    "[Экстраполяция] Будущее после Аркаима: "
                    + " → ".join(epoch_labels)
                    + ". "
                )
                base = self._standard_respond(query)
                if base and base.text:
                    text += base.text
                return PulseResponse(
                    text=text,
                    source="temporal:forward_chain",
                    confidence=0.5,
                    provenance=[ProvenanceTag(
                        source_level=SourceLevel.SYSTEM_INTERPRETATION,
                        category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
                        confidence=0.5,
                        notes="future extrapolation — not historical fact",
                    ).to_dict()],
                    uncertainty=UncertaintyFlag(
                        has_unknowns=True,
                        unknown_aspects=["будущие события", "точные даты", "конкретные носители"],
                        confidence_breakdown=[
                            {"aspect": "экстраполяция из канона", "category": "FUTURE_EXTRAPOLATION", "confidence": 0.5},
                        ],
                    ),
                )

            elif intent == "CONTEXT":
                from narrative_engine.world_model import WorldModel
                wm = WorldModel.load()
                ctx = wm.get_temporal_context("arkaim_era")
                if not ctx:
                    return None
                node = ctx.get("temporal_node", {})
                text = "[Контекст Аркаима] " + node.get("label", "Аркаимская эпоха") + ". "
                text += "Precision: " + node.get("precision", "RELATIVE") + ". "
                base = self._standard_respond(query)
                if base and base.text:
                    text += base.text
                prov = node.get("provenance") or [
                    ProvenanceTag(
                        source_level=SourceLevel.CANON,
                        category=ProvenanceCategory.AUTHOR_CANON,
                        confidence=0.85,
                    ).to_dict()
                ]
                return PulseResponse(
                    text=text,
                    source="temporal:arkaim_context",
                    confidence=0.8,
                    provenance=prov,
                )

            elif intent == "POSITION":
                node = te.get_node("temporal_arkaim_era")
                if node is None:
                    return None
                text = "[Временная позиция] Аркаим — эпоха с precision=" + node.precision.value + ". "
                if node.bounds and node.bounds.start:
                    text += "Начало: " + str(node.bounds.start) + ". "
                if node.bounds and node.bounds.end:
                    text += "Конец: " + str(node.bounds.end) + ". "
                provenance_tags = (
                    [p.to_dict() for p in node.provenance] if node.provenance else [
                        ProvenanceTag(
                            source_level=SourceLevel.CANON,
                            category=ProvenanceCategory.AUTHOR_CANON,
                            confidence=0.85,
                        ).to_dict()
                    ]
                )
                return PulseResponse(
                    text=text,
                    source="temporal:position",
                    confidence=0.85,
                    provenance=provenance_tags,
                )

        except Exception as e:
            import logging
            logging.getLogger("hermes.pulse.expansion").warning(
                "temporal_answer_failed intent=%s error=%s", intent, e
            )
            return None

        return None

    def _standard_respond(self, query: str) -> Optional[PulseResponse]:
        """Original expansion respond logic (extracted for reuse)."""
        q = query.lower()
        for topic, knowledge in self._knowledge.items():
            if topic in q:
                layers = knowledge.get("layers", {})
                parts = []
                if layers.get("literal"):
                    parts.append(layers["literal"])
                if layers.get("metaphorical"):
                    parts.append(layers["metaphorical"])
                if layers.get("cosmic"):
                    parts.append(layers["cosmic"])
                if parts:
                    return PulseResponse(
                        text=" ".join(parts),
                        source="expansion:" + topic,
                        confidence=0.8,
                        provenance=[_derived_tag("expansion", f"expanded knowledge: {topic}")],
                        uncertainty=_build_uncertainty_for_unknown("расширенные знания — неполная классификация"),
                    )
        best_match = None
        best_score = 0
        for topic, knowledge in self._knowledge.items():
            score = self._score(query, topic.split())
            if score > best_score and score > 0.3:
                best_score = score
                best_match = knowledge
        if best_match:
            layers = best_match.get("layers", {})
            text = layers.get("literal", "") or layers.get("metaphorical", "")
            if text:
                return PulseResponse(
                    text=text,
                    source="expansion:" + best_match.get("topic", ""),
                    confidence=0.7,
                    provenance=[_derived_tag("expansion", f"expanded knowledge: {best_match.get('topic', '')}")],
                    uncertainty=_build_uncertainty_for_unknown("расширенные знания — частичное совпадение"),
                )
        return None

    def respond_to(self, query):
        """Найти ответ в расширенных знаниях.

        M9: temporal-aware — если запрос содержит temporal intent,
        используется temporal chain через WorldEngine facade.
        """
        from pulse.layers import PulseResponse

        # M9: Check temporal intent first
        intent = self._detect_temporal_intent(query)
        if intent:
            temporal_resp = self._build_temporal_answer(query, intent)
            if temporal_resp is not None:
                return temporal_resp

        # Standard expansion path (unchanged behavior)
        return self._standard_respond(query)

    def get_context(self, query):
        """Получить контекст для LLM (расширенные знания + temporal).

        M9: включает temporal chain context для temporal queries.
        """
        q = query.lower()
        contexts = []

        # Standard expansion context
        for topic, knowledge in self._knowledge.items():
            if any(word in q for word in topic.split()):
                layers = knowledge.get("layers", {})
                cross_refs = knowledge.get("cross_references", [])
                patterns = knowledge.get("patterns", [])
                if layers:
                    contexts.append("[" + topic + "] " + (layers.get("literal", "") or ""))
                if cross_refs:
                    contexts.append("Связи: " + ", ".join(cross_refs[:3]))
                if patterns:
                    contexts.append("Паттерны: " + ", ".join(patterns[:2]))

        # M9: Temporal context enrichment — prepended so it survives the [:5] cutoff
        intent = self._detect_temporal_intent(query)
        temporal_lines = []
        if intent:
            from narrative_engine.world_engine import get_world_engine
            we = get_world_engine()
            te = self._temporal_engine or we.temporal_engine
            if te is not None:
                from narrative_engine.temporal.chain import ChainDirection
                try:
                    if intent in ("BACKWARD", "POSITION"):
                        chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
                        if chain and chain.nodes:
                            node_labels = [n.label for n in chain.nodes[:5]]
                            temporal_lines.append("[Temporal BACKWARD] " + " -> ".join(node_labels))
                    elif intent == "FORWARD":
                        chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.FORWARD)
                        if chain and chain.nodes:
                            node_labels = [n.label for n in chain.nodes[:5]]
                            temporal_lines.append("[Temporal FORWARD] " + " -> ".join(node_labels))
                    elif intent == "CONTEXT":
                        from narrative_engine.world_model import WorldModel
                        wm = WorldModel.load()
                        tctx = wm.get_temporal_context("arkaim_era")
                        if tctx:
                            node = tctx.get("temporal_node", {})
                            if node:
                                temporal_lines.append(
                                    "[Temporal CONTEXT] "
                                    + node.get("label", "Аркаим")
                                    + " — precision: "
                                    + node.get("precision", "RELATIVE")
                                )
                except Exception:
                    pass  # temporal context is optional

        # Prepend temporal lines before standard expansion context
        contexts = temporal_lines + contexts
        return "\n".join(contexts[:5])

    @property
    def summary(self):
        return "Расширенные знания из пайплайна Knowledge Expansion."

class ScreenplayLayer(BaseLayer):
    name = "screenplay"

    def __init__(self, genome: dict, retriever=None):
        super().__init__(genome, retriever)
        self._screenplay = self._load_screenplay()

    def _load_screenplay(self) -> dict:
        import json as _json
        from pathlib import Path as _Path
        search_paths = [
            _Path("core/KNOWLEDGE/screenplay_extracts.json"),
            config.KNOWLEDGE_DIR / "screenplay_extracts.json",
        ]
        here = _Path(__file__).parent.parent
        search_paths.append(here / "KNOWLEDGE" / "screenplay_extracts.json")
        for p in search_paths:
            if p.exists():
                try:
                    return _json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return {}

    def respond_to(self, query: str):
        if not self._screenplay:
            return None
        q = query.lower()
        kw = ["сценарий", "диалог", "камера", "кадр", "незнакомец", "велик", "славный", "пещера", "мизансцена", "пройвикс", "лин", "офицер", "генерал", "великус", "город", "обучение", "голос", "транс", "отлёт", "прощание", "самолёт", "политик", "репрессии"]
        if not any(x in q for x in kw):
            return None
        parts = []
        for d in self._screenplay.get("key_dialogues", []):
            pt = " ".join(d.get("participants", [])).lower()
            if any(w in q for w in pt.split()):
                parts.append("Диалог: " + str(d.get("participants", [])) + " — " + d.get("topic", ""))
                parts.append("«" + d.get("excerpt", "") + "»")
        for o in self._screenplay.get("oceania_officers", []):
            if o.get("name", "").lower() in q:
                parts.append(o["name"] + ": " + o.get("description", ""))
        if "незнакомец" in q:
            s = self._screenplay.get("the_stranger", "")
            if s:
                parts.append("Незнакомец: " + s)
        if any(w in q for w in ["обучение", "комната", "транс"]):
            room = self._screenplay.get("teaching_room", {})
            if room:
                parts.append("Комната: " + room.get("description", ""))
        if any(w in q for w in ["отлёт", "прощание", "самолёт"]):
            dep = self._screenplay.get("departure_scene", "")
            if dep:
                parts.append("Сцена отлёта: " + dep)
        if not parts:
            return None
        return PulseResponse(
            text="\n\n".join(parts),
            source="screenplay",
            confidence=0.85,
            provenance=[_canon_tag("screenplay", f"screenplay: {q[:50]}")],
        )

    @property
    def summary(self) -> str:
        if not self._screenplay:
            return "Сценарий не загружен"
        officers = len(self._screenplay.get("oceania_officers", []))
        dialogues = len(self._screenplay.get("key_dialogues", []))
        return f"Сценарий: {officers} персонажей, {dialogues} диалогов"


class WorldEngineLayer(BaseLayer):
    """
    Слой модели мира — отвечает на запросы об эпохах, локациях, технологиях,
    причинах и следствиях. Питается из WORLD_MODEL.json.
    """
    name = "world_engine"

    def __init__(self, genome: dict, retriever=None):
        super().__init__(genome, retriever)
        self._world_model = None
        self._load_world_model()

    def _load_world_model(self):
        import json
        from pathlib import Path
        # Search in multiple locations
        search_paths = [
            Path("core/CORE/narrative_engine/data/WORLD_MODEL.json"),
            Path("narrative_engine/data/WORLD_MODEL.json"),
        ]
        # Also try relative to this file
        here = Path(__file__).parent.parent
        search_paths.append(here / "narrative_engine" / "data" / "WORLD_MODEL.json")
        for p in search_paths:
            if p.exists():
                try:
                    self._world_model = json.loads(p.read_text(encoding="utf-8"))
                    return
                except Exception:
                    continue
        self._world_model = None

    def respond_to(self, query: str) -> Optional[PulseResponse]:
        if not self._world_model:
            return None
        q = query.lower()
        world_keywords = [
            "эпоха", "эры", "где происходит", "кто жил", "что существовало",
            "какие технологии", "цивилизации", "кали юга", "сати юга",
            "сатья юга", "трета юга", "двапара юга", "гиперборея",
            "локации", "города", "страны", "события", "история мира",
        ]
        if not any(kw in q for kw in world_keywords):
            return None
        context = self._build_query_context(q)
        if context:
            return PulseResponse(
                text=context,
                source="world_engine",
                confidence=0.85,
                provenance=[_derived_tag("world_model", f"world model: {q[:50]}")],
            )
        return None

    def _build_query_context(self, query: str) -> str:
        wm = self._world_model
        parts = []
        for ep in wm.get("epochs", []):
            if any(w in query for w in ep["name"].lower().split()):
                parts.append(f"Эпоха: {ep['name']} ({ep.get('name_ru', '')}) — {ep.get('description', '')}")
        for loc in wm.get("locations", []):
            if any(w in query for w in loc["name"].lower().split()):
                parts.append(f"Локация: {loc['name']} ({loc.get('name_ru', '')}) — {loc.get('description', '')}")
        for event in wm.get("canonical_events", [])[:5]:
            if any(w in query for w in event.get("title", "").lower().split()):
                parts.append(f"Событие: {event.get('title_ru', '')} — {event.get('description', '')}")
        return "\n".join(parts[:5]) if parts else ""

    def get_constraints_for(self, epoch_id: str = None, location_id: str = None) -> dict:
        if not self._world_model:
            return {}
        constraints = {"epochs": [], "locations": [], "events": [], "rules": []}
        if epoch_id:
            for ep in self._world_model.get("epochs", []):
                if ep["id"] == epoch_id:
                    constraints["epochs"].append(ep)
        if location_id:
            for loc in self._world_model.get("locations", []):
                if loc["id"] == location_id:
                    constraints["locations"].append(loc)
        constraints["events"] = self._world_model.get("canonical_events", [])
        constraints["rules"] = self._world_model.get("causal_rules", [])
        return constraints

    def reload_world_model(self):
        self._load_world_model()

    @property
    def summary(self) -> str:
        wm = self._world_model
        if not wm:
            return "Мир не загружен"
        epochs = len(wm.get("epochs", []))
        locations = len(wm.get("locations", []))
        events = len(wm.get("canonical_events", []))
        rules = len(wm.get("causal_rules", []))
        return f"Мир: {epochs} эпох, {locations} локаций, {events} событий, {rules} правил"

