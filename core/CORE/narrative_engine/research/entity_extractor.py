"""Entity Extractor — извлечение сущностей из текста книги."""

import re
import json
import logging
from typing import Optional
from pydantic import BaseModel

log = logging.getLogger("hermes.narrative.entity_extractor")


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str  # location, character, technology, event, concept
    context_snippet: str
    confidence: float = 0.7


# Known entities from the book
KNOWN_ENTITIES = {
    # Locations
    "гиперборея": ("location", "Гиперборея"),
    "аркаим": ("location", "Аркаим"),
    "тмутаракань": ("location", "Тмутаракань"),
    "шумер": ("location", "Шумер"),
    "индия": ("location", "Индия"),
    "атлантида": ("location", "Атлантида"),
    "лемурия": ("location", "Лемурия"),
    "океания": ("location", "Океания"),
    "рус": ("location", "Древняя Русь"),
    "европа": ("location", "Европа"),
    "африка": ("location", "Африка"),
    "кавказ": ("location", "Кавказ"),
    "ура": ("location", "Урал"),
    "уран": ("location", "Урал"),
    # Characters
    "велик": ("character", "Велик"),
    "архат": ("character", "Архат"),
    "мирович": ("character", "Мирович"),
    "световит": ("character", "Световит"),
    "радомир": ("character", "Радомир"),
    "мирослав": ("character", "Мирослав"),
    "рада": ("character", "Рада"),
    "жрец": ("character", "Жрец"),
    "учитель": ("character", "Учитель"),
    # Concepts
    "кали юга": ("concept", "Кали Юга"),
    "сатья юга": ("concept", "Сатья Юга"),
    "трета юга": ("concept", "Трета Юга"),
    "двапара юга": ("concept", "Двапара Юга"),
    "духовное развитие": ("concept", "Духовное развитие"),
    "космическое сознание": ("concept", "Космическое сознание"),
    "карма": ("concept", "Карма"),
    "дхарма": ("concept", "Дхарма"),
    "йога": ("concept", "Йога"),
    "медитация": ("concept", "Медитация"),
    "просветление": ("concept", "Просветление"),
    "перерождение": ("concept", "Перерождение"),
    # Technologies
    "кристальная технология": ("technology", "Кристальная технология"),
    "гармония энергий": ("technology", "Гармония энергий"),
    "каменное зодчество": ("technology", "Каменное зодчество"),
    "круговая система": ("technology", "Круговая система"),
}

# Patterns for Russian proper nouns (potential names)
NAME_PATTERN = re.compile(r'\b[А-ЯЁ][а-яё]{2,}(?:а|у|е|ом|ей)?\b')

# Common Russian words that look like names but aren't
NOT_NAMES = {
    "это", "что", "как", "где", "когда", "был", "была", "было", "были",
    "его", "её", "их", "эти", "тот", "та", "те", "все", "вся", "всё",
    "нет", "да", "ещё", "уже", "тоже", "также", "более", "менее",
    "между", "перед", "после", "через", "около", "вдоль", "над", "под",
    "каждый", "каждая", "каждое", "другой", "другая", "другое",
    "такой", "такая", "такое", "весь", "вся", "всё",
    "много", "мало", "чтобы", "который", "которая", "которое",
    "самый", "самая", "самое", "первый", "второй", "третий",
    "новый", "новая", "новое", "старый", "старая", "старое",
    "большой", "большая", "большое", "маленький", "маленькая",
    "хороший", "хорошая", "хорошее", "плохой", "плохая", "плохое",
    "один", "два", "три", "четыре", "пять",
    "сегодня", "вчера", "завтра", "сейчас", "потом", "теперь",
    "сюда", "туда", "здесь", "там", "тогда", "потому", "поэтому",
    "значит", "конечно", "действительно", "пожалуй", "вероятно",
    "может", "нужно", "надо", "можно", "нельзя", "должен", "должна",
    "какой", "какая", "какое", "чей", "чья", "чьё",
    "этот", "эта", "эти", "тот", "та", "те",
    "того", "той", "тех", "этому", "этой", "этим",
    "свою", "свой", "своя", "своё", "свои",
    "очень", "вполне", "крайне", "слишком", "довольно",
    "будет", "будут", "быть", "есть", "иметь",
    "стала", "стало", "стали", "стал",
    "мог", "могла", "могло", "могли",
    "знал", "знала", "знало", "знали",
    "жил", "жила", "жило", "жили",
    "шёл", "шла", "шло", "шли",
    "дал", "дала", "дало", "дали",
    "взял", "взяла", "взяло", "взяли",
    "сказал", "сказала", "сказали",
    "пошёл", "пошла", "пошло", "пошли",
    "пришёл", "пришла", "пришло", "пришли",
    "ушёл", "ушла", "ушло", "ушли",
    "встал", "встала", "встало", "встали",
    "сел", "села", "село", "сели",
    "лёг", "легла", "легло", "легли",
    "взял", "взяла", "взяло", "взяли",
    "дал", "дала", "дало", "дали",
    "сделал", "сделала", "сделало", "сделали",
    "начал", "начала", "начало", "начали",
    "кончил", "кончила", "кончило", "кончили",
    "закончил", "закончила", "закончило", "закончили",
    "остановился", "остановилась", "остановилось", "остановились",
    "повернулся", "повернулась", "повернулось", "повернулись",
    "поднялся", "поднялась", "поднялось", "поднялись",
    "опустился", "опустилась", "опустилось", "опустились",
    "вышел", "вышла", "вышло", "вышли",
    "вошёл", "вошла", "вошло", "вошли",
    "бежал", "бежала", "бежало", "бежали",
    "летел", "летела", "летело", "летели",
    "плыл", "плыла", "плыло", "плыли",
    "ехал", "ехала", "ехало", "ехали",
    "стоял", "стояла", "стояло", "стояли",
    "сидел", "сидела", "сидело", "сидели",
    "лежал", "лежала", "лежало", "лежали",
    "спал", "спала", "спало", "спали",
    "ел", "ела", "ело", "ели",
    "пил", "пила", "пило", "пили",
    "брал", "брала", "брало", "брали",
    "кидал", "кидала", "кидало", "кидали",
    "ломал", "ломала", "ломало", "ломали",
    "рвал", "рвала", "рвало", "рвали",
    "резал", "резала", "резало", "резали",
    "колол", "колола", "кололо", "кололи",
    "жёг", "жгла", "жгло", "жгли",
    "тёр", "терла", "терло", "терли",
    "молол", "молола", "мололо", "мололи",
    "точил", "точила", "точило", "точили",
    "шил", "шила", "шило", "шили",
    "вязал", "вязала", "вязало", "вязали",
    "вышивал", "вышивала", "вышивало", "вышивали",
    "рисовал", "рисовала", "рисовало", "рисовали",
    "писал", "писала", "писало", "писали",
    "читал", "читала", "читало", "читали",
    "учил", "учила", "учило", "учили",
    "учился", "училась", "училось", "учились",
    "думал", "думала", "думало", "думали",
    "верил", "верила", "верило", "верили",
    "знал", "знала", "знало", "знали",
    "помнил", "помнила", "помнило", "помнили",
    "чувствовал", "чувствовала", "чувствовало", "чувствовали",
    "видел", "видела", "видело", "видели",
    "слышал", "слышала", "слышало", "слышали",
    "чуял", "чуяла", "чуяло", "чуяли",
    "ощущал", "ощущала", "ощущало", "ощущали",
    "понимал", "понимала", "понимало", "понимали",
    "вспомнил", "вспомнила", "вспомнило", "вспомнили",
    "забыл", "забыла", "забыло", "забыли",
    "вспомнить", "забыть", "понять", "узнать", "увидеть", "услышать",
    "сделать", "начать", "кончить", "остановить", "продолжить",
    "идти", "бежать", "лететь", "плыть", "ехать", "стоять", "сидеть",
    "лежать", "спать", "есть", "пить", "брать", "кидать", "ломать",
    "рвать", "резать", "колоть", "жечь", "тереть", "молоть", "точить",
    "шить", "вязать", "вышивать", "рисовать", "писать", "читать",
    "учить", "учиться", "думать", "верить", "знать", "помнить",
    "чувствовать", "видеть", "слышать", "чуть", "ощущать", "понимать",
    "вспомнить", "забыть",
}


