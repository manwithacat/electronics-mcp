import pytest
import json
import warnings
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_circuit import define_circuit
from electronics_mcp.mcp.tools_simulation import (
    dc_operating_point, ac_analysis, transient_analysis,
    transfer_function, impedance, poles_and_zeros,
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


RC_FILTER_JSON = json.dumps({
    "name": "RC Low-Pass",
    "components": [
        {"id": "V1", "type": "voltage_source", "subtype": "ac",
         "parameters": {"amplitude": "1V"}, "nodes": ["input", "gnd"]},
        {"id": "R1", "type": "resistor",
         "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
        {"id": "C1", "type": "capacitor",
         "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
    ]
})


def _create_circuit():
    result = define_circuit(RC_FILTER_JSON)
    return result.split("ID: ")[1].split("\n")[0].strip()


class TestNumericalTools:
    def test_dc_operating_point(self):
        cid = _create_circuit()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = dc_operating_point(cid)
        assert "Node Voltages" in result

    def test_ac_analysis(self):
        cid = _create_circuit()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = ac_analysis(cid, "output")
        assert "AC Analysis" in result

    def test_transient_analysis(self):
        cid = _create_circuit()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = transient_analysis(cid, 0.001, "output")
        assert "Transient" in result


class TestSymbolicTools:
    def test_transfer_function(self):
        cid = _create_circuit()
        result = transfer_function(cid, "input", "output")
        assert "Transfer Function" in result

    def test_impedance(self):
        cid = _create_circuit()
        result = impedance(cid, "input", "output")
        assert "Impedance" in result

    def test_poles_and_zeros(self):
        cid = _create_circuit()
        result = poles_and_zeros(cid, "input", "output")
        assert "Poles" in result
