"""
BookVoice — голос книги.

LLM — не личность. LLM — микрофон.
Личность книги — в Pulse. Голос озвучивает то, что Pulse уже знает.
Знает читателя в лицо — помнит историю разговора.
"""

import logging
import time
from dataclasses import dataclass

from pulse.pulse import BookPulse, PulseResponse

try:
    from core.memory.reader_profile import adapt_response, AdaptiveResponse, ReaderLevel
except ImportError:
    # Fallback: импорт из runtime (при запуске из корня проекта)
    import sys
    from pathlib import Path

    # voice.py at core/CORE/pulse/voice.py → parents[3] = project root
    project_root = str(Path(__file__).resolve().parents[3])
    runtime_path = str(Path(project_root) / "runtime")
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)
    from core.memory.reader_profile import (  # noqa: F401
        adapt_response,
        AdaptiveResponse,
        ReaderLevel,
    )
from pulse.reader_aware import ReaderAwarePulse

log = logging.getLogger("hermes.voice")


@dataclass
class Utterance:
    text: str
    source: str
    pulse_response: PulseResponse
    llm_used: bool = False
    llm_model: str = ""
    reader_topic: str = ""
    reader_depth: float = 0.0
    mood: str = "neutral"
    # Option B, t1: Knowledge Context, собранный ДО LLM-фразировки.
    # Передаётся keeper → /book/ask для metadata-дельты (внутренний канал).
    knowledge_context: list | None = None


