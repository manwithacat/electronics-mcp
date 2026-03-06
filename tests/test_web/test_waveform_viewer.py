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
        conn.execute(
            "INSERT INTO circuits (id, name, description, schema_json) "
            "VALUES (?, ?, ?, ?)",
            (
                "c1",
                "Test Circuit",
                "A test",
                json.dumps({"name": "test", "components": []}),
            ),
        )
        conn.execute(
            "INSERT INTO simulation_results "
            "(id, circuit_id, analysis_type, parameters, results_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "sim1",
                "c1",
                "transient",
                json.dumps({"duration": 0.01}),
                json.dumps(
                    {"time": [0, 0.001, 0.002], "signals": {"vout": [0, 2.5, 5.0]}}
                ),
            ),
        )
    return TestClient(app)


class TestWaveformViewer:
    def test_viewer_renders(self, client):
        resp = client.get("/waveforms/c1")
        assert resp.status_code == 200
        assert "Waveform Viewer" in resp.text
        assert "transient" in resp.text

    def test_viewer_not_found(self, client):
        resp = client.get("/waveforms/nonexistent")
        assert resp.status_code == 404

    def test_waveform_data_endpoint(self, client):
        resp = client.get("/waveforms/c1/data/sim1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analysis_type"] == "transient"
        assert "signals" in data["data"]

    def test_waveform_data_not_found(self, client):
        resp = client.get("/waveforms/c1/data/nonexistent")
        data = resp.json()
        assert "error" in data

    def test_waveform_data_normalizes_transient(self, client):
        """Test that transient data with 'voltage' key gets normalized to 'signals'."""
        db = client.app.state.db
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO simulation_results "
                "(id, circuit_id, analysis_type, parameters, results_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "sim2",
                    "c1",
                    "transient",
                    "{}",
                    json.dumps({"time": [0, 1], "voltage": [0, 5]}),
                ),
            )
        resp = client.get("/waveforms/c1/data/sim2")
        data = resp.json()["data"]
        assert "signals" in data
        assert "voltage" in data["signals"]

    def test_waveform_data_normalizes_ac(self, client):
        """Test that AC data with 'magnitude_db' gets normalized to 'magnitude'."""
        db = client.app.state.db
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO simulation_results "
                "(id, circuit_id, analysis_type, parameters, results_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "sim3",
                    "c1",
                    "ac",
                    "{}",
                    json.dumps(
                        {"frequency": [1, 10, 100], "magnitude_db": [0, -3, -20]}
                    ),
                ),
            )
        resp = client.get("/waveforms/c1/data/sim3")
        data = resp.json()["data"]
        assert "magnitude" in data
        assert "magnitude_db" not in data

    def test_viewer_no_simulations(self, tmp_path):
        db = Database(tmp_path / "test2.db")
        db.initialize()
        app.state.db = db
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO circuits (id, name, description, schema_json) "
                "VALUES (?, ?, ?, ?)",
                ("c2", "Empty", "No sims", json.dumps({"name": "e", "components": []})),
            )
        c = TestClient(app)
        resp = c.get("/waveforms/c2")
        assert resp.status_code == 200
        assert "No simulation results" in resp.text
