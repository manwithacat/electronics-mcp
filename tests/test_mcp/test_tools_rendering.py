import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import define_circuit
from electronics_mcp.mcp.tools_rendering import (
    draw_schematic,
    render_bode,
    render_waveform,
    generate_circuit_report,
)
import electronics_mcp.mcp.server as srv


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project):
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize()
    yield
    srv._config = None
    srv._db = None


RC_FILTER_JSON = json.dumps(
    {
        "name": "RC Low-Pass",
        "components": [
            {
                "id": "V1",
                "type": "voltage_source",
                "subtype": "dc",
                "parameters": {"voltage": "5V"},
                "nodes": ["input", "gnd"],
            },
            {
                "id": "R1",
                "type": "resistor",
                "parameters": {"resistance": "10k"},
                "nodes": ["input", "output"],
            },
            {
                "id": "C1",
                "type": "capacitor",
                "parameters": {"capacitance": "10n"},
                "nodes": ["output", "gnd"],
            },
        ],
    }
)


def _create_circuit():
    result = define_circuit(RC_FILTER_JSON)
    return result.split("ID: ")[1].split("\n")[0].strip()


class TestRenderingTools:
    def test_draw_schematic(self):
        cid = _create_circuit()
        result = draw_schematic(cid)
        assert "Schematic saved" in result

    def test_render_bode(self):
        cid = _create_circuit()
        freqs = json.dumps([100, 1000, 10000])
        mag = json.dumps([-0.1, -3.0, -20.0])
        phase = json.dumps([-5, -45, -85])
        result = render_bode(cid, freqs, mag, phase)
        assert "Bode plot saved" in result

    def test_render_waveform(self):
        cid = _create_circuit()
        time = json.dumps([0, 0.001, 0.002, 0.003])
        signals = json.dumps({"output": [0, 3.2, 4.5, 4.9]})
        result = render_waveform(cid, time, signals)
        assert "Waveform plot saved" in result

    def test_generate_report(self):
        cid = _create_circuit()
        result = generate_circuit_report(cid, notes="Test report")
        assert "Report saved" in result
