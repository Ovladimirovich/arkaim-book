"""Story Engine API Routes — /book/story-engine/*.

Полный pipeline с best-effort error handling:
  Request → CanonValidator → ContextAssembler → UnifiedPlanner → Composer → LLM → Response

Каждый этап возвращает StageResult. Pipeline продолжает работу даже при ошибках.
LLM получает всё что удалось собрать.
"""

import json
import uuid
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth.rbac import require_role

from narrative_engine.world_model import WorldModel
from narrative_engine.constraint_engine import StoryRequest, parse_prompt
from narrative_engine.canon_validator import CanonValidator, CanonCheckResult
from narrative_engine.context_assembler import ContextAssembler, FullContext
from narrative_engine.planner import UnifiedPlanner, NarrativePlan
from narrative_engine.story.composer import compose_prompt, format_composer_prompt
from narrative_engine.story.post_validator import (
    validate_story,
    validate_story_with_plan,
)
from narrative_engine.pipeline_errors import (
    PipelineResult,
    run_stage,
    run_stage_with_fallback,
)

log = logging.getLogger("hermes.narrative.story_api")

router = APIRouter(prefix="/story-engine", tags=["Story Engine"])

from narrative_engine.story import store


class GenerateRequest(BaseModel):
    prompt: str
    epoch: str | None = None
    location: str | None = None
    character_type: str | None = None
    max_length: int = 2000
    style: str = "literary"


@router.post(
    "/parse", summary="Парсинг промпта", dependencies=[Depends(require_role("reader"))]
)
async def parse(request: StoryRequest):
    parsed = parse_prompt(request.prompt)
    return {"ok": True, "data": parsed.model_dump()}


@router.post(
    "/constraints",
    summary="Построение модели ограничений (canon-aware)",
    dependencies=[Depends(require_role("reader"))],
)
async def get_constraints(request: StoryRequest):
    wm = WorldModel.load()
    validator = CanonValidator(wm)
    canon_result = validator.validate(request)
    return {"ok": True, "data": canon_result.constraints.model_dump()}


