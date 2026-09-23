"""
ReaderMemory вЂ” РєРЅРёРіР° РїРѕРјРЅРёС‚ РєР°Р¶РґРѕРіРѕ С‡РёС‚Р°С‚РµР»СЏ.

РџСЂРѕС„РёР»СЊ С‡РёС‚Р°С‚РµР»СЏ, РёСЃС‚РѕСЂРёСЏ С‚РµРј, РіР»СѓР±РёРЅР° РїРѕРіСЂСѓР¶РµРЅРёСЏ.
РџРѕР·РІРѕР»СЏРµС‚ РєРЅРёРіРµ РѕС‚РІРµС‡Р°С‚СЊ В«СЂР°СЃСЃРєР°Р¶Рё РїРѕРґСЂРѕР±РЅРµРµВ» Р±РµР· РїРµСЂРµРґР°С‡Рё РєРѕРЅС‚РµРєСЃС‚Р°.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from core.database import get_db_manager
from core.memory.reader_profile import (
    ReaderProfile as EnhancedReaderProfile,
    ReaderLevel,
    LearningStyle,
    adapt_response,
    AdaptiveResponse,
)


DB_DIR = Path(__file__).resolve().parent.parent / "memory" / "data"
DB_PATH = DB_DIR / "readers.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@dataclass
class TopicMemory:
    name: str
    depth: float = 0.0          # 0.0вЂ“1.0 РєР°Рє РіР»СѓР±РѕРєРѕ СѓС€Р»Рё
    questions_count: int = 0
    last_asked: str = ""         # ISO datetime
    pulse_source: str = ""       # knowledge:character, meaning:values, ...


@dataclass
class ReaderProfile:
    reader_id: str
    display_name: str = ""
    provider: str = ""
    first_seen: str = ""
    last_seen: str = ""
    questions_total: int = 0
    topics: dict[str, TopicMemory] = field(default_factory=dict)
    last_topic: str = ""          # РїРѕСЃР»РµРґРЅСЏСЏ С‚РµРјР° РґР»СЏ В«СЂР°СЃСЃРєР°Р¶Рё РїРѕРґСЂРѕР±РЅРµРµВ»
    last_question: str = ""
    last_answer: str = ""
    conversation_count: int = 0


class ReaderMemoryStore:
    """
    РҐСЂР°РЅРёР»РёС‰Рµ РїР°РјСЏС‚Рё С‡РёС‚Р°С‚РµР»РµР№.

    РљР°Р¶РґС‹Р№ С‡РёС‚Р°С‚РµР»СЊ РёРјРµРµС‚ РїСЂРѕС„РёР»СЊ СЃ РёСЃС‚РѕСЂРёРµР№ С‚РµРј.
    РљРЅРёРіР° В«РїРѕРјРЅРёС‚В», Рѕ С‡С‘Рј СЃ РЅРёРј РіРѕРІРѕСЂРёР»Р°.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = str(db_path or DB_PATH)
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> None:
        if self._conn is not None:
            return
        db_manager = get_db_manager()
        self._conn = await db_manager.get_connection(
            db_path=self._db_path,
            migrations_dir=MIGRATIONS_DIR,
        )

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
        self._conn = None

    # в”Ђв”Ђ РџСЂРѕС„РёР»СЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def get_or_create(self, reader_id: str, display_name: str = "", provider: str = "") -> ReaderProfile:
        """РџРѕР»СѓС‡РёС‚СЊ РїСЂРѕС„РёР»СЊ С‡РёС‚Р°С‚РµР»СЏ РёР»Рё СЃРѕР·РґР°С‚СЊ РЅРѕРІС‹Р№."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT reader_id, display_name, provider, first_seen, last_seen, "
            "questions_total, last_topic, last_question, last_answer, conversation_count "
            "FROM readers WHERE reader_id = ?",
            (reader_id,),
        )
        row = await cursor.fetchone()

        now = datetime.now(tz=timezone.utc).isoformat()

        if not row:
            await self._conn.execute(
                "INSERT INTO readers (reader_id, display_name, provider, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                (reader_id, display_name, provider, now, now),
            )
            await self._conn.commit()
        else:
            display_name = display_name or row["display_name"]
            provider = provider or row["provider"]
            await self._conn.execute(
                "UPDATE readers SET display_name = COALESCE(NULLIF(?, ''), display_name), last_seen = ?, provider = COALESCE(NULLIF(?, ''), provider) WHERE reader_id = ?",
                (display_name, now, provider, reader_id),
            )
            await self._conn.commit()

        return await self._load_profile(reader_id)

    def _decay_depth(self, depth: float, last_asked: str) -> float:
        """Р—Р°С‚СѓС…Р°РЅРёРµ РіР»СѓР±РёРЅС‹ С‚РµРјС‹ РїРѕ РІСЂРµРјРµРЅРё."""
        if not last_asked or depth <= 0:
            return depth
        try:
            last_dt = datetime.fromisoformat(last_asked)
            now = datetime.now(tz=timezone.utc)
            days = (now - last_dt).days
            if days > 30:
                return depth * 0.2
            elif days > 7:
                return depth * 0.5
            return depth
        except Exception:
            return depth

    async def _load_profile(self, reader_id: str) -> ReaderProfile | None:
        cursor = await self._conn.execute(
            "SELECT * FROM readers WHERE reader_id = ?", (reader_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        profile = ReaderProfile(
            reader_id=row["reader_id"],
            display_name=row["display_name"] or "",
            provider=row["provider"] or "",
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            questions_total=row["questions_total"],
            last_topic=row["last_topic"] or "",
            last_question=row["last_question"] or "",
            last_answer=row["last_answer"] or "",
            conversation_count=row["conversation_count"],
        )

        # Р—Р°РіСЂСѓР·РёС‚СЊ С‚РµРјС‹ (СЃ Р·Р°С‚СѓС…Р°РЅРёРµРј РіР»СѓР±РёРЅС‹)
        tc = await self._conn.execute(
            "SELECT name, depth, questions_count, last_asked, pulse_source FROM topics WHERE reader_id = ? ORDER BY depth DESC",
            (reader_id,),
        )
        for trow in await tc.fetchall():
            # Р—Р°С‚СѓС…Р°РЅРёРµ РіР»СѓР±РёРЅС‹ РїРѕ РІСЂРµРјРµРЅРё
            decayed_depth = self._decay_depth(trow["depth"], trow["last_asked"] or "")
            profile.topics[trow["name"]] = TopicMemory(
                name=trow["name"],
                depth=decayed_depth,
                questions_count=trow["questions_count"],
                last_asked=trow["last_asked"] or "",
                pulse_source=trow["pulse_source"] or "",
            )

        return profile

    # в”Ђв”Ђ Р’Р·Р°РёРјРѕРґРµР№СЃС‚РІРёРµ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def record_interaction(
        self,
        reader_id: str,
        question: str,
        answer: str,
        topic: str = "",
        pulse_source: str = "",
    ):
        """Р—Р°РїРёСЃР°С‚СЊ РѕРґРЅРѕ РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёРµ: РІРѕРїСЂРѕСЃ-РѕС‚РІРµС‚."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()

        # РћР±РЅРѕРІРёС‚СЊ РїСЂРѕС„РёР»СЊ
        await self._conn.execute(
            "UPDATE readers SET questions_total = questions_total + 1, "
            "last_seen = ?, last_topic = ?, last_question = ?, "
            "last_answer = ?, conversation_count = conversation_count + 1 "
            "WHERE reader_id = ?",
            (now, topic, question, answer, reader_id),
        )

        # РћР±РЅРѕРІРёС‚СЊ РёР»Рё СЃРѕР·РґР°С‚СЊ С‚РµРјСѓ
        if topic:
            existing = await self._conn.execute(
                "SELECT depth, questions_count FROM topics WHERE reader_id = ? AND name = ?",
                (reader_id, topic),
            )
            row = await existing.fetchone()
            if row:
                new_depth = min(1.0, row["depth"] + 0.1)
                await self._conn.execute(
                    "UPDATE topics SET depth = ?, questions_count = questions_count + 1, "
                    "last_asked = ?, pulse_source = COALESCE(NULLIF(?, ''), pulse_source) "
                    "WHERE reader_id = ? AND name = ?",
                    (new_depth, now, pulse_source, reader_id, topic),
                )
            else:
                await self._conn.execute(
                    "INSERT INTO topics (reader_id, name, depth, questions_count, last_asked, pulse_source) "
                    "VALUES (?, ?, ?, 1, ?, ?)",
                    (reader_id, topic, 0.3, now, pulse_source),
                )

        await self._conn.commit()

    # в”Ђв”Ђ В«Р Р°СЃСЃРєР°Р¶Рё РїРѕРґСЂРѕР±РЅРµРµВ» в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def get_last_topic_context(self, reader_id: str) -> dict:
        """
        РџРѕРЅСЏС‚СЊ, Рѕ С‡С‘Рј С‡РёС‚Р°С‚РµР»СЊ СЃРїСЂР°С€РёРІР°Р» РІ РїСЂРѕС€Р»С‹Р№ СЂР°Р·.
        Р’РѕР·РІСЂР°С‰Р°РµС‚ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ В«СЂР°СЃСЃРєР°Р¶Рё РїРѕРґСЂРѕР±РЅРµРµВ».
        """
        profile = await self._load_profile(reader_id)
        if not profile or not profile.last_topic:
            return {}

        topic = profile.topics.get(profile.last_topic)
        return {
            "topic": profile.last_topic,
            "depth": topic.depth if topic else 0.0,
            "last_question": profile.last_question,
            "last_answer": profile.last_answer,
            "source": topic.pulse_source if topic else "",
            "questions_count": topic.questions_count if topic else 0,
        }

    # в”Ђв”Ђ Р’РёР·СѓР°Р»СЊРЅР°СЏ РїР°РјСЏС‚СЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def save_visual_memory(
        self,
        reader_id: str,
        scene_id: str,
        image_hash: str,
        visual_spec_hash: str,
        character_id: str | None = None,
    ):
        """РЎРѕС…СЂР°РЅРёС‚СЊ Р·Р°РїСЂРѕСЃ РІРёР·СѓР°Р»РёР·Р°С†РёРё."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cached_until = (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat()

        await self._conn.execute(
            """
            INSERT OR REPLACE INTO visual_memory
                (reader_id, scene_id, character_id, image_hash, visual_spec_hash, created_at, cached_until)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (reader_id, scene_id, character_id, image_hash, visual_spec_hash, now, cached_until),
        )
        await self._conn.commit()

    async def get_visual_memory(self, reader_id: str, scene_id: str, character_id: str | None = None) -> dict | None:
        """РџРѕР»СѓС‡РёС‚СЊ СЃРѕС…СЂР°РЅС‘РЅРЅС‹Р№ РІРёР·СѓР°Р», РµСЃР»Рё РѕРЅ РµС‰С‘ Р°РєС‚СѓР°Р»РµРЅ."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()

        query = """
            SELECT reader_id, scene_id, character_id, image_hash, visual_spec_hash, created_at, cached_until
            FROM visual_memory
            WHERE reader_id = ? AND scene_id = ? AND cached_until > ?
        """
        params: list = [reader_id, scene_id, now]
        if character_id is not None:
            query += " AND character_id = ?"
            params.append(character_id)
        else:
            query += " AND character_id IS NULL"

        cursor = await self._conn.execute(query, tuple(params))
        row = await cursor.fetchone()
        return dict(row) if row else None


    # ── Расширенный профиль ──────────────────────────

    async def get_enhanced_profile(self, reader_id: str) -> EnhancedReaderProfile | None:
        """Получить расширенный профиль читателя с уровнем и стилем."""
        base_profile = await self._load_profile(reader_id)
        if not base_profile:
            return None

        enhanced = EnhancedReaderProfile(
            reader_id=base_profile.reader_id,
            display_name=base_profile.display_name,
            provider=base_profile.provider,
            first_seen=base_profile.first_seen,
            last_seen=base_profile.last_seen,
            questions_total=base_profile.questions_total,
            conversation_count=base_profile.conversation_count,
            last_topic=base_profile.last_topic,
            last_question=base_profile.last_question,
            topics_explored=len(base_profile.topics),
        )

        # Рассчитать уровень
        enhanced.calculate_level()

        # Определить стиль обучения
        enhanced.detect_learning_style(base_profile.topics)

        # Определить интересы (топ-3 темы по глубине)
        sorted_topics = sorted(base_profile.topics.values(), key=lambda t: t.depth, reverse=True)
        enhanced.primary_interests = [t.name for t in sorted_topics[:3]]

        # Рассчитать вовлечённость
        enhanced.engagement_score = self._calculate_engagement(enhanced)

        # Сгенерировать рекомендации
        enhanced.recommended_topics = self._generate_recommendations(enhanced)

        return enhanced

    def _calculate_engagement(self, profile: EnhancedReaderProfile) -> float:
        """Рассчитать score вовлечённости (0-100)."""
        score = 0

        # По количеству вопросов
        if profile.questions_total >= 50:
            score += 30
        elif profile.questions_total >= 20:
            score += 20
        elif profile.questions_total >= 5:
            score += 10

        # По количеству тем
        if profile.topics_explored >= 20:
            score += 30
        elif profile.topics_explored >= 10:
            score += 20
        elif profile.topics_explored >= 3:
            score += 10

        # По частоте сессий (упрощённо)
        if profile.conversation_count >= 10:
            score += 20
        elif profile.conversation_count >= 3:
            score += 10

        return min(100, score)

    def _generate_recommendations(self, profile: EnhancedReaderProfile) -> list[str]:
        """Сгенерировать рекомендации на основе профиля."""
        recommendations = []

        # Рекомендовать темы, которые ещё не изучены
        all_topics = [
            "Гиперборея", "Аркаим", "Архат", "Учитель", "Велик",
            "Звукознание", "Кали Юга", "Иерархия Света", "Духовное пробуждение",
            "Энергетика мест", "Передача знаний", "Эмиграция Гипербореев",
        ]

        explored = set(profile.primary_interests)
        for topic in all_topics:
            if topic not in explored and len(recommendations) < 3:
                recommendations.append(topic)

        return recommendations

    async def get_adaptive_context(self, reader_id: str) -> str:
        """Получить адаптивный контекст для LLM на основе профиля."""
        enhanced = await self.get_enhanced_profile(reader_id)
        if not enhanced:
            return ""

        return enhanced.get_context_for_llm()

    async def build_reader_context(self, reader_id: str) -> str:
        """
        РџРѕСЃС‚СЂРѕРёС‚СЊ С‚РµРєСЃС‚РѕРІС‹Р№ РєРѕРЅС‚РµРєСЃС‚ С‡РёС‚Р°С‚РµР»СЏ РґР»СЏ Pulse/Voice.
        В«Р­С‚РѕС‚ С‡РёС‚Р°С‚РµР»СЊ СѓР¶Рµ СЃРїСЂР°С€РёРІР°Р» Рѕ Р“РёРїРµСЂР±РѕСЂРµРµ. РћС‚РІРµС‚РёС‚СЊ РіР»СѓР±Р¶Рµ.В»
        """
        profile = await self._load_profile(reader_id)
        if not profile:
            return ""

        parts = [f"Р§РёС‚Р°С‚РµР»СЊ Р·Р°РґР°Р» {profile.questions_total} РІРѕРїСЂРѕСЃРѕРІ."]

        if profile.topics:
            explored = sorted(profile.topics.values(), key=lambda t: t.depth, reverse=True)[:5]
            topic_desc = []
            for t in explored:
                level = "РїРѕРІРµСЂС…РЅРѕСЃС‚РЅРѕ" if t.depth < 0.4 else "РІ РґРµС‚Р°Р»СЏС…" if t.depth > 0.7 else "СѓРјРµСЂРµРЅРЅРѕ"
                topic_desc.append(f"В«{t.name}В» ({level}, {t.questions_count} РІРѕРїСЂРѕСЃРѕРІ)")
            parts.append("Р Р°РЅРµРµ РѕР±СЃСѓР¶РґР°Р»: " + ", ".join(topic_desc))

        if profile.last_topic:
            parts.append(f"РџРѕСЃР»РµРґРЅСЏСЏ С‚РµРјР°: В«{profile.last_topic}В»")
            tc = profile.topics.get(profile.last_topic)
            if tc and tc.depth < 1.0:
                parts.append("РњРѕР¶РЅРѕ СѓРіР»СѓР±РёС‚СЊ СЌС‚Сѓ С‚РµРјСѓ.")

        return "\n".join(parts)

    # в”Ђв”Ђ РћС‡РёСЃС‚РєР° в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def prune_old_conversations(self, days: int = 30) -> dict:
        """РЈРґР°Р»РёС‚СЊ РґРёР°Р»РѕРіРё СЃС‚Р°СЂС€Рµ N РґРЅРµР№."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "DELETE FROM conversations WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await self._conn.commit()
        return {"deleted": cursor.rowcount}

    # в”Ђв”Ђ РЎС‚Р°С‚РёСЃС‚РёРєР° в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def get_stats(self) -> dict:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT (SELECT COUNT(*) FROM readers) as readers, "
            "(SELECT COUNT(*) FROM topics) as topics, "
            "(SELECT COALESCE(SUM(questions_total), 0) FROM readers) as questions"
        )
        row = await cursor.fetchone()
        return {
            "total_readers": row["readers"],
            "total_topics": row["topics"],
            "total_questions": row["questions"],
        }

    # в”Ђв”Ђ РџСЂРѕРіСЂРµСЃСЃ С‡С‚РµРЅРёСЏ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    async def record_reading(
        self,
        reader_id: str,
        chapter_id: str,
        chapter_index: int,
        read_seconds: int = 0,
        scroll_percent: float = 0.0,
        completed: bool = False,
    ):
        """Р—Р°РїРёСЃР°С‚СЊ СЃРѕР±С‹С‚РёРµ С‡С‚РµРЅРёСЏ РіР»Р°РІС‹."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()

        existing = await self._conn.execute(
            "SELECT id, read_seconds FROM reading_progress WHERE reader_id = ? AND chapter_id = ?",
            (reader_id, chapter_id),
        )
        row = await existing.fetchone()

        if row:
            await self._conn.execute(
                "UPDATE reading_progress SET last_read_at = ?, "
                "read_seconds = read_seconds + ?, "
                "scroll_percent = MAX(scroll_percent, ?), "
                "completed = MAX(completed, ?) "
                "WHERE reader_id = ? AND chapter_id = ?",
                (now, read_seconds, scroll_percent, int(completed), reader_id, chapter_id),
            )
        else:
            await self._conn.execute(
                "INSERT INTO reading_progress "
                "(reader_id, chapter_id, chapter_index, first_read_at, last_read_at, read_seconds, completed, scroll_percent) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (reader_id, chapter_id, chapter_index, now, now, read_seconds, int(completed), scroll_percent),
            )

        await self._conn.commit()

    async def get_reading_progress(self, reader_id: str) -> list[dict]:
        """РџРѕР»СѓС‡РёС‚СЊ РїСЂРѕРіСЂРµСЃСЃ С‡С‚РµРЅРёСЏ РІСЃРµС… РіР»Р°РІ."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT chapter_id, chapter_index, first_read_at, last_read_at, "
            "read_seconds, completed, scroll_percent "
            "FROM reading_progress WHERE reader_id = ? ORDER BY chapter_index",
            (reader_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "chapter_id": r["chapter_id"],
                "chapter_index": r["chapter_index"],
                "first_read_at": r["first_read_at"],
                "last_read_at": r["last_read_at"],
                "read_seconds": r["read_seconds"],
                "completed": bool(r["completed"]),
                "scroll_percent": r["scroll_percent"],
            }
            for r in rows
        ]

    async def get_last_position(self, reader_id: str) -> dict | None:
        """РџРѕР»СѓС‡РёС‚СЊ РїРѕСЃР»РµРґРЅСЋСЋ РїРѕР·РёС†РёСЋ С‡С‚РµРЅРёСЏ (РґР»СЏ В«РїСЂРѕРґРѕР»Р¶РёС‚СЊВ»)."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT chapter_id, chapter_index, scroll_percent, last_read_at "
            "FROM reading_progress WHERE reader_id = ? "
            "ORDER BY last_read_at DESC LIMIT 1",
            (reader_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "chapter_id": row["chapter_id"],
            "chapter_index": row["chapter_index"],
            "scroll_percent": row["scroll_percent"],
            "last_read_at": row["last_read_at"],
        }

    async def get_reading_stats(self, reader_id: str) -> dict:
        """РЎС‚Р°С‚РёСЃС‚РёРєР° С‡С‚РµРЅРёСЏ."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed, "
            "COALESCE(SUM(read_seconds), 0) as total_seconds "
            "FROM reading_progress WHERE reader_id = ?",
            (reader_id,),
        )
        row = await cursor.fetchone()
        return {
            "chapters_started": row["total"] or 0,
            "chapters_completed": row["completed"] or 0,
            "total_seconds": row["total_seconds"] or 0,
        }
