import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import define_circuit
from electronics_mcp.mcp.tools_fabrication import (
    export_spice_netlist, export_kicad_netlist, export_bom,
    suggest_components, component_selection_guide,
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


RC_FILTER_JSON = json.dumps({
    "name": "RC Low-Pass",
    "components": [
        {"id": "V1", "type": "voltage_source", "subtype": "dc",
         "parameters": {"voltage": "5V"}, "nodes": ["input", "gnd"]},
        {"id": "R1", "type": "resistor",
         "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
        {"id": "C1", "type": "capacitor",
         "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
    ]
})


def _create_circuit():
    result = define_circuit(RC_FILTER_JSON)
    return result.split("ID: ")[1].split("\n")[0].strip()


class TestFabricationTools:
    def test_export_spice(self):
        cid = _create_circuit()
        result = export_spice_netlist(cid)
        assert "SPICE netlist saved" in result

    def test_export_kicad(self):
        cid = _create_circuit()
        result = export_kicad_netlist(cid)
        assert "KiCad netlist saved" in result

    def test_export_bom(self):
        cid = _create_circuit()
        result = export_bom(cid)
        assert "BOM saved" in result
        assert "Total components: 3" in result

    def test_suggest_components(self):
        result = suggest_components("resistor")
        assert isinstance(result, str)

    def test_selection_guide(self):
        result = component_selection_guide("resistor")
        assert "Selection Guide" in result or "guide" in result.lower()
