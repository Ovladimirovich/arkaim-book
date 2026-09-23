"""
ReaderProfile — расширенный профиль читателя.

Хранит не только историю вопросов, но и:
- Уровень понимания (novice, intermediate, advanced, expert)
- Интересы и предпочтения
- Стиль обучения (визуальный, текстовый, практический)
- Уровень вовлечённости
- Рекомендации по дальнейшему чтению
"""
from dataclasses import dataclass, field
from enum import Enum


class ReaderLevel(str, Enum):
    """Уровень понимания читателя."""
    NOVICE = "novice"           # Новичок — первые вопросы
    INTERMEDIATE = "intermediate"  # Средний — задаёт уточнения
    ADVANCED = "advanced"       # Продвинутый — глубокие вопросы
    EXPERT = "expert"           # Эксперт — сравнения, критический анализ


class LearningStyle(str, Enum):
    """Стиль обучения читателя."""
    VISUAL = "visual"           # Любит картинки, схемы, карты
    TEXTUAL = "textual"         # Любит текст, цитаты, объяснения
    PRACTICAL = "practical"     # Любит примеры, практики, упражнения
    PHILOSOPHICAL = "philosophical"  # Любит смыслы, связи, глубину
    HISTORICAL = "historical"   # Любит факты, даты, археологию


@dataclass
class ReaderProfile:
    """Расширенный профиль читателя."""
    reader_id: str
    display_name: str = ""
    provider: str = ""
    first_seen: str = ""
    last_seen: str = ""
    questions_total: int = 0
    conversation_count: int = 0

    # Уровень понимания
    level: ReaderLevel = ReaderLevel.NOVICE
    level_score: float = 0.0  # 0-100, автоматически рассчитывается

    # Интересы
    primary_interests: list[str] = field(default_factory=list)  # Топ-3 темы
    learning_style: LearningStyle = LearningStyle.TEXTUAL

    # Вовлечённость
    engagement_score: float = 0.0  # 0-100
    session_frequency: float = 0.0  # Сессий в неделю
    avg_session_length: float = 0.0  # Средняя длина сессии (вопросов)

    # История
    last_topic: str = ""
    last_question: str = ""
    topics_explored: int = 0  # Количество уникальных тем
    deep_dives: int = 0       # Количество «расскажи подробнее»

    # Рекомендации
    recommended_topics: list[str] = field(default_factory=list)
    reading_path: list[str] = field(default_factory=list)  # Рекомендуемый путь

    def calculate_level(self) -> ReaderLevel:
        """Автоматически рассчитать уровень на основе активности."""
        score = 0

        # По количеству вопросов
        if self.questions_total >= 50:
            score += 30
        elif self.questions_total >= 20:
            score += 20
        elif self.questions_total >= 5:
            score += 10

        # По количеству тем
        if self.topics_explored >= 20:
            score += 30
        elif self.topics_explored >= 10:
            score += 20
        elif self.topics_explored >= 3:
            score += 10

        # По глубине вопросов
        if self.deep_dives >= 10:
            score += 20
        elif self.deep_dives >= 3:
            score += 10

        # По частоте сессий
        if self.session_frequency >= 3:
            score += 20
        elif self.session_frequency >= 1:
            score += 10

        self.level_score = min(100, score)

        if score >= 70:
            self.level = ReaderLevel.EXPERT
        elif score >= 40:
            self.level = ReaderLevel.ADVANCED
        elif score >= 15:
            self.level = ReaderLevel.INTERMEDIATE
        else:
            self.level = ReaderLevel.NOVICE

        return self.level

    def detect_learning_style(self, topics: dict) -> LearningStyle:
        """Определить стиль обучения по интересам читателя."""
        style_scores = {
            LearningStyle.VISUAL: 0,
            LearningStyle.TEXTUAL: 0,
            LearningStyle.PRACTICAL: 0,
            LearningStyle.PHILOSOPHICAL: 0,
            LearningStyle.HISTORICAL: 0,
        }

        # Карта тем → стили
        style_map = {
            "визуал": LearningStyle.VISUAL,
            "символ": LearningStyle.VISUAL,
            "архетип": LearningStyle.VISUAL,
            "цитат": LearningStyle.TEXTUAL,
            "текст": LearningStyle.TEXTUAL,
            "язык": LearningStyle.TEXTUAL,
            "практи": LearningStyle.PRACTICAL,
            "ритуал": LearningStyle.PRACTICAL,
            "звукознани": LearningStyle.PRACTICAL,
            "философи": LearningStyle.PHILOSOPHICAL,
            "смысл": LearningStyle.PHILOSOPHICAL,
            "мисси": LearningStyle.PHILOSOPHICAL,
            "истори": LearningStyle.HISTORICAL,
            "археологи": LearningStyle.HISTORICAL,
            "дат": LearningStyle.HISTORICAL,
        }

        for topic_name, topic_data in topics.items():
            depth = topic_data.depth if hasattr(topic_data, 'depth') else 0
            for keyword, style in style_map.items():
                if keyword in topic_name.lower():
                    style_scores[style] += depth

        # Выбрать стиль с максимальным.score
        if any(style_scores.values()):
            self.learning_style = max(style_scores, key=style_scores.get)

        return self.learning_style

    def get_context_for_llm(self) -> str:
        """Получить контекст читателя для LLM."""
        parts = []

        parts.append(f"Читатель: {self.display_name or 'Незнакомец'}")
        parts.append(f"Уровень: {self.level.value} ({self.level_score:.0f}/100)")
        parts.append(f"Интересы: {', '.join(self.primary_interests[:3]) or 'не определены'}")
        parts.append(f"Стиль: {self.learning_style.value}")
        parts.append(f"Вовлечённость: {self.engagement_score:.0f}/100")
        parts.append(f"Вопросов: {self.questions_total}, Тем изучено: {self.topics_explored}")

        if self.recommended_topics:
            parts.append(f"Рекомендации: {', '.join(self.recommended_topics[:3])}")

        return "\n".join(parts)


