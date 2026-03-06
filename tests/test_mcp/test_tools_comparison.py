import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import define_circuit
from electronics_mcp.mcp.tools_comparison import (
    create_comparison,
    compare_boms,
    rank_designs,
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


def _make_circuit(name, r_value="10k"):
    schema = json.dumps(
        {
            "name": name,
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
                    "parameters": {"resistance": r_value},
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
    result = define_circuit(schema)
    return result.split("ID: ")[1].split("\n")[0].strip()


class TestComparisonTools:
    def test_create_comparison(self):
        cid1 = _make_circuit("Circuit A")
        cid2 = _make_circuit("Circuit B", "22k")
        result = create_comparison("Test Comparison", json.dumps([cid1, cid2]))
        assert "created" in result.lower()

    def test_compare_boms(self):
        cid1 = _make_circuit("Circuit A")
        cid2 = _make_circuit("Circuit B", "22k")
        result = compare_boms(json.dumps([cid1, cid2]))
        assert "Circuit A" in result
        assert "Circuit B" in result

    def test_rank_designs(self):
        cid1 = _make_circuit("Small")
        cid2 = _make_circuit("Also Small")
        result = rank_designs(json.dumps([cid1, cid2]))
        assert "Rankings" in result
