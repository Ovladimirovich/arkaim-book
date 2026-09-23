"""Tests for World Engine integration."""
import pytest
import sys
sys.path.insert(0, '../core/CORE')


@pytest.fixture
def world_engine():
    """Create a fresh WorldEngine for testing."""
    from narrative_engine.world_engine import WorldEngine
    engine = WorldEngine()
    engine.initialize()
    return engine


class TestWorldModelExt:
    """Tests for WorldModelExt."""

    def test_load_all_categories(self, world_engine):
        """Test that all categories are loaded."""
        categories = world_engine._world_model.get_categories()
        assert len(categories) > 0
        assert "geography" in categories
        assert "philosophy" in categories

    def test_get_category(self, world_engine):
        """Test getting a specific category."""
        geo = world_engine._world_model.get_category("geography")
        assert len(geo) > 0
        assert all("id" in item for item in geo)

    def test_search(self, world_engine):
        """Test search functionality."""
        results = world_engine._world_model.search("Аркаим")
        assert len(results) > 0

    def test_stats(self, world_engine):
        """Test statistics."""
        stats = world_engine._world_model.get_stats()
        assert stats["total_entities"] > 400
        assert stats["total_categories"] >= 13


class TestRelationGraph:
    """Tests for RelationGraph."""

    def test_load_relations(self, world_engine):
        """Test that relations are loaded."""
        graph = world_engine._relation_graph
        assert graph is not None
        stats = graph.get_stats()
        assert stats["total_relations"] > 200

    def test_get_neighbors(self, world_engine):
        """Test getting neighbors."""
        neighbors = world_engine._relation_graph.get_neighbors("region_arkaim")
        assert len(neighbors) > 0

    def test_find_path(self, world_engine):
        """Test finding a path between entities."""
        path = world_engine._relation_graph.find_path("region_arkaim", "region_hyperborea")
        assert path is not None
        assert path.path_length > 0


class TestFormEngine:
    """Tests for FormEngine."""

    def test_build_form_context(self, world_engine):
        """Test building form context."""
        context = world_engine.form_engine.build_form_context("region_arkaim")
        assert context is not None
        assert len(context.forms) > 0

    def test_generate_visual_prompt(self, world_engine):
        """Test generating visual prompt."""
        prompt = world_engine.form_engine.generate_visual_prompt("region_arkaim")
        assert len(prompt) > 50

    def test_get_available_forms(self, world_engine):
        """Test getting available forms."""
        forms = world_engine.form_engine.get_available_forms()
        assert len(forms) > 0
        assert "architecture" in forms


class TestConsistencyEngine:
    """Tests for ConsistencyEngine."""

    def test_get_rules(self, world_engine):
        """Test getting rules."""
        rules = world_engine.consistency.get_rules()
        assert len(rules) > 0
        assert all(hasattr(r, "id") for r in rules)

    def test_validate_entity(self, world_engine):
        """Test validating an entity."""
        entity = {
            "id": "test_entity",
            "name": "Test Entity",
            "category": "geography",
            "description": "A test entity"
        }
        report = world_engine.consistency.validate_entity(entity)
        assert report.score > 0.5


class TestExperienceEngine:
    """Tests for ExperienceEngine."""

    def test_get_available_modes(self, world_engine):
        """Test getting available modes."""
        modes = world_engine.experience.get_available_modes()
        assert len(modes) > 0
        assert any(m["mode"] == "dialog" for m in modes)

    def test_create_path(self, world_engine):
        """Test creating an experience path."""
        from narrative_engine.experience_engine import ExperienceMode
        path = world_engine.experience.create_path(ExperienceMode.DIALOG)
        assert path is not None
        assert path.mode == ExperienceMode.DIALOG


class TestWorldEngine:
    """Tests for WorldEngine integration."""

    def test_search(self, world_engine):
        """Test world search."""
        results = world_engine.search("Аркаим")
        assert results["total"] > 0

    def test_get_entity(self, world_engine):
        """Test getting an entity."""
        entity = world_engine.get_entity("region_arkaim")
        assert entity is not None
        assert entity["id"] == "region_arkaim"

    def test_get_entity_context(self, world_engine):
        """Test getting entity context."""
        context = world_engine.get_entity_context("region_arkaim")
        assert "entity" in context
        assert "relations" in context

    def test_summary(self, world_engine):
        """Test world summary."""
        summary = world_engine.summary()
        assert "сущностей" in summary

    def test_stats(self, world_engine):
        """Test world stats."""
        stats = world_engine.get_stats()
        assert "world_model" in stats
        assert "relation_graph" in stats
