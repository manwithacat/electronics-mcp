import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.engines.knowledge.manager import KnowledgeManager
from electronics_mcp.mcp.resources import (
    get_topology_resource, get_component_resource,
    get_formulas_resource, get_knowledge_resource,
)
import electronics_mcp.mcp.server as srv


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project):
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize(seed=True)
    yield
    srv._config = None
    srv._db = None


class TestResources:
    def test_topology_resource_not_found(self):
        result = get_topology_resource("nonexistent")
        data = json.loads(result)
        assert "error" in data

    def test_topology_resource_found(self):
        km = KnowledgeManager(srv._db)
        km.learn_pattern("topology", "common_collector",
                         "Common Collector", "Unity gain buffer.")
        result = get_topology_resource("common_collector")
        data = json.loads(result)
        assert data["title"] == "Common Collector"

    def test_component_resource(self):
        result = get_component_resource("resistor")
        data = json.loads(result)
        assert data["type"] == "resistor"
        assert len(data["categories"]) > 0

    def test_formulas_resource(self):
        km = KnowledgeManager(srv._db)
        km.learn_pattern("topology", "ohms_law", "Ohm's Law", "V=IR",
                         formulas=[{"name": "V", "expression": "I*R"}])
        result = get_formulas_resource("ohms_law")
        data = json.loads(result)
        assert len(data["formulas"]) == 1

    def test_knowledge_resource(self):
        km = KnowledgeManager(srv._db)
        km.learn_pattern("general", "decoupling", "Decoupling Caps",
                         "Place 100nF caps near IC power pins.")
        result = get_knowledge_resource("decoupling")
        data = json.loads(result)
        assert data["title"] == "Decoupling Caps"
