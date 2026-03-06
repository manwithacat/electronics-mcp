import json
import pytest
from fastapi.testclient import TestClient
from electronics_mcp.core.database import Database
from electronics_mcp.web.app import app


RC_SCHEMA = {
    "name": "rc_filter",
    "components": [
        {"id": "R1", "type": "resistor",
         "parameters": {"resistance": "1k"}, "nodes": ["in", "out"]},
        {"id": "C1", "type": "capacitor",
         "parameters": {"capacitance": "100n"}, "nodes": ["out", "gnd"]},
    ],
}


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    app.state.db = db
    schema_json = json.dumps(RC_SCHEMA)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO circuits (id, name, description, schema_json) "
            "VALUES (?, ?, ?, ?)",
            ("rc1", "RC Filter", "Test filter", schema_json),
        )
        conn.execute(
            "INSERT INTO circuit_versions (id, circuit_id, version, schema_json) "
            "VALUES (?, ?, 1, ?)",
            ("v1", "rc1", schema_json),
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

    def test_save_persists_changes(self, client):
        resp = client.post(
            "/explorer/rc1/save",
            data={"R1__resistance": "22k", "C1__capacitance": "100n"},
        )
        assert resp.status_code == 200
        assert "version 2" in resp.text.lower() or "Version: 2" in resp.text

        # Verify DB was updated
        db = app.state.db
        with db.connect() as conn:
            row = conn.execute(
                "SELECT schema_json FROM circuits WHERE id = 'rc1'"
            ).fetchone()
            schema = json.loads(row["schema_json"])
            r1 = next(c for c in schema["components"] if c["id"] == "R1")
            assert r1["parameters"]["resistance"] == "22k"

            versions = conn.execute(
                "SELECT version FROM circuit_versions WHERE circuit_id = 'rc1' ORDER BY version"
            ).fetchall()
            assert len(versions) == 2

    def test_save_no_changes(self, client):
        resp = client.post(
            "/explorer/rc1/save",
            data={"R1__resistance": "1k", "C1__capacitance": "100n"},
        )
        assert resp.status_code == 200
        assert "no parameter changes" in resp.text.lower()

    def test_save_not_found(self, client):
        resp = client.post(
            "/explorer/nonexistent/save",
            data={"R1__resistance": "22k"},
        )
        assert resp.status_code == 404
