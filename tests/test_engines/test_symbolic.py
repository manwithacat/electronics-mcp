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


class TestNodeVoltage:
    def test_node_voltage_at_output(self, analyzer):
        result = analyzer.node_voltage(RC_FILTER, "output")
        assert "latex" in result
        assert "expression" in result
        assert "python_expr" in result

    def test_node_voltage_at_input(self, analyzer):
        result = analyzer.node_voltage(RC_FILTER, "input")
        assert "latex" in result


class TestSimplify:
    def test_simplify_rc(self, analyzer):
        result = analyzer.simplify(RC_FILTER)
        assert "simplified_expression" in result
        assert "latex" in result
        assert "description" in result

    def test_simplify_contains_r_and_c(self, analyzer):
        result = analyzer.simplify(RC_FILTER)
        expr = result["simplified_expression"]
        assert "R" in expr or "C" in expr


class TestStepResponse:
    def test_step_response_expression(self, analyzer):
        result = analyzer.step_response(RC_FILTER, "input", "output")
        assert "expression" in result
        assert "latex" in result

    def test_step_response_with_plot(self, analyzer, tmp_path):
        result = analyzer.step_response(
            RC_FILTER, "input", "output", plot_dir=tmp_path
        )
        assert "plot_path" in result
        import os
        assert os.path.exists(result["plot_path"])
