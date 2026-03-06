import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_subcircuit import (
    list_subcircuits,
    get_subcircuit,
    create_subcircuit,
    import_subcircuit,
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


VOLTAGE_DIVIDER = json.dumps(
    {
        "name": "voltage_divider",
        "components": [
            {
                "id": "R1",
                "type": "resistor",
                "parameters": {"resistance": "10k"},
                "nodes": ["input", "output"],
            },
            {
                "id": "R2",
                "type": "resistor",
                "parameters": {"resistance": "10k"},
                "nodes": ["output", "gnd"],
            },
        ],
    }
)


class TestSubcircuitTools:
    def test_create_and_list(self):
        result = create_subcircuit(
            "voltage_divider",
            VOLTAGE_DIVIDER,
            json.dumps(["input", "output", "gnd"]),
            category="passive",
            description="Simple resistive voltage divider",
        )
        assert "created" in result.lower()

        listing = list_subcircuits()
        assert "voltage_divider" in listing

    def test_list_by_category(self):
        create_subcircuit(
            "vd1", VOLTAGE_DIVIDER, json.dumps(["in", "out", "gnd"]), category="passive"
        )
        result = list_subcircuits(category="passive")
        assert "vd1" in result

        result_empty = list_subcircuits(category="amplifier")
        assert "No subcircuits" in result_empty

    def test_get_subcircuit(self):
        create_subcircuit(
            "test_sc",
            VOLTAGE_DIVIDER,
            json.dumps(["in", "out"]),
            category="passive",
            description="Test subcircuit",
            design_notes="For testing only",
        )
        result = get_subcircuit("test_sc")
        assert "test_sc" in result
        assert "passive" in result

    def test_get_not_found(self):
        result = get_subcircuit("nonexistent")
        assert "not found" in result.lower()

    def test_import_subcircuit(self):
        spice = ".subckt opamp in+ in- out vcc vee\n...\n.ends"
        result = import_subcircuit(
            "opamp_model", spice, json.dumps(["in+", "in-", "out", "vcc", "vee"])
        )
        assert "imported" in result.lower()