@router.post(
    "/generate",
    summary="Генерация истории (полный pipeline, SSE streaming)",
    dependencies=[Depends(require_role("reader"))],
)
async def generate(request: GenerateRequest):
    """Генерация истории с best-effort pipeline и SSE streaming.

    SSE события:
    - pipeline_status — статус каждого этапа
    - constraints — модель ограничений
    - canon_check — результат canon-валидации
    - narrative_plan — план повествования
    - chunk — кусочки текста
    - done — финальный результат
    - error — ошибка
    """
    pipeline_start = time.time()
    pipeline = PipelineResult()

    # ── 1. Парсинг промпта ──
    parsed = parse_prompt(request.prompt)
    if request.epoch:
        parsed.epoch = request.epoch
    if request.location:
        parsed.location = request.location
    if request.character_type:
        parsed.character_type = request.character_type
    parsed.max_length = request.max_length
    parsed.style = request.style

    # ── 2. Canon-валидация (best-effort) ──
    wm = WorldModel.load()
    validator = CanonValidator(wm)
    canon_stage = run_stage("canon_validator", validator.validate, parsed)
    pipeline.add(canon_stage)

    if canon_stage.ok and canon_stage.data:
        canon_result: CanonCheckResult = canon_stage.data
    else:
        # Fallback: минимальный CanonCheckResult
        from narrative_engine.constraint_engine import build_constraints

        constraints = build_constraints(parsed, wm)
        canon_result = CanonCheckResult(
            valid=True,
            constraints=constraints,
            warnings=[f"CanonValidator failed: {canon_stage.error}"],
        )

    constraints = canon_result.constraints

    # ── 3. Сборка контекста (best-effort) ──
    assembler = ContextAssembler(wm)
    context_stage = run_stage_with_fallback(
        "context_assembler",
        assembler.assemble,
        lambda: FullContext(world_state=constraints.resolved_context.model_dump()),
        canon_result,
    )
    pipeline.add(context_stage)

    full_context: FullContext = (
        context_stage.data
        if context_stage.ok
        else FullContext(
            world_state=constraints.resolved_context.model_dump(),
        )
    )

    # ── 4. Планирование (best-effort) ──
    planner = UnifiedPlanner(wm)
    plan_stage = run_stage_with_fallback(
        "unified_planner",
        planner.plan,
        lambda: NarrativePlan(),
        parsed,
        full_context,
    )
    pipeline.add(plan_stage)

    narrative_plan: NarrativePlan = (
        plan_stage.data if plan_stage.ok else NarrativePlan()
    )

    # ── 5. Composer ──
    composer_stage = run_stage(
        "composer",
        compose_prompt,
        constraints,
        full_context,
        narrative_plan,
        request.style,
        request.max_length,
    )
    pipeline.add(composer_stage)

    if composer_stage.ok and composer_stage.data:
        composed = composer_stage.data
    else:
        # Fallback: минимальный промпт
        composed = {
            "system_instruction": "Ты — писатель в мире «Наследие Аркаима».",
            "user_prompt": request.prompt,
        }

    full_prompt = format_composer_prompt(composed)
    brief = {
        "system_instruction": composed["system_instruction"],
        "world_context": composed["user_prompt"],
    }

    # Story ID
    story_id = str(uuid.uuid4())[:8]
    pipeline.total_duration_ms = (time.time() - pipeline_start) * 1000

    async def event_stream() -> AsyncGenerator[str, None]:
        # 1. Отправляем статус pipeline
        yield f"data: {json.dumps({'type': 'pipeline_status', 'data': pipeline.summary()}, default=str)}\n\n"

        # 2. Отправляем ограничения
        yield f"data: {json.dumps({'type': 'constraints', 'data': constraints.model_dump()}, default=str)}\n\n"

        # 3. Отправляем canon-валидацию
        yield f"data: {json.dumps({'type': 'canon_check', 'data': canon_result.model_dump()}, default=str)}\n\n"

        # 4. Отправляем narrative_plan
        yield f"data: {json.dumps({'type': 'narrative_plan', 'data': narrative_plan.model_dump()}, default=str)}\n\n"

        # 5. Генерируем текст через LLM (или заглушку)
        full_text = []
        try:
            async for chunk in _stream_generation(full_prompt, brief):
                full_text.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
        except Exception as e:
            log.error("story_generation_error error=%s", e)
            yield f"data: {json.dumps({'type': 'error', 'stage': 'llm_generation', 'message': str(e)})}\n\n"

        # 6. Собираем полный текст и валидируем (включая план)
        story_text = "".join(full_text)
        validation = validate_story_with_plan(
            story_text, constraints, wm, narrative_plan
        )

        # 7. Сохраняем в историю
        story_record = {
            "id": story_id,
            "text": story_text,
            "word_count": len(story_text.split()),
            "prompt": request.prompt,
            "constraints": constraints.model_dump(),
            "validation": validation.model_dump(),
            "narrative_plan": narrative_plan.model_dump(),
            "pipeline": pipeline.summary(),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        store.save_story(story_record)

        # 8. Отправляем финальный результат
        yield f"data: {json.dumps({'type': 'done', 'id': story_id, 'validation': validation.model_dump(), 'word_count': story_record['word_count'], 'pipeline_ok': pipeline.final_ok}, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/history",
    summary="История сгенерированных историй",
    dependencies=[Depends(require_role("reader"))],
)
async def get_history(limit: int = 20):
    return {"ok": True, "data": store.get_stories(limit)}


@router.get(
    "/history/{story_id}",
    summary="Конкретная история",
    dependencies=[Depends(require_role("reader"))],
)
async def get_story(story_id: str):
    story = store.get_story(story_id)
    if story:
        return {"ok": True, "data": story}
    raise HTTPException(404, "Story not found")


