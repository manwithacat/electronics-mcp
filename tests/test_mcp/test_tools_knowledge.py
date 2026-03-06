import pytest
import json
import warnings
from tests.markers import requires_ngspice
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import define_circuit
from electronics_mcp.mcp.tools_simulation import dc_operating_point
from electronics_mcp.mcp.tools_knowledge import (
    search_knowledge,
    get_topic,
    explain_topology,
    design_guide,
    component_info,
    list_formulas,
    learn_pattern,
    what_if,
    check_design,
)
import electronics_mcp.mcp.server as srv


RC_FILTER_JSON = json.dumps(
    {
        "name": "RC Low-Pass",
        "components": [
            {
                "id": "V1",
                "type": "voltage_source",
                "subtype": "ac",
                "parameters": {"amplitude": "1V"},
                "nodes": ["input", "gnd"],
            },
            {
                "id": "R1",
                "type": "resistor",
                "parameters": {"resistance": "10k"},
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


def _create_circuit():
    result = define_circuit(RC_FILTER_JSON)
    return result.split("ID: ")[1].split("\n")[0].strip()


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project):
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize(seed=True)
    yield
    srv._config = None
    srv._db = None


class TestKnowledgeTools:
    def test_learn_and_search(self):
        result = learn_pattern(
            "filter",
            "rc_lowpass",
            "RC Low-Pass Filter",
            "An RC low-pass filter attenuates high frequencies.",
            json.dumps([{"name": "fc", "expression": "1/(2*pi*R*C)"}]),
        )
        assert "stored" in result.lower()

        search_result = search_knowledge("low-pass filter")
        assert "RC Low-Pass" in search_result

    def test_get_topic(self):
        learn_pattern(
            "topology",
            "voltage_divider",
            "Voltage Divider",
            "Two resistors creating a voltage fraction.",
        )
        result = get_topic("voltage_divider")
        assert "Voltage Divider" in result

    def test_get_topic_not_found(self):
        result = get_topic("nonexistent_topic")
        assert "No article" in result

    def test_explain_topology(self):
        learn_pattern(
            "topology",
            "half_bridge",
            "Half Bridge",
            "A half-bridge topology uses two switches.",
        )
        result = explain_topology("half_bridge")
        assert "half_bridge" in result.lower() or "Half Bridge" in result

    def test_design_guide(self):
        learn_pattern(
            "filter",
            "low_pass_filter",
            "LP Filter Design",
            "1. Choose cutoff\n2. Select R\n3. Calc C",
        )
        result = design_guide("low_pass_filter")
        assert "Steps" in result or "Design Guide" in result

    def test_component_info(self):
        result = component_info("resistor")
        assert "resistor" in result.lower()

    def test_list_formulas(self):
        learn_pattern(
            "topology",
            "ohms_law",
            "Ohm's Law",
            "V = IR",
            json.dumps([{"name": "V", "expression": "I * R"}]),
        )
        result = list_formulas("ohms_law")
        assert "I * R" in result

    def test_list_formulas_not_found(self):
        result = list_formulas("nonexistent")
        assert "No formulas" in result


class TestWhatIf:
    def test_what_if_returns_analysis(self):
        cid = _create_circuit()
        result = what_if(cid, "double R1 resistance")
        assert "What-If Analysis" in result
        assert "double R1 resistance" in result
        assert "RC Low-Pass" in result

    def test_what_if_lists_components(self):
        cid = _create_circuit()
        result = what_if(cid, "increase capacitance")
        assert "R1" in result
        assert "C1" in result


class TestCheckDesign:
    def test_check_design_no_results(self):
        cid = _create_circuit()
        result = check_design(cid)
        assert "No simulation results" in result

    @requires_ngspice
    def test_check_design_with_results(self):
        cid = _create_circuit()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            dc_operating_point(cid)
        result = check_design(cid)
        assert "Design Check" in result
        assert "Latest Simulation Results" in result