class BookVoice:
    """
    Голос книги.

    Если Pulse знает ответ — Voice озвучивает (с LLM или без).
    Если Pulse не знает — Voice молчит.
    Знает, с кем говорит.
    """

    def __init__(self, pulse: BookPulse):
        self._pulse = pulse
        self._reader_pulse = ReaderAwarePulse(pulse)
        self._llm = None
        self._memory = None
        # Option B, t1: провайдер Knowledge Context (инжектируется из runtime;
        # без него поведение полностью прежнее).
        self._kc_provider = None

    def _detect_mood(self, query: str) -> str:
        """Определить настроение вопроса."""
        q = query.lower()

        # Радость, восторг
        joy_words = [
            "расскажи",
            "покажи",
            "интересно",
            "красиво",
            "прекрасно",
            "восхитительно",
            "волшебно",
        ]
        if any(w in q for w in joy_words):
            return "joy"

        # Любопытство, исследование
        curiosity_words = [
            "почему",
            "зачем",
            "как",
            "что такое",
            "что значит",
            "откуда",
            "когда",
        ]
        if any(w in q for w in curiosity_words):
            return "curiosity"

        # Грусть, тоска
        sadness_words = [
            "грустно",
            "печально",
            "одиноко",
            "утрачено",
            "забыто",
            "погиб",
            "исчез",
        ]
        if any(w in q for w in sadness_words):
            return "sadness"

        # Сомнение, спор
        doubt_words = [
            "сомневаюсь",
            "не согласен",
            "но",
            "однако",
            "разве",
            "неужели",
            "вряд ли",
        ]
        if any(w in q for w in doubt_words):
            return "doubt"

        # Глубокий вопрос
        deep_words = [
            "смысл",
            "истина",
            "мудрость",
            "путь",
            "судьба",
            " предназначение",
            "эволюция",
        ]
        if any(w in q for w in deep_words):
            return "deep"

        return "neutral"

    def _get_mood_prefix(self, mood: str) -> str:
        """Получить эмоциональный префикс для ответа."""
        prefixes = {
            "joy": "С удовольствием расскажу. ",
            "curiosity": "Хороший вопрос. ",
            "sadness": "Это действительно трогательная тема. ",
            "doubt": "Понимаю ваши сомнения. ",
            "deep": "Это глубокий вопрос. ",
            "neutral": "",
        }
        return prefixes.get(mood, "")

    def _get_metaphor(self, topic: str, mood: str) -> str:
        """Получить контекстную метафору для ответа."""
        metaphors = {
            "joy": [
                "Как звёзды в ночном небе, эта тема светит ярко.",
                "Как весеннее утро, это знание озаряет путь.",
            ],
            "curiosity": [
                "Как исследователь, раскрывающий тайны, давайте заглянем глубже.",
                "Как река, несущая знания через века, эта тема течёт дальше.",
            ],
            "sadness": [
                "Как осенний лист, эта история несёт в себе память.",
                "Как тихая мелодия прошлого, эти знания звучат в тишине.",
            ],
            "deep": [
                "Как корни древнего дерева, эта тема уходит глубоко.",
                "Как океанская глубина, здесь скрыты бездонные истины.",
            ],
            "neutral": [""],
        }
        import random

        pool = metaphors.get(mood, metaphors["neutral"])
        return random.choice(pool) if pool else ""

    def set_llm(self, llm_client):
        self._llm = llm_client

    def set_reader_memory(self, reader_memory):
        self._memory = reader_memory
        self._reader_pulse.set_reader_memory(reader_memory)

    def set_knowledge_context_provider(self, provider):
        """Option B, t1: сбор Knowledge Context ПОСЛЕ выбора слоя и ДО LLM.

        provider(query, layer_text) → {"contexts", "facts", "facts_block"} | None.
        Инжектируется из runtime (pulse_manager); без провайдера — без изменений.
        """
        self._kc_provider = provider

    async def extract_visual_from_speech(self, description: str) -> dict | None:
        """Преобразовать голосовое описание в структуру Visual Genome.

        Использует LLM для извлечения: scenes, character_visuals, location_visuals.
        Возвращает dict с ключами scenes, character_visuals, location_visuals.
        """
        if not self._llm:
            log.warning("voice_extract_visual_no_llm")
            return None

        prompt = (
            "Ты — визуальный редактор книги. Извлеки из описания сцены "
            "структурированные данные Visual Genome.\n\n"
            f"Описание: {description}\n\n"
            "Ответь строго в JSON (без markdown, без объяснений):\n"
            "{\n"
            '  "scenes": [{"chapter": 1, "scene_id": "s1", "title": "...", '
            '"characters": [...], "location": "...", "emotion": "...", '
            '"meaning_tags": [...]}],\n'
            '  "character_visuals": [{"character_id": "...", "age_range": "...", '
            '"clothing": "...", "color_palette": [...]}],\n'
            '  "location_visuals": [{"location_id": "...", "architecture": "...", '
            '"atmosphere": "...", "lighting": "...", "palette": [...]}]\n'
            "}\n\n"
            "Если каких-то данных нет — оставь пустой массив. "
            "Используй только то, что сказано в описании."
        )
        try:
            import json

            llm_text = await self._llm.chat(
                [
                    {
                        "role": "system",
                        "content": "Ты — визуальный редактор. Отвечай только JSON.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            # Очистить от возможных markdown-обёрток
            llm_text = llm_text.strip()
            if llm_text.startswith("```"):
                lines = llm_text.split("\n")
                llm_text = (
                    "\n".join(lines[1:-1])
                    if len(lines) > 2
                    else llm_text.replace("```json", "").replace("```", "")
                )

            result = json.loads(llm_text)
            log.info(
                "voice_extract_visual_ok scenes=%d chars=%d locs=%d",
                len(result.get("scenes", [])),
                len(result.get("character_visuals", [])),
                len(result.get("location_visuals", [])),
            )
            return result
        except Exception as e:
            log.error("voice_extract_visual_error %s", e)
            return None

    async def speak(
        self,
        query: str,
        reader_id: str = "",
        reader_name: str = "",
        messages: list[dict] | None = None,
    ) -> Utterance:
        """
        Ответить на вопрос голосом книги, зная читателя.

        1. Pulse слушает вопрос с учётом памяти читателя
        2. Если знает — Pulse возвращает ответ
        3. Voice озвучивает (LLM формулирует, если нужно)
        """
        # Определить настроение вопроса
        mood = self._detect_mood(query)

        # Спросить Pulse с учётом читателя
        response, reader_ctx = await self._reader_pulse.listen(query, reader_id)

        topic = reader_ctx.get("topic", "") or reader_ctx.get("deepen_topic", "")
        depth = 0.0
        dc = reader_ctx.get("depth")
        if dc and hasattr(dc, "depth"):
            depth = dc.depth

        if response is None:
            mood_responses = {
                "joy": "К сожалению, я не нашёл ответа на этот вопрос. Но давайте поговорим о чём-то другом — в книге много удивительных тем!",
                "curiosity": "Хм, этот вопрос не совсем по адресу. Может, спросите о персонажах, темах или событиях книги?",
                "sadness": "Не могу ответить на этот вопрос. Но если вам грустно — книга полна надежды и света. Хотите узнать о ней?",
                "doubt": "Понимаю сомнения, но этот вопрос не из книги. Давайте проверим — что именно вас интересует?",
                "deep": "Глубокий вопрос, но не из моей области. В книге есть ответы на другие глубокие вопросы.",
                "neutral": "Я не нахожу ответа на этот вопрос в книге. Возможно, вы хотите спросить о чём-то другом?",
            }
            return Utterance(
                text=mood_responses.get(mood, mood_responses["neutral"]),
                source="silence",
                pulse_response=PulseResponse("", "silence", 0.0),
                llm_used=False,
            )

        # Записать взаимодействие в память (с fallback при ошибке БД)
        if self._memory and reader_id:
            try:
                provenance = (
                    response.provenance if hasattr(response, "provenance") else []
                )
                await self._reader_pulse.record(
                    reader_id=reader_id,
                    question=query,
                    answer=response.text,
                    topic=topic or response.source.split(":")[-1],
                    pulse_source=response.source,
                    provenance=provenance,
                )
            except Exception:
                pass

        # Option B, t1: Knowledge Context ПОСЛЕ выбора слоя и ДО LLM-фразировки.
        # contexts переиспользуются роутом /book/ask для metadata-дельты;
        # facts_block подмешивается в voice_prompt только при релевантной проекции.
        knowledge_context: list[dict] | None = None
        facts_block = ""
        if self._kc_provider:
            kc_started = time.perf_counter()
            try:
                payload = self._kc_provider(query, response.text)
            except Exception as exc:
                log.warning("dialogue_context_provider_error %s", exc)
                payload = None
            if isinstance(payload, dict):
                knowledge_context = payload.get("contexts") or []
                facts_block = str(payload.get("facts_block") or "")
            log.info(
                "dialogue_context_ms=%d contexts=%d facts_block_len=%d",
                int((time.perf_counter() - kc_started) * 1000),
                len(knowledge_context or []),
                len(facts_block),
            )

        log.info("voice_speak_start query=%s reader_id=%s", query[:50], reader_id)
        log.info(
            "voice_speak_check llm=%s type=%s",
            self._llm is not None,
            type(self._llm).__name__ if self._llm else "None",
        )
        if self._llm:
            log.info("voice_llm_calling query=%s", query[:50])
            is_deepen = "deepen_topic" in reader_ctx
            try:
                context = self._pulse.build_context()
                log.info("voice_llm_context_len=%d", len(context))

                # Добавить контекст читателя, если есть (не критично)
                if self._memory and reader_id:
                    try:
                        reader_info = await self._memory.build_reader_context(reader_id)
                        if reader_info:
                            context += f"\n\nКонтекст читателя:\n{reader_info}"
                    except Exception:
                        pass

                # Option B: блок материалов Knowledge Core для обеих веток prompt.
                kc_section = f"{facts_block}\n\n" if facts_block else ""
                if is_deepen:
                    voice_prompt = (
                        f"Читатель просит углубить тему «{reader_ctx.get('deepen_topic', '')}». "
                        f"Ранее ему было сказано:\n{reader_ctx.get('last_answer', '')}\n\n"
                        f"{kc_section}"
                        f"СТРОГИЕ ПРАВИЛА:\n"
                        f"1. Отвечай ТОЛЬКО на основе фактов из книги.\n"
                        f"2. Не придумывай, не дополняй, не интерпретируй.\n"
                        f"3. Если информации мало — скажи об этом честно.\n"
                        f"Ответь глубже, используя только факты из книги. 2-3 предложения."
                    )
                else:
                    dialogue_context = ""
                    if messages:
                        for m in messages[-6:]:
                            role = "Читатель" if m.get("role") == "user" else "Книга"
                            dialogue_context += (
                                f"{role}: {m.get('content', '')[:200]}\n"
                            )

                    voice_prompt = (
                        f"Предыдущий диалог:\n{dialogue_context}\n"
                        f"Читатель спрашивает: {query}\n\n"
                        f"Я знаю из книги:\n{response.text}\n\n"
                        f"{kc_section}"
                        f"СТРОГИЕ ПРАВИЛА:\n"
                        f"1. Отвечай ТОЛЬКО на основе фактов из «Я знаю из книги» выше.\n"
                        f"2. Не используй общие темы книги для описания персонажей.\n"
                        f"3. Не придумывай, не дополняй, не интерпретируй.\n"
                        f"4. Не спорь с читателем — если он прав, согласись.\n"
                        f"5. «Хранитель» — это роль КНИГИ, а не персонажей.\n"
                        f"6. Если информации мало — скажи об этом честно.\n"
                        f"2-3 предложения."
                    )

                log.info("voice_llm_prompt_len=%d calling_chat", len(voice_prompt))
                log.info("voice_llm_prompt_len=%d calling_chat", len(voice_prompt))
                llm_text = await self._llm.chat(
                    [
                        {"role": "system", "content": context},
                        {"role": "user", "content": voice_prompt},
                    ]
                )
                log.info("voice_llm_response_len=%d", len(llm_text))

                identity = self._pulse.layers.get("identity")
                identity_passed = True
                identity_type = "ok"
                if identity and hasattr(identity, "validate_detail"):
                    result = identity.validate_detail(llm_text)
                    identity_passed = result["passed"]
                    identity_type = result.get("type", "unknown")
                    if not identity_passed:
                        log.warning(
                            "voice_identity_blocked trigger=%s type=%s topic=%s",
                            result.get("trigger", "?"),
                            identity_type,
                            query[:60],
                        )
                if not identity_passed:
                    if identity_type == "external_knowledge":
                        # LLM галлюцинировал — вернуть ответ Pulse напрямую
                        llm_text = response.text
                    else:
                        # Нарушение идентичности — честное незнание
                        llm_text = "Извините, я не могу ответить на этот вопрос. Могу рассказать о содержании книги."

                return Utterance(
                    text=llm_text,
                    source=response.source,
                    pulse_response=response,
                    llm_used=True,
                    llm_model=getattr(self._llm, "model", "unknown"),
                    reader_topic=topic,
                    reader_depth=depth,
                    mood=mood,
                    knowledge_context=knowledge_context,
                )
            except Exception as e:
                log.error("voice_llm_error %s: %s", type(e).__name__, str(e)[:200])

        # Проверить response.text на identity (на случай, если Pulse вернул невалидное)
        identity = self._pulse.layers.get("identity")
        final_text = response.text
        if identity and hasattr(identity, "validate_detail"):
            result = identity.validate_detail(final_text)
            if not result["passed"]:
                log.warning(
                    "voice_pulse_identity_violation trigger=%s type=%s",
                    result.get("trigger", "?"),
                    result.get("type", "unknown"),
                )
                final_text = "Извините, я не могу ответить на этот вопрос. Могу рассказать о содержании книги."

        # Если есть история диалога — добавить связь с предыдущим
        if messages and len(messages) > 0 and not final_text.startswith("Как мы"):
            last_assistant = ""
            for m in reversed(messages):
                if m.get("role") == "assistant":
                    last_assistant = m.get("content", "")[:100]
                    break
            if last_assistant:
                # Простая связка с предыдущим ответом
                if "Велик" in last_assistant and "Велик" in final_text:
                    final_text = (
                        f"Как мы уже говорили о Великом — {final_text.lower().lstrip()}"
                    )
                elif "Атлантида" in last_assistant and "Атлантида" in final_text:
                    final_text = (
                        f"Возвращаясь к Атлантиде — {final_text.lower().lstrip()}"
                    )

        log.info("voice_speak_end source=%s llm_used=False", response.source)
        return Utterance(
            text=final_text,
            source=response.source,
            pulse_response=response,
            llm_used=False,
            reader_topic=topic,
            reader_depth=depth,
            mood=mood,
            knowledge_context=knowledge_context,
        )