def extract_entities(text: str, chapter: Optional[int] = None) -> list[ExtractedEntity]:
    """Извлечь известные сущности из текста + regex-based extraction."""
    entities = []
    text_lower = text.lower()
    seen = set()

    # 1. Known entities (keyword matching)
    for keyword, (etype, ename) in KNOWN_ENTITIES.items():
        if keyword in text_lower and keyword not in seen:
            seen.add(keyword)
            idx = text_lower.index(keyword)
            start = max(0, idx - 50)
            end = min(len(text), idx + len(keyword) + 50)
            snippet = text[start:end]
            entities.append(ExtractedEntity(
                name=ename,
                entity_type=etype,
                context_snippet=snippet,
                confidence=0.9,
            ))

    # 2. Regex-based extraction for proper nouns
    potential_names = NAME_PATTERN.findall(text)
    for name in potential_names:
        name_lower = name.lower()
        if name_lower in NOT_NAMES or name_lower in seen or len(name) < 4:
            continue
        # Skip if already found as known entity
        if any(name_lower in e.name.lower() for e in entities):
            continue
        seen.add(name_lower)
        # Find context
        idx = text_lower.index(name_lower)
        start = max(0, idx - 50)
        end = min(len(text), idx + len(name) + 50)
        snippet = text[start:end]
        entities.append(ExtractedEntity(
            name=name,
            entity_type="character",  # Default to character for proper nouns
            context_snippet=snippet,
            confidence=0.5,
        ))

    return entities


async def extract_entities_llm(text: str, chapter: Optional[int] = None) -> list[ExtractedEntity]:
    """Извлечь сущности через LLM (fallback на rule-based)."""
    try:
        from providers.registry import ProviderRegistry

        extraction_prompt = f"""Извлеки все именованные сущности из текста.
Для каждой сущности укажи:
- name: имя
- type: location/character/concept/technology/event
- context: контекстная цитата (50-100 символов)

Текст:
{text[:3000]}

Верни JSON-массив объектов {{name, type, context}}."""

        provider = ProviderRegistry.get("gigachat") or ProviderRegistry.get("openrouter")
        if not provider:
            return extract_entities(text, chapter)

        messages = [{"role": "user", "content": extraction_prompt}]
        response = ""
        async for token in provider.stream(messages):
            if token and not token.startswith("data:"):
                response += token

        # Parse JSON from response
        import json
        # Try to find JSON array in response
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            items = json.loads(match.group())
            entities = []
            for item in items:
                entities.append(ExtractedEntity(
                    name=item.get("name", ""),
                    entity_type=item.get("type", "concept"),
                    context_snippet=item.get("context", ""),
                    confidence=0.8,
                ))
            return entities

    except Exception as e:
        log.warning("llm_entity_extraction_failed error=%s", e)

    # Fallback to rule-based
    return extract_entities(text, chapter)
