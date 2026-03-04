import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, ComponentBase, CircuitModification, ComponentUpdate


@pytest.fixture
def cm(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize()
    return CircuitManager(db)


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    description="Test filter",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestCircuitManager:
    def test_create_circuit(self, cm):
        circuit_id = cm.create(RC_FILTER)
        assert circuit_id is not None

        retrieved = cm.get(circuit_id)
        assert retrieved["name"] == "RC Low-Pass"

    def test_list_circuits(self, cm):
        cm.create(RC_FILTER)
        circuits = cm.list_all()
        assert len(circuits) == 1
        assert circuits[0]["name"] == "RC Low-Pass"

    def test_modify_circuit_creates_version(self, cm):
        circuit_id = cm.create(RC_FILTER)

        mod = CircuitModification(
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        version = cm.modify(circuit_id, mod)
        assert version == 2

        schema = cm.get_schema(circuit_id)
        r1 = next(c for c in schema.components if c.id == "R1")
        assert r1.parameters["resistance"] == "22k"

    def test_clone_circuit(self, cm):
        original_id = cm.create(RC_FILTER)
        clone_id = cm.clone(original_id, "RC Clone")
        assert clone_id != original_id
        clone = cm.get(clone_id)
        assert clone["name"] == "RC Clone"

    def test_delete_circuit(self, cm):
        circuit_id = cm.create(RC_FILTER)
        cm.delete(circuit_id)
        assert cm.get(circuit_id) is None

    def test_validate_circuit_finds_floating_nodes(self, cm):
        # A circuit with a node connected to only one component
        schema = CircuitSchema(
            name="Bad Circuit",
            components=[
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"},
                              nodes=["input", "floating_node"]),
            ],
        )
        circuit_id = cm.create(schema)
        warnings = cm.validate(circuit_id)
        assert any("floating" in w.lower() or "unconnected" in w.lower()
                    for w in warnings)

    def test_get_version_history(self, cm):
        circuit_id = cm.create(RC_FILTER)
        mod = CircuitModification(
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        cm.modify(circuit_id, mod)
        versions = cm.get_versions(circuit_id)
        assert len(versions) == 2
