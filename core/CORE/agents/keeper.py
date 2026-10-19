"""
Keeper Agent — Хранитель книги.

Главный эксперт по книге. Использует Pulse (живое ядро) для ответов.
LLM — только инструмент озвучки (BookVoice), не источник личности.
"""

import logging
from typing import Dict, Any, Optional
from agents.base import BaseAgent
from core_memory.logger import EventLogger
from pulse.pulse import BookPulse
from pulse.voice import BookVoice

log = logging.getLogger("hermes.keeper")


class KeeperAgent(BaseAgent):
    """
    Keeper — Хранитель идей книги.

    В отличие от старой версии, Keeper не имитирует личность через system prompt.
    Личность живёт в Pulse. Keeper только направляет вопрос в Pulse
    и возвращает ответ.
    """

    def __init__(
        self, pulse: Optional[BookPulse] = None, voice: Optional[BookVoice] = None
    ):
        super().__init__(
            name="Keeper",
            description="Хранитель книги 'Наследие Аркаима'. Отвечает на вопросы по книге.",
        )
        self.pulse = pulse
        self.voice = voice
        self.event_logger = EventLogger()

    def get_system_prompt(self) -> str:
        if self.pulse and self.pulse.is_loaded:
            return self.pulse.build_context()
        return ""

    async def act(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        question = input_data.get("question", "")
        reader_id = input_data.get("reader_id", "")
        reader_name = input_data.get("reader_name", "")
        messages = input_data.get("messages", [])

        if not self.pulse:
            return {
                "answer": "Система ещё не загрузила книгу. Попробуйте позже.",
                "source": "pulse_unavailable",
            }

        if not self.pulse.is_loaded:
            self.pulse.load()

        if self._is_spam(question):
            return {"answer": "", "source": "silence", "spam": True}

        if self.voice:
            log.info(
                "keeper_act voice=%s voice_llm=%s",
                self.voice is not None,
                self.voice._llm is not None if self.voice else "N/A",
            )
            utterance = await self.voice.speak(
                question,
                reader_id=reader_id,
                reader_name=reader_name,
                messages=messages,
            )
        else:
            response = self.pulse.listen(question)
            utterance_text = (
                response.text if response else "Я не нахожу ответа в книге."
            )

        answer_text = utterance.text if self.voice else utterance_text

        identity = self.pulse.layers.get("identity")
        identity_gate = {"passed": True, "trigger": ""}
        if identity and hasattr(identity, "validate_detail"):
            identity_gate = identity.validate_detail(answer_text)
            if not identity_gate["passed"]:
                answer_text = self._fallback_silence()

        layer_used = utterance.pulse_response.source if self.voice else "pulse"
        confidence = utterance.pulse_response.confidence if self.voice else 1.0
        rag_source = ""
        if "rag" in layer_used or "catalog" in layer_used:
            rag_source = layer_used

        self.event_logger.log_event(
            {
                "event_type": "keeper_answer",
                "topic": question[:100],
                "user_sentiment": "neutral",
                "system_action": "pulse_response",
                "outcome": "ok",
                "metadata": {
                    "identity_gate": identity_gate,
                    "answer_length": len(answer_text),
                    "source": utterance.source if self.voice else "pulse_direct",
                    "llm_used": utterance.llm_used if self.voice else False,
                    "layer_used": layer_used,
                    "confidence": confidence,
                    "rag_source": rag_source,
                    "intent": "question",
                },
            }
        )

        # Serialize provenance: ProvenanceTag → dict for JSON API
        if self.voice and hasattr(utterance.pulse_response, "get_provenance_dicts"):
            provenance = utterance.pulse_response.get_provenance_dicts()
        elif self.voice and hasattr(utterance.pulse_response, "provenance"):
            provenance = utterance.pulse_response.provenance
        else:
            provenance = []

        # Структурированная неопределённость
        uncertainty = None
        if (
            self.voice
            and hasattr(utterance.pulse_response, "uncertainty")
            and utterance.pulse_response.uncertainty
        ):
            u = utterance.pulse_response.uncertainty
            uncertainty = {
                "has_unknowns": u.has_unknowns,
                "unknown_aspects": u.unknown_aspects,
                "confidence_breakdown": u.confidence_breakdown,
            }

        # Инициатива книги — предложить уточняющий вопрос
        suggestion = self._suggest_followup(
            answer_text, utterance.mood if self.voice else "neutral", layer_used
        )

        result_payload = {
            "answer": answer_text,
            "source": utterance.source if self.voice else "pulse",
            "provenance": provenance,
            "uncertainty": uncertainty,
            "pulse_confidence": utterance.pulse_response.confidence
            if self.voice
            else 1.0,
            "llm_used": utterance.llm_used if self.voice else False,
            "mood": utterance.mood if self.voice else "neutral",
            "suggestion": suggestion,
        }
        # Option B, t1: внутренний канал Knowledge Context → /book/ask для
        # metadata-дельты. Роут снимает ключ ДО формирования публичного payload,
        # поэтому наружу он не попадает; без провайдера ключа нет вовсе.
        if self.voice and getattr(utterance, "knowledge_context", None):
            result_payload["_dialogue_context"] = utterance.knowledge_context
        return result_payload

    def _suggest_followup(self, answer: str, mood: str, source: str) -> str:
        """Предложить уточняющий вопрос на основе ответа и настроения."""
        import random

        suggestions = {
            "curiosity": [
                "Хотите узнать больше об этом?",
                "Вас интересует связь с другими темами?",
                "Хотите сравнить с другими персонажами?",
            ],
            "joy": [
                "В книге есть ещё удивительные моменты!",
                "Хотите узнать о связанных темах?",
                "Может, рассказать о символах?",
            ],
            "deep": [
                "Хотите углубиться в эту тему?",
                "В книге есть ещё глубокие ответы.",
                "Может, спросите о философии книги?",
            ],
            "neutral": [
                "Хотите узнать подробнее?",
                "Есть ещё вопросы по этой теме?",
            ],
        }

        pool = suggestions.get(mood, suggestions["neutral"])
        return random.choice(pool) if pool else ""

    def _is_spam(self, text: str) -> bool:
        if not text or len(text.strip()) < 3:
            return True
        if len(text) > 5:
            repeated = max(text.count(c) for c in set(text))
            if repeated / len(text) > 0.7:
                return True
        return False

    def _fallback_silence(self) -> str:
        return "Я не могу ответить на этот вопрос в рамках книги. Пожалуйста, переформулируйте."


class HeraldAgent(BaseAgent):
    """
    Herald — Вестник. Создатель контента.
    Использует Pulse для контекста и LLM только для формулировки.
    """

    def __init__(self, pulse: Optional[BookPulse] = None):
        super().__init__(
            name="Herald",
            description="Создатель контента на основе книги 'Наследие Аркаима'.",
        )
        self.pulse = pulse

    def set_pulse(self, pulse: BookPulse):
        self.pulse = pulse

    async def act(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from llm_client import llm

        content_type = input_data.get("content_type", "post")
        topic = input_data.get("topic", "")
        tone = input_data.get("tone", "спокойный, мудрый")

        context = ""
        if self.pulse and self.pulse.is_loaded:
            context = self.pulse.build_context()

        system_prompt = context + (
            "\n\nНапиши материал по теме, используя ТОЛЬКО знания из книги. "
            "Не придумывай факты. Голос — мудрый, спокойный."
        )
        user_prompt = f"Напиши {content_type} на тему '{topic}' в {tone} тоне."

        try:
            draft = await llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
        except Exception as e:
            draft = f"[Ошибка генерации] {e}"

        return {
            "draft": draft,
            "status": "pending_approval",
            "id": f"draft_{hash(topic) & 0xFFFFFFFF:08x}",
        }


class DiplomatAgent(BaseAgent):
    """
    Diplomat — Дипломат. Коммуникатор с сообществом.
    """

    def __init__(self, pulse: Optional[BookPulse] = None):
        super().__init__(
            name="Diplomat",
            description="Коммуникатор, пишет персонализированные сообщения.",
        )
        self.pulse = pulse

    def set_pulse(self, pulse: BookPulse):
        self.pulse = pulse

    async def act(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from llm_client import llm

        target = input_data.get("target", "")
        context_input = input_data.get("context", "")

        context = ""
        if self.pulse and self.pulse.is_loaded:
            context = self.pulse.build_context()

        system_prompt = context + (
            "\n\nНапиши письмо, используя ТОЛЬКО знания из книги. "
            "Будь уважителен и мудр. Не используй маркетинговые приёмы."
        )
        user_prompt = f"Напиши персонализированное сообщение для {target}. Контекст: {context_input}."

        try:
            draft = await llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
        except Exception as e:
            draft = f"[Ошибка генерации] {e}"

        return {
            "draft": draft,
            "status": "pending_approval",
        }
