import pytest
import warnings
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.simulation.numerical import NumericalSimulator


@pytest.fixture
def simulator():
    return NumericalSimulator()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
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
)

VOLTAGE_DIVIDER = CircuitSchema(
    name="Voltage Divider",
    components=[
        ComponentBase(
            id="V1",
            type="voltage_source",
            subtype="dc",
            parameters={"voltage": "10V"},
            nodes=["input", "gnd"],
        ),
        ComponentBase(
            id="R1",
            type="resistor",
            parameters={"resistance": "10k"},
            nodes=["input", "output"],
        ),
        ComponentBase(
            id="R2",
            type="resistor",
            parameters={"resistance": "10k"},
            nodes=["output", "gnd"],
        ),
    ],
)


class TestDCOperatingPoint:
    def test_voltage_divider(self, simulator):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.dc_operating_point(VOLTAGE_DIVIDER)
        # With equal resistors, output should be half of input
        assert abs(results["node_voltages"]["output"] - 5.0) < 0.01
        assert abs(results["node_voltages"]["input"] - 10.0) < 0.01


class TestACAnalysis:
    def test_rc_filter_cutoff(self, simulator, tmp_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.ac_analysis(
                RC_FILTER,
                start_freq=1,
                stop_freq=1e6,
                points_per_decade=100,
                output_node="output",
                plot_dir=tmp_path,
            )
        # Cutoff frequency should be ~1/(2*pi*R*C) = ~1591 Hz
        assert "bandwidth_hz" in results
        assert abs(results["bandwidth_hz"] - 1591) < 200  # Within ~12%


class TestTransientAnalysis:
    def test_rc_step_response(self, simulator, tmp_path):
        step_circuit = CircuitSchema(
            name="RC Step",
            components=[
                ComponentBase(
                    id="V1",
                    type="voltage_source",
                    subtype="pulse",
                    parameters={
                        "v1": "0V",
                        "v2": "5V",
                        "rise_time": "1n",
                        "pulse_width": "10m",
                    },
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
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.transient_analysis(
                step_circuit,
                duration=1e-3,
                step_size=1e-6,
                output_node="output",
                plot_dir=tmp_path,
            )
        assert "rise_time" in results or "final_value" in results
