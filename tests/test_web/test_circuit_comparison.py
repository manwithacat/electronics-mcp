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
    with db.connect() as conn:
        for i in range(2):
            conn.execute(
                "INSERT INTO circuits (id, name, description, schema_json) "
                "VALUES (?, ?, ?, ?)",
                (f"c{i}", f"Circuit {i}", f"Test {i}",
                 json.dumps({"name": f"c{i}", "components": []})),
            )
        conn.execute(
            "INSERT INTO comparisons (id, name, description, circuit_ids, "
            "comparison_axes, results) VALUES (?, ?, ?, ?, ?, ?)",
            ("cmp1", "RC vs RL", "Filter comparison",
             json.dumps(["c0", "c1"]),
             json.dumps(["bandwidth", "attenuation"]),
             json.dumps({"c0": {"bandwidth": "1kHz"}, "c1": {"bandwidth": "2kHz"}})),
        )
    return TestClient(app)


class TestComparisonList:
    def test_list_comparisons(self, client):
        resp = client.get("/compare/")
        assert resp.status_code == 200
        assert "RC vs RL" in resp.text

    def test_empty_list(self, tmp_path):
        db = Database(tmp_path / "test2.db")
        db.initialize()
        app.state.db = db
        c = TestClient(app)
        resp = c.get("/compare/")
        assert resp.status_code == 200
        assert "No comparisons" in resp.text


class TestComparisonDetail:
    def test_detail_view(self, client):
        resp = client.get("/compare/cmp1")
        assert resp.status_code == 200
        assert "RC vs RL" in resp.text
        assert "Circuit 0" in resp.text
        assert "Circuit 1" in resp.text

    def test_detail_not_found(self, client):
        resp = client.get("/compare/nonexistent")
        assert resp.status_code == 404

    def test_comparison_data_endpoint(self, client):
        resp = client.get("/compare/cmp1/data")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["circuit_ids"]) == 2
        assert "bandwidth" in data["axes"]

    def test_comparison_data_not_found(self, client):
        resp = client.get("/compare/nonexistent/data")
        data = resp.json()
        assert "error" in data

    def test_comparison_run_endpoint(self, client):
        resp = client.post("/compare/cmp1/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "circuits" in data
        # Both circuits should be in results
        assert "c0" in data["circuits"]
        assert "c1" in data["circuits"]

    def test_comparison_run_not_found(self, client):
        resp = client.post("/compare/nonexistent/run")
        assert resp.status_code == 404
