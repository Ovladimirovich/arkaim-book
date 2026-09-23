"""
CharacterProfiler — глубинный профиль персонажей.
Извлекает из книги: ранг, роль, аффилиации, ключевые эпизоды, психологию.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

BASE = Path(__file__).resolve().parents[2]
GENOME_PATH = BASE / "GENOME" / "GENOME_v1.0.0.json"
BOOK_PATH = BASE / "SOURCE_OF_TRUTH" / "BOOK" / "КНИГА.md"


# Регулярные паттерны для извлечения структурированной информации
PATTERNS = {
    "rank": re.compile(
        r"(?:опытный\s+)?(военачальник|генерал|полководец|командир|офицер|лидер|глава|правитель|царь|князь|воин)",
        re.IGNORECASE,
    ),
    "role": re.compile(
        r"(?:был|являлся|стал|считался|был\s+известен\s+как|зарекомендовал\s+себя\s+как)\s+"
        r"([^\.]{3,60})",
        re.IGNORECASE,
    ),
    "affiliation": re.compile(
        r"(?:цивилизация|империя|держава|страна|государство|народ|общество|организация)\s+"
        r"([А-ЯЁ][а-яё]+(?:[\s-][А-ЯЁ][а-яё]+)*)",
        re.IGNORECASE,
    ),
    "achievement": re.compile(
        r"(?:достиг|получил|завоевал|создал|основал|постиг|овладел|развил|познал|прошёл)\s+"
        r"([^\.]{10,100})",
        re.IGNORECASE,
    ),
    "psychology": re.compile(
        r"(?:чувствовал|ощущал|понимал|осознавал|стремился|желал|мечтал|верил|знал|любил)\s+"
        r"([^\.]{10,80})",
        re.IGNORECASE,
    ),
}


class CharacterProfile:
    """Профиль одного персонажа."""

    def __init__(self, name: str, genome_entry: Optional[Dict] = None):
        self.name = name
        self.genome_id = (genome_entry or {}).get("id", "")
        self.aliases: List[str] = (genome_entry or {}).get("aliases", [])
        self.archetype: str = (genome_entry or {}).get("archetype", "")
        self.genome_description: str = (genome_entry or {}).get("description", "")

        # Извлекаемые поля
        self.rank: str = ""
        self.role: str = ""
        self.affiliations: List[str] = []
        self.achievements: List[str] = []
        self.psychology_traits: List[str] = []
        self.key_episodes: List[Dict] = []
        self.mention_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "genome_id": self.genome_id,
            "aliases": self.aliases,
            "archetype": self.archetype,
            "rank": self.rank,
            "role": self.role,
            "affiliations": self.affiliations,
            "achievements": self.achievements,
            "psychology_traits": self.psychology_traits,
            "key_episodes": self.key_episodes,
            "mention_count": self.mention_count,
        }


class CharacterProfiler:
    def __init__(self, book_path: Optional[Path] = None, genome_path: Optional[Path] = None):
        self.book_path = book_path or BOOK_PATH
        self.genome_path = genome_path or GENOME_PATH
        self._book_text = ""
        self._genome = {}
        self._load()

    def _load(self):
        if self.book_path.exists():
            self._book_text = self.book_path.read_text(encoding="utf-8")
        if self.genome_path.exists():
            self._genome = json.loads(self.genome_path.read_text(encoding="utf-8"))

    def _get_characters_from_genome(self) -> List[Dict]:
        """Извлекает всех персонажей из генома."""
        chars = self._genome.get("modules", {}).get("characters", [])
        # Дедикаплицируем: группируем по каноническому имени
        from intelligence.nameresolver import NameResolver
        nr = NameResolver()
        seen = set()
        result = []
        for c in chars:
            canonical = nr.resolve(c["name"])
            if canonical not in seen:
                seen.add(canonical)
                # Собираем все алиасы
                all_aliases = set(c.get("aliases", []))
                for c2 in chars:
                    if nr.resolve(c2["name"]) == canonical:
                        all_aliases.update(c2.get("aliases", []))
                        # Если описание длиннее — берём его
                        if len(c2.get("description", "")) > len(c.get("description", "")):
                            c = c2
                c["aliases"] = list(all_aliases)
                result.append(c)
        return result

    def _extract_mentions(self, text: str, names: Set[str]) -> List[int]:
        """Находит все позиции упоминаний любого из имён."""
        positions = []
        for name in names:
            start = 0
            while True:
                idx = text.find(name, start)
                if idx == -1:
                    break
                positions.append(idx)
                start = idx + 1
        return sorted(positions)

    def _extract_context(self, text: str, pos: int, radius: int = 150) -> str:
        """Извлекает контекст вокруг позиции."""
        start = max(0, pos - radius)
        end = min(len(text), pos + radius)
        return text[start:end].replace("\n", " ")

    def _extract_episode(self, text: str, pos: int, radius: int = 600) -> Dict:
        """Извлекает эпизод вокруг упоминания персонажа."""
        # Ищем границы предложения
        ctx_start = max(0, pos - radius)
        ctx_end = min(len(text), pos + radius)
        snippet = text[ctx_start:ctx_end].replace("\n", " ")

        # Пытаемся найти начало предложения
        sentence_start = snippet.rfind(". ", 0, radius)
        sentence_end = snippet.find(". ", radius)
        if sentence_start == -1:
            sentence_start = 0
        else:
            sentence_start = sentence_start + 2  # skip ". "
        if sentence_end == -1:
            sentence_end = len(snippet)

        episode_text = snippet[sentence_start:sentence_end + 1].strip()
        return {
            "position": pos,
            "text": episode_text[:300],
            "full_text": episode_text[:600],
        }

    def _analyze_rank(self, text: str) -> str:
        """Определяет ранг/звание."""
        mentions = PATTERNS["rank"].findall(text)
        if mentions:
            return mentions[0].capitalize()
        return ""

    def _analyze_role(self, text: str) -> str:
        """Определяет роль."""
        matches = PATTERNS["role"].findall(text)
        if matches:
            return matches[0].strip().capitalize()
        return ""

    def _analyze_affiliations(self, text: str) -> List[str]:
        """Определяет принадлежность к группам/цивилизациям."""
        matches = PATTERNS["affiliation"].findall(text)
        return list(set(m.strip() for m in matches))

    def _analyze_achievements(self, text: str) -> List[str]:
        """Извлекает достижения."""
        matches = PATTERNS["achievement"].findall(text)
        return [m.strip() for m in matches[:10]]

    def _analyze_psychology(self, text: str) -> List[str]:
        """Извлекает психологические черты."""
        matches = PATTERNS["psychology"].findall(text)
        return [m.strip() for m in matches[:10]]

    def profile_character(self, genome_entry: Dict) -> CharacterProfile:
        """Строит глубинный профиль персонажа."""
        from intelligence.nameresolver import NameResolver
        nr = NameResolver()

        name = genome_entry["name"]
        canonical = nr.resolve(name)
        profile = CharacterProfile(canonical, genome_entry)

        # Все имена для поиска
        search_names = {canonical}
        for a in genome_entry.get("aliases", []):
            search_names.add(a)
        # Добавляем все алиасы из NameResolver
        search_names = search_names.union(nr.get_all_aliases(canonical))

        # Собираем весь текст, где упоминается персонаж
        mentions = self._extract_mentions(self._book_text, search_names)
        profile.mention_count = len(mentions)

        # Если упоминаний мало — ищем по тексту всей книги
        search_text = self._book_text
        if mentions:
            # Собираем контекст вокруг всех упоминаний
            contexts = []
            for pos in mentions:
                ctx = self._extract_context(search_text, pos)
                contexts.append(ctx)
                # Извлекаем ключевые эпизоды (первые 5)
                if len(profile.key_episodes) < 5:
                    episode = self._extract_episode(search_text, pos)
                    profile.key_episodes.append(episode)
            combined_text = " ".join(contexts)
        else:
            combined_text = search_text  # fallback: вся книга

        # Извлекаем структурированные поля
        profile.rank = self._analyze_rank(combined_text)
        profile.role = self._analyze_role(combined_text)
        profile.affiliations = self._analyze_affiliations(combined_text)
        profile.achievements = self._analyze_achievements(combined_text)
        profile.psychology_traits = self._analyze_psychology(combined_text)

        return profile

    def profile_all(self) -> Dict[str, CharacterProfile]:
        """Профилирует всех персонажей из генома."""
        chars = self._get_characters_from_genome()
        profiles = {}
        for c in chars:
            p = self.profile_character(c)
            profiles[p.name] = p
        return profiles

    def save_profiles(self, output_path: Optional[Path] = None):
        """Сохраняет профили в KNOWLEDGE/character_profiles.json."""
        profiles = self.profile_all()
        data = {name: p.to_dict() for name, p in profiles.items()}
        path = output_path or (BASE / "KNOWLEDGE" / "character_profiles.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def get_stats(self) -> Dict:
        profiles = self.profile_all()
        with_rank = sum(1 for p in profiles.values() if p.rank)
        with_aff = sum(1 for p in profiles.values() if p.affiliations)
        with_psy = sum(1 for p in profiles.values() if p.psychology_traits)
        total_eps = sum(len(p.key_episodes) for p in profiles.values())
        return {
            "total_characters": len(profiles),
            "with_rank": with_rank,
            "with_affiliations": with_aff,
            "with_psychology": with_psy,
            "total_key_episodes": total_eps,
            "most_mentioned": max(profiles.values(), key=lambda p: p.mention_count).name,
            "top_mention_count": max(p.mention_count for p in profiles.values()),
        }
