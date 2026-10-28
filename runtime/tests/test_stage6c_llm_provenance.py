"""Этап 6c: LLM-часть knowledge_expansion — provenance и propose-only.

Проверяется реальный путь:
  LLM-ответ → EnrichedKnowledge с обязательной маркировкой
  SYSTEM_INTERPRETATION + requires_author_review → сохранение в
  KNOWLEDGE-файл без потери file-level provenance → граф не обновляется
  до авторской проверки.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge_expansion.enrichers.deep_analyzer import DeepAnalyzer  # noqa: E402
from knowledge_expansion.models import RawKnowledge, ValidatedKnowledge  # noqa: E402
from knowledge_expansion.store.knowledge_store import KnowledgeStore  # noqa: E402

_LLM_JSON = json.dumps(
    {
        "layers": {"literal": "буквально", "metaphorical": "метафора", "cosmic": "космос"},
        "cross_references": ["Аркаим"],
        "patterns": ["спираль"],
        "connections": [{"target": "Гиперборея", "type": "related_to", "description": "связь"}],
    },
    ensure_ascii=False,
)


class FakeLLM:
    """LLM-заглушка: возвращает заранее заданный ответ и пишет промпты."""

    def __init__(self, response: str = _LLM_JSON):
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        self.prompts.append(prompt)
        return self.response


class CountingStore:
    """Подмена graph-сторов: считает, что в них реально записали."""

    instances: list[CountingStore] = []

    def __init__(self):
        self.items: list[object] = []
        CountingStore.instances.append(self)

    def add(self, item: object) -> None:
        self.items.append(item)


def _raw(topic: str = "Тема") -> RawKnowledge:
    return RawKnowledge(source="test", topic=topic, content="Исходный текст")


def _review_item(topic: str = "LLM-тема") -> ValidatedKnowledge:
    return ValidatedKnowledge(
        source="test",
        topic=topic,
        content="LLM-контент",
        metadata={"_provenance_metadata": dict(DeepAnalyzer.LLM_PROVENANCE)},
    )


class TestDeepAnalyzerProvenance:
    async def test_llm_result_is_marked_as_review_candidate(self):
        analyzer = DeepAnalyzer(llm_client=FakeLLM())

        [item] = await analyzer.enrich([_raw()])

        prov = item.metadata["_provenance_metadata"]
        assert prov["source"] == "LLM"
        assert prov["requires_author_review"] is True
        assert prov["provenance_category"] == "SYSTEM_INTERPRETATION"
        assert prov["source_level"] == "SYSTEM_INTERPRETATION"
        assert prov["status"] == "PENDING_REVIEW"
        assert item.patterns == ["спираль"]
        assert item.connections[0]["target"] == "Гиперборея"

    async def test_empty_llm_response_is_not_marked_as_llm(self):
        analyzer = DeepAnalyzer(llm_client=FakeLLM(""))

        [item] = await analyzer.enrich([_raw()])

        assert "_provenance_metadata" not in item.metadata
        assert item.layers["literal"] == "Исходный текст"

    async def test_without_llm_no_provenance_is_added(self):
        analyzer = DeepAnalyzer(llm_client=None)

        [item] = await analyzer.enrich([_raw()])

        assert "_provenance_metadata" not in item.metadata


class TestKnowledgeStoreProposeOnly:
    async def test_wrapped_file_keeps_provenance_and_appends(self, tmp_path: Path):
        output = tmp_path / "PHILOSOPHY_DEEP.json"
        output.write_text(
            json.dumps(
                {
                    "_provenance_metadata": {
                        "category": "DERIVED",
                        "source_level": "SYSTEM_INTERPRETATION",
                        "notes": "seed",
                    },
                    "items": [{"topic": "Старая тема"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        store = KnowledgeStore(knowledge_dir=tmp_path)

        result = await store.save([_review_item()], output)

        assert result.success is True
        assert result.items_saved == 1
        data = json.loads(output.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "file-level обёртка потеряна"
        assert data["_provenance_metadata"]["notes"] == "seed"
        assert [item["topic"] for item in data["items"]] == ["Старая тема", "LLM-тема"]
        record = data["items"][1]["_provenance_metadata"]
        assert record["requires_author_review"] is True
        assert record["source"] == "LLM"

    async def test_bare_list_format_still_supported(self, tmp_path: Path):
        output = tmp_path / "OUT.json"
        output.write_text(json.dumps([{"topic": "Старая"}]), encoding="utf-8")
        store = KnowledgeStore(knowledge_dir=tmp_path)

        result = await store.save([_review_item()], output)

        assert result.items_saved == 1
        data = json.loads(output.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert [item["topic"] for item in data] == ["Старая", "LLM-тема"]

    async def test_unknown_file_format_is_not_overwritten(self, tmp_path: Path):
        output = tmp_path / "UNKNOWN.json"
        original = {"weird_key": "must stay"}
        output.write_text(json.dumps(original), encoding="utf-8")
        store = KnowledgeStore(knowledge_dir=tmp_path)

        result = await store.save([_review_item()], output)

        assert result.success is False
        assert json.loads(output.read_text(encoding="utf-8")) == original

    async def test_review_candidate_does_not_update_graph(self, tmp_path: Path, monkeypatch):
        import book_os.entity_store as entity_store
        import book_os.fact_store as fact_store
        import book_os.relationship_store as relationship_store

        CountingStore.instances = []
        monkeypatch.setattr(entity_store, "EntityStore", CountingStore)
        monkeypatch.setattr(relationship_store, "RelationshipStore", CountingStore)
        monkeypatch.setattr(fact_store, "FactStore", CountingStore)
        output = tmp_path / "OUT.json"
        store = KnowledgeStore(knowledge_dir=tmp_path)

        result = await store.save([_review_item()], output)

        assert result.graph_updates == 0
        assert all(not instance.items for instance in CountingStore.instances)

    async def test_non_review_item_still_updates_graph(self, tmp_path: Path, monkeypatch):
        import book_os.entity_store as entity_store
        import book_os.fact_store as fact_store
        import book_os.relationship_store as relationship_store

        CountingStore.instances = []
        monkeypatch.setattr(entity_store, "EntityStore", CountingStore)
        monkeypatch.setattr(relationship_store, "RelationshipStore", CountingStore)
        monkeypatch.setattr(fact_store, "FactStore", CountingStore)
        output = tmp_path / "OUT.json"
        store = KnowledgeStore(knowledge_dir=tmp_path)
        item = ValidatedKnowledge(source="test", topic="Обычная", content="Текст")

        result = await store.save([item], output)

        assert result.graph_updates >= 1
        assert any(instance.items for instance in CountingStore.instances)


class TestPipelineWithLlm:
    def test_default_pipeline_does_not_enable_llm_autonomously(self):
        from knowledge_expansion.pipeline import create_default_pipeline

        pipeline = create_default_pipeline()

        assert pipeline.enricher._llm is None, "фоновый путь не должен включать LLM сам"

    def test_explicit_llm_client_is_used(self):
        from knowledge_expansion.pipeline import create_default_pipeline

        llm = FakeLLM()

        pipeline = create_default_pipeline(llm_client=llm)

        assert pipeline.enricher._llm is llm

    def test_default_llm_client_requires_credentials(self, monkeypatch):
        from core.config import settings
        from knowledge_expansion.pipeline import default_llm_client

        monkeypatch.setattr(settings, "GIGACHAT_TOKEN", "")
        monkeypatch.setattr(settings, "GIGACHAT_CLIENT_ID", "")
        monkeypatch.setattr(settings, "GIGACHAT_CLIENT_SECRET", "")

        assert default_llm_client() is None

    async def test_llm_module_writes_candidate_without_graph_update(self, tmp_path: Path):
        from knowledge_expansion.pipeline import KnowledgeExpansionPipeline

        source = tmp_path / "SOURCE.json"
        source.write_text(
            json.dumps({"name": "Философия", "description": "Исходное описание"}, ensure_ascii=False),
            encoding="utf-8",
        )
        output = tmp_path / "DEEP.json"
        llm = FakeLLM()
        pipeline = KnowledgeExpansionPipeline(llm_client=llm)
        pipeline.store = KnowledgeStore(knowledge_dir=tmp_path)
        pipeline.register_module(
            "test_module",
            {"source_files": [source], "output_file": output},
        )

        result = await pipeline.run_module("test_module")

        assert result.success is True
        assert result.items_saved == 1
        assert result.graph_updates == 0, "LLM-кандидат не должен публиковаться в граф"
        assert llm.prompts, "LLM не был вызван"
        data = json.loads(output.read_text(encoding="utf-8"))
        prov = data[0]["metadata"]["_provenance_metadata"]
        assert prov["requires_author_review"] is True
        assert prov["provenance_category"] == "SYSTEM_INTERPRETATION"