@router.post(
    "/validate",
    summary="Валидация текста по ограничениям",
    dependencies=[Depends(require_role("reader"))],
)
async def validate_text(text: str, request: StoryRequest):
    wm = WorldModel.load()
    validator = CanonValidator(wm)
    canon_result = validator.validate(request)
    validation = validate_story(text, canon_result.constraints, wm)
    return {"ok": True, "data": validation.model_dump()}


async def _stream_generation(prompt: str, brief: dict) -> AsyncGenerator[str, None]:
    """Генерация текста через LLM с streaming и retry."""
    max_retries = 2
    providers_tried = []

    for attempt in range(max_retries + 1):
        try:
            from providers.registry import ProviderRegistry

            messages = [
                {"role": "system", "content": brief.get("system_instruction", "")},
                {"role": "user", "content": prompt},
            ]

            for provider_name in ["gigachat", "openrouter"]:
                if provider_name in providers_tried:
                    continue
                try:
                    provider = ProviderRegistry.get(provider_name)
                    if not provider:
                        continue
                    async for token in provider.stream(messages):
                        if token.startswith("data: "):
                            try:
                                chunk = json.loads(token[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                                    await asyncio.sleep(0)
                            except (json.JSONDecodeError, IndexError, KeyError):
                                pass
                        elif token.startswith("data: [DONE]"):
                            continue
                        elif token and not token.startswith("data:"):
                            yield token
                            await asyncio.sleep(0)
                    return  # Success
                except Exception as e:
                    providers_tried.append(provider_name)
                    log.warning(
                        "story_provider_failed provider=%s attempt=%d error=%s",
                        provider_name,
                        attempt,
                        e,
                    )
                    continue

            # All providers failed — use stub
            log.warning("all_providers_failed_using_stub")
            async for chunk in _stream_stub(prompt, brief):
                yield chunk
            return

        except ImportError:
            async for chunk in _stream_stub(prompt, brief):
                yield chunk
            return

    # All retries exhausted
    async for chunk in _stream_stub(prompt, brief):
        yield chunk


async def _stream_stub(prompt: str, brief: dict) -> AsyncGenerator[str, None]:
    """Заглушка для генерации — имитирует streaming текста."""
    epoch_label = "Сатья Юга"
    loc_label = "Гиперборея"
    world_ctx = brief.get("world_context", "")
    if "ЭПОХА:" in world_ctx:
        epoch_label = world_ctx.split("ЭПОХА:")[1].split("\n")[0].strip()
    if "ЛОКАЦИЯ:" in world_ctx:
        loc_label = world_ctx.split("ЛОКАЦИЯ:")[1].split("\n")[0].strip()

    char_label = "ученик"
    prompt_lower = prompt.lower()
    if "жрец" in prompt_lower:
        char_label = "жрец"
    elif "воин" in prompt_lower:
        char_label = "воин"
    elif "мудрец" in prompt_lower:
        char_label = "мудрец"
    elif "странник" in prompt_lower:
        char_label = "странник"
    elif "учитель" in prompt_lower:
        char_label = "учитель"
    elif "царь" in prompt_lower or "князь" in prompt_lower:
        char_label = "князь"

    stub_text = (
        f"В древней {loc_label}, в эпоху {epoch_label}, жил молодой {char_label}. "
        f"Каждое утро он поднимался на вершину холма, чтобы встретить рассвет. "
        f"Солнечные лучи касались его лица, и он чувствовал древнюю мудрость, "
        f"пронизывающую каждую травинку, каждый камень.\n\n"
        f"«Сегодня ты узнаешь нечто важное», — сказал ему Учитель. "
        f"«Мир помнит то, что люди забыли. И ты должен стать мостом между прошлым и будущим.»\n\n"
        f"{char_label.capitalize()} не понял слов, но почувствовал их глубину. "
        f"Он знал: путь познания — это не цель, а сам процесс движения."
    )

    paragraphs = stub_text.split("\n\n")
    for para in paragraphs:
        words = para.split()
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i : i + 3]) + " "
            yield chunk
            await asyncio.sleep(0.05)
        yield "\n\n"
        await asyncio.sleep(0.1)
