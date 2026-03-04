import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, ComponentBase, SubcircuitInstance


@pytest.fixture
def cm(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize()
    return CircuitManager(db)


class TestNetlistGeneration:
    def test_simple_rc_netlist(self, cm):
        schema = CircuitSchema(
            name="RC Filter",
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="dc",
                              parameters={"voltage": "5V"}, nodes=["input", "gnd"]),
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"}, nodes=["input", "output"]),
                ComponentBase(id="C1", type="capacitor",
                              parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
            ],
        )
        circuit_id = cm.create(schema)
        netlist = cm.generate_netlist(circuit_id)

        assert "R1" in netlist
        assert "C1" in netlist
        assert "V1" in netlist
        # Verify it's valid SPICE-ish syntax
        assert ".end" in netlist.lower() or "END" in netlist

    def test_subcircuit_expansion(self, cm):
        # First, store a subcircuit in the DB
        with cm.db.connect() as conn:
            conn.execute(
                "INSERT INTO subcircuits (id, name, category, schema_json, ports, parameters) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("sub1", "voltage_divider", "passive",
                 json.dumps({"components": [
                     {"id": "R1", "type": "resistor",
                      "parameters": {"resistance": "PARAM_r_top"}, "nodes": ["vin", "vout"]},
                     {"id": "R2", "type": "resistor",
                      "parameters": {"resistance": "PARAM_r_bottom"}, "nodes": ["vout", "gnd"]},
                 ]}),
                 json.dumps([{"name": "vin"}, {"name": "vout"}, {"name": "gnd"}]),
                 json.dumps([{"name": "r_top", "default": "10k"},
                             {"name": "r_bottom", "default": "10k"}]))
            )

        schema = CircuitSchema(
            name="With Subcircuit",
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="dc",
                              parameters={"voltage": "12V"}, nodes=["input", "gnd"]),
            ],
            subcircuit_instances=[
                SubcircuitInstance(
                    id="U1", reference="voltage_divider",
                    parameters={"r_top": "20k", "r_bottom": "10k"},
                    port_connections={"vin": "input", "vout": "output", "gnd": "gnd"},
                ),
            ],
        )
        circuit_id = cm.create(schema)
        netlist = cm.generate_netlist(circuit_id)

        # Subcircuit should be expanded inline
        assert "20k" in netlist or "20000" in netlist
