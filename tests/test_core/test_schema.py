import pytest
from electronics_mcp.core.schema import (
    CircuitSchema,
    ComponentBase,
    SubcircuitInstance,
    DesignIntent,
    Probe,
    CircuitModification,
    ComponentUpdate,
)


class TestCircuitSchema:
    def test_minimal_circuit(self):
        circuit = CircuitSchema(
            name="Test",
            components=[
                ComponentBase(
                    id="R1",
                    type="resistor",
                    parameters={"resistance": "10k"},
                    nodes=["input", "output"],
                ),
            ],
        )
        assert circuit.name == "Test"
        assert circuit.ground_node == "gnd"
        assert len(circuit.components) == 1

    def test_full_rc_filter(self):
        circuit = CircuitSchema(
            name="RC Low-Pass Filter",
            description="First-order low-pass filter with 1.59kHz cutoff",
            design_intent=DesignIntent(
                topology="low_pass_filter",
                target_specs={"cutoff_frequency_hz": 1590},
            ),
            components=[
                ComponentBase(
                    id="V1",
                    type="voltage_source",
                    subtype="ac",
                    parameters={"amplitude": "1V", "offset": "0V"},
                    nodes=["input", "gnd"],
                ),
                ComponentBase(
                    id="R1",
                    type="resistor",
                    parameters={"resistance": "10k"},
                    nodes=["input", "output"],
                ),
                ComponentBase(
                    id="C1",
                    type="capacitor",
                    parameters={"capacitance": "10n"},
                    nodes=["output", "gnd"],
                ),
            ],
            probes=[
                Probe(node="output", label="Vout"),
            ],
        )
        assert circuit.design_intent.topology == "low_pass_filter"
        assert len(circuit.probes) == 1

    def test_subcircuit_instance(self):
        circuit = CircuitSchema(
            name="With Subcircuit",
            components=[],
            subcircuit_instances=[
                SubcircuitInstance(
                    id="U_BUCK",
                    reference="buck_output_stage",
                    parameters={"inductance": "22u", "capacitance": "47u"},
                    port_connections={
                        "vin": "switch_node",
                        "vout": "output",
                        "gnd": "gnd",
                    },
                ),
            ],
        )
        assert circuit.subcircuit_instances[0].reference == "buck_output_stage"

    def test_invalid_component_type_rejected(self):
        with pytest.raises(ValueError):
            ComponentBase(id="X1", type="invalid_type", parameters={}, nodes=["a", "b"])

    def test_component_needs_at_least_two_nodes(self):
        with pytest.raises(ValueError):
            ComponentBase(
                id="R1", type="resistor", parameters={"resistance": "10k"}, nodes=["a"]
            )


class TestCircuitModification:
    def test_add_component(self):
        mod = CircuitModification(
            add=[
                ComponentBase(
                    id="C2",
                    type="capacitor",
                    parameters={"capacitance": "100n"},
                    nodes=["output", "gnd"],
                )
            ],
        )
        assert len(mod.add) == 1

    def test_remove_and_update(self):
        mod = CircuitModification(
            remove=["R3"],
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        assert mod.remove == ["R3"]

    def test_rename_node(self):
        mod = CircuitModification(
            rename_node={"old_output": "filtered_output"},
        )
        assert "old_output" in mod.rename_node
