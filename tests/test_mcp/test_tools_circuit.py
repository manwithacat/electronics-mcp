import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import (
    define_circuit, modify_circuit, get_circuit,
    validate_circuit, list_circuits, clone_circuit, delete_circuit,
)
import electronics_mcp.mcp.server as srv


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project):
    """Point the MCP server at a temp project."""
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize()
    yield
    srv._config = None
    srv._db = None


RC_FILTER_JSON = json.dumps({
    "name": "RC Low-Pass",
    "components": [
        {"id": "V1", "type": "voltage_source", "subtype": "ac",
         "parameters": {"amplitude": "1V"}, "nodes": ["input", "gnd"]},
        {"id": "R1", "type": "resistor",
         "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
        {"id": "C1", "type": "capacitor",
         "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
    ]
})


class TestCircuitTools:
    def test_define_and_list(self):
        result = define_circuit(RC_FILTER_JSON)
        assert "created" in result.lower()
        assert "RC Low-Pass" in result

        listing = list_circuits()
        assert "RC Low-Pass" in listing

    def test_modify_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        mod_json = json.dumps({
            "update": [{"id": "R1", "parameters": {"resistance": "22k"}}]
        })
        mod_result = modify_circuit(circuit_id, mod_json)
        assert "version 2" in mod_result

    def test_get_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        schema_json = get_circuit(circuit_id)
        schema = json.loads(schema_json)
        assert schema["name"] == "RC Low-Pass"

    def test_validate_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        validation = validate_circuit(circuit_id)
        assert "no issues" in validation.lower() or "validation" in validation.lower()

    def test_clone_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        clone_result = clone_circuit(circuit_id, "RC Variant")
        assert "Cloned" in clone_result
        assert "RC Variant" in clone_result

    def test_delete_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        delete_result = delete_circuit(circuit_id)
        assert "deleted" in delete_result.lower()

        listing = list_circuits()
        assert "No circuits" in listing
