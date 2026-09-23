"""Cause-Effect Planner — детерминированный каркас + LLM для связей.

Гибридный подход:
1. Детерминированный каркас: временной порядок + exclusion-правила + паттерны
2. LLM для генерации причинно-следственных связей (в Composer)
3. Post-валидация: cause-before-effect, entity presence
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.constraint_engine import StoryRequest

log = logging.getLogger("hermes.narrative.planners.cause_effect")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class CauseEffectNode(BaseModel):
    id: str
    type: str  # "cause", "effect", "reaction", "world_change", "constraint"
    description: str
    source_level: str = "SYSTEM_INTERPRETATION"
    confidence: float = 0.8
    depends_on: list[str] = Field(default_factory=list)
    characters_involved: list[str] = Field(default_factory=list)
    epoch: str = ""
    order: int = 0  # для временной упорядоченности


class CauseEffectTree(BaseModel):
    root: str
    nodes: list[CauseEffectNode] = Field(default_factory=list)
    branches: list[list[str]] = Field(default_factory=list)
    world_impact: dict = Field(default_factory=dict)
    matched_pattern: str = ""
    temporal_order: list[str] = Field(default_factory=list)  # ID узлов по порядку времени


# ── Паттерны → цепочки узлов ──

PATTERN_CHAINS = {
    # ── Классические паттерны (10 существующих) ──
    "Путешествие героя": [
        {"type": "cause", "desc": "Герой покидает привычный мир", "order": 1},
        {"type": "effect", "desc": "Герой проходит испытания на пути", "order": 2},
        {"type": "effect", "desc": "Герой обретает новый опыт и знания", "order": 3},
        {"type": "effect", "desc": "Герой возвращается с даром", "order": 4},
    ],
    "Учитель → Ученик → Посредник": [
        {"type": "cause", "desc": "Учитель передаёт знания ученику", "order": 1},
        {"type": "effect", "desc": "Ученик усваивает и трансформирует знание", "order": 2},
        {"type": "effect", "desc": "Ученик становится Посредником для следующего поколения", "order": 3},
    ],
    "Катастрофа → Миграция → Возрождение": [
        {"type": "cause", "desc": "Катастрофа разрушает привычный мир", "order": 1},
        {"type": "effect", "desc": "Народ вынужден мигрировать", "order": 2},
        {"type": "effect", "desc": "На новом месте начинается возрождение", "order": 3},
    ],
    "Зеркальные эпохи": [
        {"type": "cause", "desc": "Эпоха расцвета (свет)", "order": 1},
        {"type": "effect", "desc": "Зеркальное отражение — эпоха упадка (тьма)", "order": 2},
    ],
    "Триада: Дух — Тело — Разум": [
        {"type": "cause", "desc": "Духовное пробуждение", "order": 1},
        {"type": "effect", "desc": "Телесная трансформация", "order": 2},
        {"type": "effect", "desc": "Расширение разума", "order": 3},
    ],
    "Связь с природой": [
        {"type": "cause", "desc": "Человек обращается к природе как учителю", "order": 1},
        {"type": "effect", "desc": "Природа раскрывает законы", "order": 2},
        {"type": "effect", "desc": "Человек живёт в гармонии с природой", "order": 3},
    ],
    "Передача через молчание": [
        {"type": "cause", "desc": "Учитель присутствует в безмолвии", "order": 1},
        {"type": "effect", "desc": "Ученик воспринимает знание через пространство", "order": 2},
    ],
    "Изоляция → Осознание → Возврат": [
        {"type": "cause", "desc": "Герой уединяется", "order": 1},
        {"type": "effect", "desc": "В уединении приходит осознание", "order": 2},
        {"type": "effect", "desc": "Герой возвращается для служения", "order": 3},
    ],
    "Круг замыкается": [
        {"type": "cause", "desc": "Начало пути", "order": 1},
        {"type": "effect", "desc": "Прохождение через испытания", "order": 2},
        {"type": "effect", "desc": "Возврат к началу на новом уровне", "order": 3},
    ],
    "Гармония через знание": [
        {"type": "cause", "desc": "Познание законов", "order": 1},
        {"type": "effect", "desc": "Понимание ведёт к гармонии", "order": 2},
    ],
    # ── Новые паттерны (40+) ──
    "Пробуждение": [
        {"type": "cause", "desc": "Спитон получает первый сигнал", "order": 1},
        {"type": "effect", "desc": "Начинается внутренняя трансформация", "order": 2},
        {"type": "effect", "desc": "Мир вокруг начинает откликаться", "order": 3},
    ],
    "Испытание": [
        {"type": "cause", "desc": "Герой стоит перед выбором", "order": 1},
        {"type": "effect", "desc": "Путь разделяется на два", "order": 2},
        {"type": "effect", "desc": "Выбор определяет дальнейшее развитие", "order": 3},
    ],
    "Потеря → Поиск → Обретение": [
        {"type": "cause", "desc": "Герой теряет то, что казалось вечным", "order": 1},
        {"type": "effect", "desc": "Начинается поиск утраченного", "order": 2},
        {"type": "effect", "desc": "Находится нечто большее, чем было", "order": 3},
    ],
    "Восхождение": [
        {"type": "cause", "desc": "Герой поднимается над обстоятельствами", "order": 1},
        {"type": "effect", "desc": "Каждый шаг расширяет сознание", "order": 2},
        {"type": "effect", "desc": "Достигается новый уровень понимания", "order": 3},
    ],
    "Нисхождение": [
        {"type": "cause", "desc": "Герой опускается в глубины", "order": 1},
        {"type": "effect", "desc": "Столкновение с теневой стороной", "order": 2},
        {"type": "effect", "desc": "Интеграция тёмного и светлого", "order": 3},
    ],
    "Союз против хаоса": [
        {"type": "cause", "desc": "Возникает угроза единству", "order": 1},
        {"type": "effect", "desc": "Разрозненные силы объединяются", "order": 2},
        {"type": "effect", "desc": "Совместными усилиями хаос побеждается", "order": 3},
    ],
    "Жертва ради будущего": [
        {"type": "cause", "desc": "Герой осознаёт необходимость жертвы", "order": 1},
        {"type": "effect", "desc": "Происходит отказ от личного ради общего", "order": 2},
        {"type": "effect", "desc": "Будущее поколение получает дар", "order": 3},
    ],
    "Пророчество сбывается": [
        {"type": "cause", "desc": "Знаки указывают на приближение пророчества", "order": 1},
        {"type": "effect", "desc": "События складываются в единую картину", "order": 2},
        {"type": "effect", "desc": "Пророчество реализуется, мир меняется", "order": 3},
    ],
    "Возвращение изгнанника": [
        {"type": "cause", "desc": "Изгнанник получает сигнал о возвращении", "order": 1},
        {"type": "effect", "desc": "Путь обратно полон испытаний", "order": 2},
        {"type": "effect", "desc": "Изгнанник возвращается преображённым", "order": 3},
    ],
    "Открытие тайны": [
        {"type": "cause", "desc": "Герой замечает несоответствие", "order": 1},
        {"type": "effect", "desc": "Начинается расследование", "order": 2},
        {"type": "effect", "desc": "Тайна раскрывается, мир меняется", "order": 3},
    ],
    "Преодоление страха": [
        {"type": "cause", "desc": "Герой встречает свой главный страх", "order": 1},
        {"type": "effect", "desc": "Страх парализует, но герой сопротивляется", "order": 2},
        {"type": "effect", "desc": "Страх побеждается, рождается смелость", "order": 3},
    ],
    "Перерождение": [
        {"type": "cause", "desc": "Старый мир рушится", "order": 1},
        {"type": "effect", "desc": "Из руин рождается нечто новое", "order": 2},
        {"type": "effect", "desc": "Новый мир обретает форму", "order": 3},
    ],
    "Дар предков": [
        {"type": "cause", "desc": "Предки передают мудрость через поколения", "order": 1},
        {"type": "effect", "desc": "Нынешнее поколение осознаёт наследие", "order": 2},
        {"type": "effect", "desc": "Мудрость применяется для решения текущих проблем", "order": 3},
    ],
    "Баланс сил": [
        {"type": "cause", "desc": "Одна сторона набирает силу", "order": 1},
        {"type": "effect", "desc": "Другая сторона вынуждена уравновешивать", "order": 2},
        {"type": "effect", "desc": "Устанавливается новый баланс", "order": 3},
    ],
    "Цикл времён": [
        {"type": "cause", "desc": "Эпоха подходит к завершению", "order": 1},
        {"type": "effect", "desc": "Начинается переходный период", "order": 2},
        {"type": "effect", "desc": "Рождается новая эпоха", "order": 3},
    ],
    "Служение": [
        {"type": "cause", "desc": "Герой осознаёт свой долг", "order": 1},
        {"type": "effect", "desc": "Герой посвящает себя служению", "order": 2},
        {"type": "effect", "desc": "Служение приносит плоды", "order": 3},
    ],
    "Восстание против тьмы": [
        {"type": "cause", "desc": "Тьма угрожает миру", "order": 1},
        {"type": "effect", "desc": "Герой собирает силы света", "order": 2},
        {"type": "effect", "desc": "Происходит решающая битва", "order": 3},
        {"type": "effect", "desc": "Свет побеждает, мир восстанавливается", "order": 4},
    ],
    "Тайное знание": [
        {"type": "cause", "desc": "Герой обнаруживает скрытый источник", "order": 1},
        {"type": "effect", "desc": "Знание раскрывается постепенно", "order": 2},
        {"type": "effect", "desc": "Знание трансформирует героя", "order": 3},
    ],
    "Единение с природой": [
        {"type": "cause", "desc": "Человек слышит голос природы", "order": 1},
        {"type": "effect", "desc": "Природа раскрывает свои тайны", "order": 2},
        {"type": "effect", "desc": "Человек и природа становятся единым целым", "order": 3},
    ],
    "Преображение через страдание": [
        {"type": "cause", "desc": "Герой проходит через боль", "order": 1},
        {"type": "effect", "desc": "Страдание очищает и укрепляет", "order": 2},
        {"type": "effect", "desc": "Из боли рождается новое понимание", "order": 3},
    ],
    "Хранитель огня": [
        {"type": "cause", "desc": "Герой становится хранителем священного огня", "order": 1},
        {"type": "effect", "desc": "Огонь защищает и направляет", "order": 2},
        {"type": "effect", "desc": "Герой передаёт огонь следующему поколению", "order": 3},
    ],
    "Путь воина": [
        {"type": "cause", "desc": "Герой принимает путь воина", "order": 1},
        {"type": "effect", "desc": "Испытания закаляют характер", "order": 2},
        {"type": "effect", "desc": "Воин защищает тех, кто не может защитить себя", "order": 3},
    ],
    "Мудрость через опыт": [
        {"type": "cause", "desc": "Герой проходит через множество испытаний", "order": 1},
        {"type": "effect", "desc": "Каждое испытание учит чему-то", "order": 2},
        {"type": "effect", "desc": "Накопленная мудрость помогает другим", "order": 3},
    ],
    "Пробуждение совести": [
        {"type": "cause", "desc": "Герой осознаёт последствия своих действий", "order": 1},
        {"type": "effect", "desc": "Совесть требует изменений", "order": 2},
        {"type": "effect", "desc": "Герой меняет путь, мир меняется", "order": 3},
    ],
    "Единство против разделения": [
        {"type": "cause", "desc": "Разделение ослабляет мир", "order": 1},
        {"type": "effect", "desc": "Герой ищет путь к единению", "order": 2},
        {"type": "effect", "desc": "Единство возвращает силу", "order": 3},
    ],
    "Трансформация через искусство": [
        {"type": "cause", "desc": "Герой обращается к творчеству", "order": 1},
        {"type": "effect", "desc": "Искусство раскрывает скрытые истины", "order": 2},
        {"type": "effect", "desc": "Творчество меняет мир вокруг", "order": 3},
    ],
    "Восстановление утраченного": [
        {"type": "cause", "desc": "Герой обнаруживает следы прошлого", "order": 1},
        {"type": "effect", "desc": "Начинается работа по восстановлению", "order": 2},
        {"type": "effect", "desc": "Прошлое обретает новую жизнь", "order": 3},
    ],
    "Познание себя": [
        {"type": "cause", "desc": "Герой задаётся вопросом «Кто я?»", "order": 1},
        {"type": "effect", "desc": "Начинается внутреннее путешествие", "order": 2},
        {"type": "effect", "desc": "Герой обретает подлинную природу", "order": 3},
    ],
    "Связь поколений": [
        {"type": "cause", "desc": "Старшее поколение передаёт знания", "order": 1},
        {"type": "effect", "desc": "Младшее поколение усваивает и развивает", "order": 2},
        {"type": "effect", "desc": "Знание растёт через поколения", "order": 3},
    ],
    "Преодоление гордыни": [
        {"type": "cause", "desc": "Герой осознаёт свою гордыню", "order": 1},
        {"type": "effect", "desc": "Гордыня мешает, герой борется с ней", "order": 2},
        {"type": "effect", "desc": "Смирение открывает новый путь", "order": 3},
    ],
    "Дар исцеления": [
        {"type": "cause", "desc": "Герой обретает способность исцелять", "order": 1},
        {"type": "effect", "desc": "Исцеление помогает другим", "order": 2},
        {"type": "effect", "desc": "Исцеление возвращает гармонию", "order": 3},
    ],
    "Путь мудреца": [
        {"type": "cause", "desc": "Герой ищет мудрость", "order": 1},
        {"type": "effect", "desc": "Мудрость приходит через тишину", "order": 2},
        {"type": "effect", "desc": "Мудрец направляет других", "order": 3},
    ],
    "Пробуждение памяти": [
        {"type": "cause", "desc": "Герой вспоминает забытое", "order": 1},
        {"type": "effect", "desc": "Память раскрывает тайну", "order": 2},
        {"type": "effect", "desc": "Тайна меняет понимание мира", "order": 3},
    ],
    "Единство природы и духа": [
        {"type": "cause", "desc": "Герой находит связь между природой и духом", "order": 1},
        {"type": "effect", "desc": "Связь раскрывает глубинные законы", "order": 2},
        {"type": "effect", "desc": "Герой живёт в гармонии с обоими", "order": 3},
    ],
    "Преображение через любовь": [
        {"type": "cause", "desc": "Герой встречает глубокую любовь", "order": 1},
        {"type": "effect", "desc": "Любовь трансформирует восприятие", "order": 2},
        {"type": "effect", "desc": "Из любви рождается новое понимание мира", "order": 3},
    ],
    "Хранитель знания": [
        {"type": "cause", "desc": "Герой становится хранителем знания", "order": 1},
        {"type": "effect", "desc": "Знание защищается и передаётся", "order": 2},
        {"type": "effect", "desc": "Знание спасает мир в трудную минуту", "order": 3},
    ],
    "Путь целителя": [
        {"type": "cause", "desc": "Герой осознаёт дар целительства", "order": 1},
        {"type": "effect", "desc": "Целительство помогает больным", "order": 2},
        {"type": "effect", "desc": "Целитель исцеляет и мир вокруг", "order": 3},
    ],
    "Пробуждение интуиции": [
        {"type": "cause", "desc": "Герой учится слышать внутренний голос", "order": 1},
        {"type": "effect", "desc": "Интуиция раскрывает скрытое", "order": 2},
        {"type": "effect", "desc": "Интуиция направляет к истине", "order": 3},
    ],
    "Единство прошлого и будущего": [
        {"type": "cause", "desc": "Герой связывает прошлое и будущее", "order": 1},
        {"type": "effect", "desc": "Прошлое озаряет будущее", "order": 2},
        {"type": "effect", "desc": "Будущее обогащает прошлое", "order": 3},
    ],
    "Преображение через тишину": [
        {"type": "cause", "desc": "Герой находит тишину", "order": 1},
        {"type": "effect", "desc": "В тишине раскрывается истина", "order": 2},
        {"type": "effect", "desc": "Тишина меняет мир", "order": 3},
    ],
    "Хранитель огня знания": [
        {"type": "cause", "desc": "Герой зажигает огонь знания", "order": 1},
        {"type": "effect", "desc": "Огонь освещает путь другим", "order": 2},
        {"type": "effect", "desc": "Огонь знания передаётся из поколения в поколение", "order": 3},
    ],
    "Путь созидателя": [
        {"type": "cause", "desc": "Герой начинает создавать", "order": 1},
        {"type": "effect", "desc": "Созидание приносит радость", "order": 2},
        {"type": "effect", "desc": "Созданное обогащает мир", "order": 3},
    ],
    "Пробуждение сострадания": [
        {"type": "cause", "desc": "Герой встречает чужую боль", "order": 1},
        {"type": "effect", "desc": "Сострадание пробуждается", "order": 2},
        {"type": "effect", "desc": "Сострадание ведёт к действию", "order": 3},
    ],
    "Единство знания и любви": [
        {"type": "cause", "desc": "Герой соединяет знание и любовь", "order": 1},
        {"type": "effect", "desc": "Знание становится мудростью", "order": 2},
        {"type": "effect", "desc": "Мудрость меняет мир", "order": 3},
    ],
}


class CauseEffectPlanner:
    """Гибридный планировщик причинно-следственных связей."""

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._patterns = self._load_patterns()

    def _load_patterns(self) -> list:
        path = KNOWLEDGE_DIR / "PATTERNS.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get("patterns", [])
            except Exception:
                return []
        return []

    def plan(self, request: StoryRequest, context: FullContext) -> CauseEffectTree:
        # 1. Детерминированный каркас
        temporal_graph = self._build_temporal_graph(context)
        entity_presence = self._build_entity_presence(context)
        exclusion_violations = self._check_exclusions(request, context)
        matched_pattern = self._match_pattern(request)

        # 2. Генерация узлов
        nodes = self._generate_nodes(
            request, context, temporal_graph, entity_presence,
            matched_pattern, exclusion_violations,
        )

        # 3. Построение ветвей и временного порядка
        branches = self._build_branches(nodes)
        temporal_order = self._build_temporal_order(nodes)

        # 4. Post-валидация
        validated_nodes = self._validate_nodes(nodes, temporal_order)

        return CauseEffectTree(
            root=request.prompt[:100],
            nodes=validated_nodes,
            branches=branches,
            world_impact=self._compute_world_impact(validated_nodes),
            matched_pattern=matched_pattern.get("name", "") if matched_pattern else "",
            temporal_order=temporal_order,
        )

    def _build_temporal_graph(self, context: FullContext) -> dict:
        events = self._wm.get_events()
        graph = {}
        for ev in events:
            graph[ev.id] = {
                "epoch": ev.epoch,
                "order": ev.order_in_epoch,
                "chapter": ev.chapter or 0,
                "title": ev.title_ru,
            }
        return graph

    def _build_entity_presence(self, context: FullContext) -> dict:
        presence = {}
        for epoch in self._wm.get_epochs():
            chars = self._wm.get_characters_alive(epoch.id)
            presence[epoch.id] = [c.character_name for c in chars]
        return presence

    def _check_exclusions(self, request: StoryRequest, context: FullContext) -> list[dict]:
        """Проверить exclusion-правила и вернуть нарушения."""
        violations = []
        for rule in self._wm.get_rules():
            if rule.rule_type == "exclusion":
                # Проверяем: есть ли в запросе потенциальное нарушение
                prompt_lower = request.prompt.lower()
                violation = self._check_rule_violation(rule, prompt_lower, context)
                if violation:
                    violations.append({
                        "rule_id": rule.id,
                        "rule_desc": rule.description,
                        "violation": violation,
                    })
        return violations

    def _check_rule_violation(self, rule, prompt_lower: str, context: FullContext) -> Optional[str]:
        """Проверить конкретное правило на нарушение."""
        if rule.id == "rule_no_future_knowledge":
            # Персонаж не может знать о будущих событиях
            return None  # Сложно проверить без LLM

        if rule.id == "rule_no_tech_before_epoch":
            # Технологии должны соответствовать эпохе
            tech_words = ["порох", "ружье", "телефон", "интернет", "компьютер"]
            for word in tech_words:
                if word in prompt_lower:
                    return f"Запрос содержит технологию '{word}', которая может не существовать в эпохе"
            return None

        if rule.id == "rule_geographic_consistency":
            return None  # География проверяется в CanonValidator

        if rule.id == "rule_causal_chain":
            return None  # Следствия не могут предшествовать причинам — проверяется в _validate_nodes

        return None

    def _match_pattern(self, request: StoryRequest) -> Optional[dict]:
        prompt_lower = request.prompt.lower()

        keyword_map = {
            "Путешествие героя": ["путешеств", "путь", "дорог", "идти", "идёт"],
            "Учитель → Ученик → Посредник": ["учитель", "ученик", "наставник", "посредник"],
            "Катастрофа → Миграция → Возрождение": ["катастроф", "потоп", "миграц", "возрожд"],
            "Зеркальные эпохи": ["зеркал", "противополож", "отраж"],
            "Триада: Дух — Тело — Разум": ["дух", "тело", "разум", "триада"],
            "Связь с природой": ["природ", "земл", "лес", "вода"],
            "Передача через молчание": ["молчан", "тишин", "безмолв"],
            "Изоляция → Осознание → Возврат": ["уединен", "изоляц", "возврат"],
            "Круг замыкается": ["круг", "спираль", "возврат к началу"],
            "Гармония через знание": ["гармон", "познан", "знани"],
        }

        for pattern in self._patterns:
            p_name = pattern.get("name", "")
            keywords = keyword_map.get(p_name, [])
            if any(kw in prompt_lower for kw in keywords):
                return pattern

        return None

    def _generate_nodes(
        self,
        request: StoryRequest,
        context: FullContext,
        temporal_graph: dict,
        entity_presence: dict,
        matched_pattern: Optional[dict],
        exclusion_violations: list[dict],
    ) -> list[CauseEffectNode]:
        nodes = []
        node_id = 0

        # ── Узел 0: Запрос пользователя (корень) ──
        nodes.append(CauseEffectNode(
            id=f"n{node_id}",
            type="cause",
            description=request.prompt[:200],
            source_level="USER_HYPOTHESIS",
            confidence=1.0,
            order=0,
        ))
        node_id += 1

        # ── Узлы из паттерна (цепочка!) ──
        if matched_pattern:
            p_name = matched_pattern.get("name", "")
            chain = PATTERN_CHAINS.get(p_name, [])
            if chain:
                for step in chain:
                    nodes.append(CauseEffectNode(
                        id=f"n{node_id}",
                        type=step["type"],
                        description=f"[Паттерн: {p_name}] {step['desc']}",
                        source_level="SYSTEM_INTERPRETATION",
                        confidence=0.85,
                        depends_on=["n0"],
                        order=step["order"],
                    ))
                    node_id += 1
            else:
                # Паттерн есть, но цепочки нет — generic узел
                nodes.append(CauseEffectNode(
                    id=f"n{node_id}",
                    type="effect",
                    description=f"Паттерн: {p_name}. {matched_pattern.get('description', '')[:150]}",
                    source_level="SYSTEM_INTERPRETATION",
                    confidence=0.8,
                    depends_on=["n0"],
                    order=1,
                ))
                node_id += 1

        # ── Контекст эпохи ──
        if context.historical.epoch_facts:
            facts_text = "; ".join(f.text[:80] for f in context.historical.epoch_facts[:2])
            nodes.append(CauseEffectNode(
                id=f"n{node_id}",
                type="cause",
                description=f"Контекст: {facts_text}",
                source_level="CANON",
                confidence=0.95,
                depends_on=["n0"],
                order=0,
            ))
            node_id += 1

        # ── Персонажи и их роли ──
        if context.world_state and isinstance(context.world_state, dict):
            chars = context.world_state.get("characters_alive", [])[:3]
            for i, ch in enumerate(chars):
                name = ch.get("character_name", "")
                status = ch.get("status", "")
                if name:
                    # Определяем роль персонажа в истории
                    role_desc = self._infer_character_role(name, request)
                    nodes.append(CauseEffectNode(
                        id=f"n{node_id}",
                        type="reaction",
                        description=f"{name} ({status}): {role_desc}",
                        source_level="CANON",
                        confidence=0.8,
                        depends_on=["n0"],
                        characters_involved=[name],
                        order=2 + i,
                    ))
                    node_id += 1

        # ── Исключения ( constraints ) ──
        for v in exclusion_violations:
            nodes.append(CauseEffectNode(
                id=f"n{node_id}",
                type="constraint",
                description=f"Нарушение правила: {v['violation']}",
                source_level="SYSTEM_INTERPRETATION",
                confidence=1.0,
                order=0,
            ))
            node_id += 1

        # ── Стандартные правила ──
        for rule in self._wm.get_rules():
            if rule.rule_type == "exclusion":
                nodes.append(CauseEffectNode(
                    id=f"n{node_id}",
                    type="constraint",
                    description=f"Правило: {rule.description}",
                    source_level="SYSTEM_INTERPRETATION",
                    confidence=1.0,
                    order=0,
                ))
                node_id += 1

        return nodes

    def _infer_character_role(self, name: str, request: StoryRequest) -> str:
        """Вывести роль персонажа из контекста."""
        prompt_lower = request.prompt.lower()
        name_lower = name.lower()

        # Простые эвристики
        if any(kw in prompt_lower for kw in [name_lower, name_lower[:4]]):
            return "упомянут в запросе — ключевая роль"
        if "учител" in name_lower or "наставник" in name_lower:
            return "наставник, передаёт знания"
        if "ученик" in name_lower:
            return "ученик, проходит путь познания"
        return "участвует в событиях эпохи"

    def _build_branches(self, nodes: list[CauseEffectNode]) -> list[list[str]]:
        """Построить ветви (цепочки узлов по depends_on)."""
        branches = []
        root_nodes = [n for n in nodes if not n.depends_on]
        for root in root_nodes:
            branch = [root.id]
            # Рекурсивно находим дочерние
            children = [n for n in nodes if root.id in n.depends_on]
            for child in children:
                branch.append(child.id)
                # Вложенные дочерние
                grandchildren = [n for n in nodes if child.id in n.depends_on]
                for gc in grandchildren:
                    branch.append(gc.id)
            if len(branch) > 1:
                branches.append(branch)
        return branches

    def _build_temporal_order(self, nodes: list[CauseEffectNode]) -> list[str]:
        """Построить временной порядок узлов."""
        sorted_nodes = sorted(nodes, key=lambda n: n.order)
        return [n.id for n in sorted_nodes]

    def _validate_nodes(
        self,
        nodes: list[CauseEffectNode],
        temporal_order: list[str],
    ) -> list[CauseEffectNode]:
        """Post-валидация: confidence + cause-before-effect."""
        validated = []
        order_map = {nid: i for i, nid in enumerate(temporal_order)}

        for node in nodes:
            # Фильтр по confidence
            if node.confidence < 0.5:
                log.debug("dropping_low_confidence node=%s conf=%.2f", node.id, node.confidence)
                continue

            # Проверка: cause-before-effect
            if node.type == "effect" and node.depends_on:
                node_pos = order_map.get(node.id, 999)
                for dep_id in node.depends_on:
                    dep_pos = order_map.get(dep_id, 999)
                    if dep_pos > node_pos:
                        log.warning("temporal_violation node=%s depends_on=%s but appears before", node.id, dep_id)
                        # Не удаляем, но понижаем confidence
                        node.confidence *= 0.8

            validated.append(node)

        return validated

    def _compute_world_impact(self, nodes: list[CauseEffectNode]) -> dict:
        characters = set()
        for node in nodes:
            characters.update(node.characters_involved)

        return {
            "affected_characters": list(characters),
            "node_count": len(nodes),
            "types": list(set(n.type for n in nodes)),
            "constraint_count": sum(1 for n in nodes if n.type == "constraint"),
        }
