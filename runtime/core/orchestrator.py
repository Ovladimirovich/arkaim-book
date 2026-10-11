import uuid
import time
import json
import logging

from core.provider_registry import ProviderRegistry
from core.identity.sanitizer import sanitize_response as identity_sanitize
from core.identity.policy import IdentityPolicy
from memory.store import MemoryStore
from memory.leads import LeadStore
from core.tools import ToolExecutor
from core.config import settings
from skills.base import SkillContext
from skills.registry import SkillRegistry
from observability.logging import log_event
from observability.metrics import metrics
from aethon.xray import (
    Event,
    emit,
    start_trace,
    start_span,
    set_current_trace_id,
    SpanKind,
    EventKind,
    ComponentKind,
    Severity,
    provider_failures,
    provider_latency,
    fallback_count,
)
from aethon.xray.http_propagation import make_xray_headers

log = logging.getLogger("hermes.core")


class Orchestrator:
    def __init__(self, business_pack: str | None = None) -> None:
        self.memory = MemoryStore()
        self.leads = LeadStore()
        self.tools = ToolExecutor()
        self.skills = SkillRegistry.discover(business_pack=business_pack)

    def _trace_id(self, req: dict) -> str:
        return req.get("trace_id", req.get("metadata", {}).get("session_id", uuid.uuid4().hex[:16]))

    async def chat(self, req: dict, user: dict) -> dict:
        trace_id = self._trace_id(req)
        set_current_trace_id(trace_id)
        correlation_id = req.get("metadata", {}).get("session_id", "")
        trace = start_trace("core.chat", trace_id=trace_id, correlation_id=correlation_id, metadata={"provider_chain": ",".join(settings.PROVIDER_CHAIN)})
        orch_span = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id, parent_span_id=req.get("parent_span_id") or None)
        metrics.increment("chat_started")
        provider_name = ProviderRegistry.select_provider(req.get("provider"))
        model = req.get("model", provider_name)
        from core.providers.ab_testing import ab_selector

        t0 = time.time()

        # Lightweight intent classifier based on keywords
        user_text = req["messages"][-1]["content"].lower() if req.get("messages") else ""
        intent = "chat"  # default
        if any(w in user_text for w in ["расскажи", "опиши", "объясни", "что такое", "кто такой", "как работает"]):
            intent = "factual"
        elif any(w in user_text for w in ["напиши", "сгенерируй", "создай", "придумай", "сочини"]):
            intent = "creative"
        elif any(w in user_text for w in ["проанализируй", "сравни", "оцени", "анализ", "статистика"]):
            intent = "analysis"
        elif "?" in user_text:
            intent = "question"

        session_id = req.get("metadata", {}).get("session_id", "default")

        ctx = SkillContext(
            messages=req["messages"],
            user=user.get("sub", ""),
            session_id=session_id,
            user_text=req["messages"][-1]["content"],
            memory=self.memory,
            trace_id=trace_id,
        )

        chain = ProviderRegistry.chain_healthy(provider_name)
        if not chain:
            chain = ProviderRegistry.chain(provider_name)
        system_prompts = []
        contexts = []
        final_response = None

        for skill in self.skills:
            metrics.increment("skill_executed")
            try:
                result = await skill.execute(ctx)
            except Exception as exc:
                log.warning("skill_error name=%s trace_id=%s error=%s", skill.name, trace_id, exc)
                continue
            if result.handled:
                final_response = result.response
                log_event(log, "skill_handled", name=skill.name, trace_id=trace_id)
                break
            if result.system_prompt:
                system_prompts.append(result.system_prompt)
            if result.context:
                contexts.append(result.context)

        if final_response is not None:
            await self.memory.store(req["messages"], final_response, session_id=session_id, user_id=user.get("user_id", ""))
            metrics.increment("memory_store")
            orch_span.end()
            trace.end()
            log_event(log, "skill_direct", trace_id=trace_id, latency_ms=(time.time() - t0) * 1000)
            return {
                "id": trace_id,
                "object": "chat.completion",
                "model": model,
                "intent": intent,
                "choices": [{"message": {"role": "assistant", "content": final_response}}],
            }

        # Safety: если skill вернул system_prompt/context без response — НЕ передавать LLM
        # LLM будет галлюцинировать без фактической базы
        if system_prompts or contexts:
            log.warning("skill_provided_context_no_response skills=%s — falling through to LLM", [s.name for s in self.skills])

        identity_prompt = IdentityPolicy.system_prompt()
        all_prompts = [identity_prompt] + system_prompts
        messages = list(req["messages"])
        if all_prompts:
            messages = [{"role": "system", "content": "\n\n".join(all_prompts)}] + messages
        if contexts:
            kb_text = "\n\n".join(contexts)
            augmented = f"[Ответь на основе информации ниже]\n\n{kb_text}\n\nВопрос: {ctx.user_text}"
            messages[-1] = {"role": "user", "content": augmented}

        context = await self.memory.retrieve(ctx.user_text, session_id=session_id)
        if context:
            metrics.increment("memory_hit")

        last_error = None
        incoming_xray = req.get("xray_headers", {})
        for idx, name in enumerate(chain):
            provider_t0 = time.time()
            span = start_span(SpanKind.PROVIDER_CALL, f"{name}.chat", trace_id=trace_id, parent_span_id=orch_span.span_id)
            # Build provider xray headers: increment depth + logical_ts per hop
            provider_xray = None
            if incoming_xray:
                p_logical_ts = int(incoming_xray.get("logical_ts", 0)) + 1
                p_depth = int(incoming_xray.get("causal_depth", 0)) + 1
                provider_xray = make_xray_headers(
                    trace_id=incoming_xray.get("trace_id", trace_id),
                    span_id=span.span_id,
                    parent_span_id=incoming_xray.get("span_id", ""),
                    logical_ts=p_logical_ts,
                    depth=p_depth,
                )
            try:
                provider = ProviderRegistry.get(name)
                metrics.increment("provider_selected")
                response = await provider.chat(messages, context=context, trace_id=trace_id, xray_headers=provider_xray)
                span.end()
                provider_latency_val = (time.time() - provider_t0) * 1000
                provider_latency.observe(provider_latency_val)
            except Exception as exc:
                span.end("error")
                provider_failures.inc()
                metrics.increment("provider_failed")
                await ProviderRegistry.areport_failure(name)
                emit(
                    Event(
                        time.time(),
                        trace_id,
                        ComponentKind.PROVIDER,
                        EventKind.PROVIDER_FAILED,
                        Severity.ERROR,
                        f"{name} failed",
                        {"provider": name, "error": str(exc)},
                    )
                )
                log.warning("provider_fallback provider=%s trace_id=%s error=%s", name, trace_id, exc)
                last_error = exc
                if idx + 1 < len(chain):
                    fallback_count.inc()
                    metrics.increment("fallback_triggered")
                continue
            await ProviderRegistry.areport_success(name)
            ab_selector.record_latency(name, (time.time() - provider_t0) * 1000)
            if idx > 0:
                emit(
                    Event(
                        time.time(),
                        trace_id,
                        ComponentKind.PROVIDER,
                        EventKind.PROVIDER_FALLBACK,
                        Severity.INFO,
                        f"fallback {chain[0]} -> {name}",
                        {"from": chain[0], "to": name},
                    )
                )
                log_event(log, "provider_fallback_success", from_provider=chain[0], to_provider=name, trace_id=trace_id)

            provider_latency_ms = (time.time() - provider_t0) * 1000
            content = response["choices"][0]["message"]["content"] if isinstance(response, dict) and "choices" in response else str(response)
            safe_response = identity_sanitize(content, provider=name, trace_id=trace_id)
            for skill in self.skills:
                try:
                    safe_response = await skill.post_process(safe_response, ctx)
                except Exception as exc:
                    log.warning("skill_post_process_error name=%s trace_id=%s error=%s", skill.name, trace_id, exc)

            await self.memory.store(req["messages"], safe_response, session_id=session_id, user_id=user.get("user_id", ""))
            metrics.increment("memory_store")
            metrics.increment("chat_ok")
            total_latency = (time.time() - t0) * 1000
            log_event(
                log,
                "chat_ok",
                provider=name,
                intent=intent,
                latency_ms=total_latency,
                provider_latency_ms=provider_latency_ms,
                trace_id=trace_id,
                session_id=session_id,
            )
            orch_span.end()
            trace.end("ok")
            return {
                "id": trace_id,
                "object": "chat.completion",
                "model": model,
                "intent": intent,
                "choices": [{"message": {"role": "assistant", "content": safe_response}}],
            }

        metrics.increment("chat_failed")
        total_latency = (time.time() - t0) * 1000
        log_event(log, "chat_failed", chain=",".join(chain), trace_id=trace_id, latency_ms=total_latency, error=str(last_error))
        orch_span.end("error")
        trace.end("error")
        return {"id": trace_id, "object": "chat.completion", "model": model, "intent": intent, "error": f"All providers failed: {last_error}"}

    async def stream(self, req: dict, user: dict):
        trace_id = self._trace_id(req)
        provider_name = req.get("provider", "gigachat")
        t0 = time.time()
        session_id = req.get("metadata", {}).get("session_id", "default")

        if not ProviderRegistry.is_registered(provider_name):
            metrics.increment("chat_failed")
            log_event(log, "provider_not_found", provider=provider_name, trace_id=trace_id)
            yield f'data: {{"error": "Provider {provider_name} not found"}}\n\n'
            yield "data: [DONE]\n\n"
            return

        metrics.increment("chat_started")
        ctx = SkillContext(
            messages=req["messages"],
            user=user.get("sub", ""),
            session_id=session_id,
            user_text=req["messages"][-1]["content"],
            memory=self.memory,
            trace_id=trace_id,
        )

        system_prompts = []
        contexts = []

        # Реальные поля провенанса (source/confidence/llm_used) из SkillResult.metadata.
        # Заполняются только если скилл их прислал — выдумывать значения нельзя.
        skill_meta: dict = {}
        for skill in self.skills:
            try:
                result = await skill.execute(ctx)
            except Exception:
                continue
            if result.handled:
                if result.metadata and not skill_meta:
                    skill_meta = dict(result.metadata)
                if result.system_prompt:
                    # Скилл хочет LLM-помощь с контекстом — добавляем промпт, но сохраняем прямой ответ как fallback
                    system_prompts.append(result.system_prompt)

                elif result.response:
                    # Скилл нашёл ответ — возвращаем напрямую, без LLM
                    metrics.increment("skill_direct_stream")
                    log.info("stream_skill_handled skill=%s", skill.name)
                    await self.memory.store(req["messages"], result.response, session_id=session_id, user_id=user.get("user_id", ""))
                    yield f"data: {json.dumps({'text': result.response})}\n\n"
                    yield self._related_entities_event(req, result.response)
                    provenance = self._provenance_event(skill_meta)
                    if provenance:
                        yield provenance
                    yield "data: [DONE]\n\n"
                    return
            else:
                if result.system_prompt:
                    system_prompts.append(result.system_prompt)
                if result.context:
                    contexts.append(result.context)

        identity_prompt = IdentityPolicy.system_prompt()
        all_prompts = [identity_prompt] + system_prompts
        messages = list(req["messages"])
        if all_prompts:
            messages = [{"role": "system", "content": "\n\n".join(all_prompts)}] + messages
        if contexts:
            kb_text = "\n\n".join(contexts)
            augmented = f"[Ответь на основе информации ниже]\n\n{kb_text}\n\nВопрос: {ctx.user_text}"
            messages[-1] = {"role": "user", "content": augmented}

        provider = ProviderRegistry.get(provider_name)
        token_count = 0
        full_response = []
        try:
            async for token in provider.stream(messages, trace_id=trace_id):
                token_count += 1
                # Провайдер отдаёт строки вида: data: {"choices":[{"delta":{"content":"..."}}]}
                # или просто текст. Нужно извлечь content и отправить как {text: "..."}
                content = ""
                if token.startswith("data: "):
                    try:
                        chunk = json.loads(token[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                    except Exception as e:
                        log.warning("caught_exception: %s", e)
                elif token.startswith("data: [DONE]"):
                    continue
                else:
                    content = token

                if content:
                    full_response.append(content)
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as exc:
            metrics.increment("chat_failed")
            log.error("stream_failed provider=%s tokens=%d trace_id=%s error=%s", provider_name, token_count, trace_id, exc)
        else:
            full_text = "".join(full_response)
            safe_text = identity_sanitize(full_text, provider=provider_name, trace_id=trace_id)
            yield self._related_entities_event(req, safe_text)
            provenance = self._provenance_event(skill_meta)
            if provenance:
                yield provenance
            for skill in self.skills:
                try:
                    safe_text = await skill.post_process(safe_text, ctx)
                except Exception as e:
                    log.warning("caught_exception: %s", e)
            await self.memory.store(req["messages"], safe_text, session_id=session_id, user_id=user.get("user_id", ""))
            metrics.increment("memory_store")
            metrics.increment("chat_ok")
            total_latency = (time.time() - t0) * 1000
            log_event(log, "stream_ok", provider=provider_name, tokens=token_count, latency_ms=total_latency, trace_id=trace_id, session_id=session_id)

        yield "data: [DONE]\n\n"

    @staticmethod
    def _related_entities_event(req: dict, answer: str) -> str:
        """SSE metadata frame compatible with existing text-delta consumers."""
        from core.services.related_entities import resolve_related_entities

        question = req.get("messages", [{}])[-1].get("content", "")
        related = resolve_related_entities({"question": question, "answer": answer})
        return f"data: {json.dumps({'related_entities': related}, ensure_ascii=False)}\n\n"

    @staticmethod
    def _provenance_event(skill_meta: dict) -> str | None:
        """Final provenance frame before [DONE].

        Maps real SkillResult.metadata onto the AskAnswer field names
        (source, pulse_confidence, llm_used) without inventing values:
        anything the skill did not send is omitted, not defaulted.
        """
        if not skill_meta:
            return None
        payload: dict = {}
        if skill_meta.get("source") is not None:
            payload["source"] = skill_meta["source"]
        if skill_meta.get("confidence") is not None:
            payload["pulse_confidence"] = skill_meta["confidence"]
        if skill_meta.get("llm_used") is not None:
            payload["llm_used"] = skill_meta["llm_used"]
        if not payload:
            return None
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def close(self):
        await self.memory.close()
        await self.leads.close()

    async def provider_health(self) -> list[dict]:
        return await ProviderRegistry.health()

    async def memory_health(self) -> dict:
        return await self.memory.health()
