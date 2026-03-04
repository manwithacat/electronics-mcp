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
    schema = {
        "name": "rc_filter",
        "components": [
            {"id": "R1", "type": "resistor",
             "parameters": {"resistance": "1k"}, "nodes": ["in", "out"]},
            {"id": "C1", "type": "capacitor",
             "parameters": {"capacitance": "100n"}, "nodes": ["out", "gnd"]},
        ],
    }
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO circuits (id, name, description, schema_json) "
            "VALUES (?, ?, ?, ?)",
            ("rc1", "RC Filter", "Test filter", json.dumps(schema)),
        )
    return TestClient(app)


class TestParameterExplorer:
    def test_explorer_renders(self, client):
        resp = client.get("/explorer/rc1")
        assert resp.status_code == 200
        assert "R1" in resp.text
        assert "resistance" in resp.text
        assert "C1" in resp.text

    def test_explorer_not_found(self, client):
        resp = client.get("/explorer/nonexistent")
        assert resp.status_code == 404

    def test_simulate_endpoint(self, client):
        resp = client.post(
            "/explorer/rc1/simulate",
            data={"R1__resistance": "2.2k", "C1__capacitance": "47n"},
        )
        assert resp.status_code == 200
        # Should contain real simulation results or parameter info
        assert "2.2k" in resp.text or "Simulation" in resp.text

    def test_simulate_with_analysis_type(self, client):
        resp = client.post(
            "/explorer/rc1/simulate",
            data={"R1__resistance": "1k", "C1__capacitance": "100n",
                  "analysis_type": "dc_op"},
        )
        assert resp.status_code == 200
        assert "dc_op" in resp.text or "Simulation" in resp.text

    def test_explorer_shows_component_types(self, client):
        resp = client.get("/explorer/rc1")
        assert "resistor" in resp.text
        assert "capacitor" in resp.text
