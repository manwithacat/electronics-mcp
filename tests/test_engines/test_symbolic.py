import pytest
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.simulation.symbolic import SymbolicAnalyzer


@pytest.fixture
def analyzer():
    return SymbolicAnalyzer()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "R"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "C"}, nodes=["output", "gnd"]),
    ],
)


class TestTransferFunction:
    def test_rc_lowpass_transfer_function(self, analyzer):
        result = analyzer.transfer_function(RC_FILTER, "input", "output")
        assert "latex" in result
        assert "python_expr" in result
        # Should contain 1/(1 + sRC) or equivalent
        assert "s" in result["latex"] or "omega" in result["latex"]


class TestImpedance:
    def test_rc_parallel_impedance(self, analyzer):
        result = analyzer.impedance(RC_FILTER, "output", "gnd")
        assert "latex" in result
        assert "expression" in result


class TestPolesAndZeros:
    def test_rc_filter_has_one_pole(self, analyzer, tmp_path):
        result = analyzer.poles_and_zeros(
            RC_FILTER, "input", "output", plot_dir=tmp_path
        )
        assert len(result["poles"]) == 1
        assert len(result["zeros"]) == 0
