import json
import pytest
from fastapi.testclient import TestClient
from electronics_mcp.core.database import Database
from electronics_mcp.web.app import app


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    app.state.db = db
    # Seed some data
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO circuits (id, name, description, schema_json, status) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c1", "Test RC", "A test circuit",
             json.dumps({"name": "test", "components": [
                 {"id": "R1", "type": "resistor",
                  "parameters": {"resistance": "1k"}, "nodes": ["in", "out"]},
             ]}), "draft"),
        )
        conn.execute(
            "INSERT INTO knowledge (id, category, topic, title, content, "
            "formulas, related_topics, difficulty, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("k1", "design_rule", "decoupling", "Decoupling Caps",
             "Place decoupling capacitors close to IC power pins for noise reduction.",
             "[]", "[]", "beginner", "test"),
        )
    return TestClient(app)


class TestIndexPage:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "ElectronicsMCP" in resp.text

    def test_index_has_nav_links(self, client):
        resp = client.get("/")
        assert "/circuits" in resp.text
        assert "/components" in resp.text
        assert "/knowledge" in resp.text


class TestCircuitViews:
    def test_list_circuits(self, client):
        resp = client.get("/circuits")
        assert resp.status_code == 200
        assert "Test RC" in resp.text

    def test_circuit_detail(self, client):
        resp = client.get("/circuits/c1")
        assert resp.status_code == 200
        assert "Test RC" in resp.text

    def test_circuit_not_found(self, client):
        resp = client.get("/circuits/nonexistent")
        assert resp.status_code == 404


class TestKnowledgeViews:
    def test_list_knowledge(self, client):
        resp = client.get("/knowledge")
        assert resp.status_code == 200
        assert "Decoupling" in resp.text

    def test_knowledge_detail(self, client):
        resp = client.get("/knowledge/k1")
        assert resp.status_code == 200
        assert "decoupling" in resp.text.lower()


class TestComponentViews:
    def test_list_components_empty(self, client):
        resp = client.get("/components")
        assert resp.status_code == 200

    def test_component_not_found(self, client):
        resp = client.get("/components/nonexistent")
        assert resp.status_code == 404


class TestComponentSearch:
    def test_search_page_renders(self, client):
        resp = client.get("/components/search")
        assert resp.status_code == 200
        assert "Component Search" in resp.text

    def test_search_with_query(self, client):
        resp = client.get("/components/search?q=test")
        assert resp.status_code == 200

    def test_search_with_type_filter(self, client):
        resp = client.get("/components/search?type=resistor")
        assert resp.status_code == 200


class TestSubcircuitViews:
    def test_list_subcircuits_empty(self, client):
        resp = client.get("/subcircuits")
        assert resp.status_code == 200


class TestAPIEndpoints:
    def test_api_circuits(self, client):
        resp = client.get("/api/circuits")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test RC"

    def test_api_search_knowledge(self, client):
        resp = client.get("/api/knowledge/search?q=decoupling")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