@dataclass
class AdaptiveResponse:
    """Адаптивный ответ,調整ированный под читателя."""
    text: str
    level: ReaderLevel
    style: LearningStyle
    adaptations: list[str] = field(default_factory=list)  # Что было адаптировано


def adapt_response(
    base_response: str,
    profile: ReaderProfile,
    topic: str = "",
) -> AdaptiveResponse:
    """
    Адаптировать ответ под профиль читателя.

    - Novice → простой язык, примеры, без терминов
    - Intermediate → больше деталей, связей
    - Advanced → глубокий анализ, сравнения
    - Expert → критический взгляд, отсылки к первоисточникам
    """
    adaptations = []
    adapted = base_response

    # Адаптация по уровню
    if profile.level == ReaderLevel.NOVICE:
        # Упрощаем язык
        adapted = _simplify_language(adapted)
        adaptations.append("упрощён язык")
        # Добавляем контекст
        if topic:
            adapted = f"Давай разберём тему «{topic}» по порядку.\n\n{adapted}"
            adaptations.append("добавлен контекст")

    elif profile.level == ReaderLevel.INTERMEDIATE:
        # Добавляем связи
        if profile.primary_interests:
            related = [t for t in profile.primary_interests if t != topic][:2]
            if related:
                adapted += f"\n\nСвязанные темы для изучения: {', '.join(related)}"
                adaptations.append("добавлены связи")

    elif profile.level == ReaderLevel.ADVANCED:
        # Добавляем глубину
        adapted += "\n\n💡 Для глубокого понимания обрати внимание на связь с другими темами книги."
        adaptations.append("добавлена глубина")

    elif profile.level == ReaderLevel.EXPERT:
        # Критический взгляд
        adapted += "\n\n🔍 Стоит отметить: это один из взглядов на тему. В книге есть и другие интерпретации."
        adaptations.append("добавлен критический взгляд")

    # Адаптация по стилю обучения
    if profile.learning_style == LearningStyle.VISUAL:
        adapted += "\n\n🎨 Рекомендую посмотреть визуальные описания этой темы в разделе «Визуал»."
        adaptations.append("визуальная рекомендация")

    elif profile.learning_style == LearningStyle.PRACTICAL:
        adapted += "\n\n🛠️ Попробуй применить это знание на практике — задай вопрос «как это работает?»"
        adaptations.append("практическая рекомендация")

    elif profile.learning_style == LearningStyle.PHILOSOPHICAL:
        adapted += "\n\n💭 Эта тема связана с глубинными вопросами бытия. Хочешь углубиться?"
        adaptations.append("философская рекомендация")

    elif profile.learning_style == LearningStyle.HISTORICAL:
        adapted += "\n\n📜 Эта тема имеет исторические параллели. Хочешь узнать больше?"
        adaptations.append("историческая рекомендация")

    return AdaptiveResponse(
        text=adapted,
        level=profile.level,
        style=profile.learning_style,
        adaptations=adaptations,
    )


def _simplify_language(text: str) -> str:
    """Упростить язык для новичков."""
    # Замены сложных терминов на простые
    replacements = {
        "трансцендентное": "высшее",
        "космическое сознание": "понимание мира",
        "энергоинформационное поле": "энергия",
        "самозаконсервированное": "неподвижное",
        "мистический": "таинственный",
        "архат": "просветлённый учитель",
        "иерархия света": "цепь учителей",
    }

    result = text
    for complex_word, simple_word in replacements.items():
        result = result.replace(complex_word, simple_word)

    return result
