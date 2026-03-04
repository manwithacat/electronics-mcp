import pytest
import warnings
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.simulation.numerical import NumericalSimulator


@pytest.fixture
def simulator():
    return NumericalSimulator()


VOLTAGE_DIVIDER = CircuitSchema(
    name="Voltage Divider",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="dc",
                      parameters={"voltage": "10V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="R2", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["output", "gnd"]),
    ],
)

RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V", "offset": "0V"},
                      nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestDCSweep:
    def test_voltage_sweep(self, simulator, tmp_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.dc_sweep(
                VOLTAGE_DIVIDER,
                source_id="V1",
                start=0,
                stop=10,
                step=1,
                output_node="output",
                plot_dir=tmp_path,
            )
        assert "sweep_values" in results
        assert "output_values" in results
        assert len(results["sweep_values"]) > 0
        # At 10V input, output should be 5V (divider)
        last_output = results["output_values"][-1]
        assert abs(last_output - 5.0) < 0.1


class TestParametricSweep:
    def test_resistor_sweep(self, simulator, tmp_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.parametric_sweep(
                RC_FILTER,
                component_id="R1",
                parameter="resistance",
                values=["1k", "10k", "100k"],
                analysis_type="ac",
                analysis_params={
                    "start_freq": 1,
                    "stop_freq": 1e6,
                    "points_per_decade": 50,
                    "output_node": "output",
                },
                plot_dir=tmp_path,
            )
        assert "sweeps" in results
        assert len(results["sweeps"]) == 3
        # Higher resistance -> lower bandwidth
        bw_1k = results["sweeps"][0].get("bandwidth_hz", float("inf"))
        bw_100k = results["sweeps"][2].get("bandwidth_hz", float("inf"))
        assert bw_1k > bw_100k


class TestMonteCarlo:
    def test_tolerance_spread(self, simulator, tmp_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = simulator.monte_carlo(
                RC_FILTER,
                num_runs=5,
                tolerance_pct=5.0,
                analysis_type="ac",
                analysis_params={
                    "start_freq": 1,
                    "stop_freq": 1e6,
                    "points_per_decade": 50,
                    "output_node": "output",
                },
                plot_dir=tmp_path,
            )
        assert "runs" in results
        assert len(results["runs"]) == 5
        assert "statistics" in results
