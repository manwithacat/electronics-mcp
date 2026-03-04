import pytest
import csv
from pathlib import Path
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.core.database import Database
from electronics_mcp.engines.fabrication.spice_netlist import generate_spice_netlist
from electronics_mcp.engines.fabrication.kicad_netlist import generate_kicad_netlist
from electronics_mcp.engines.fabrication.bom import generate_bom, generate_bom_summary
from electronics_mcp.engines.fabrication.components import ComponentSuggester


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="dc",
                      parameters={"voltage": "5V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestSpiceNetlist:
    def test_generates_cir_file(self, tmp_path):
        path = generate_spice_netlist(RC_FILTER, tmp_path / "test.cir")
        assert path.exists()
        content = path.read_text()
        assert "R1" in content
        assert "C1" in content
        assert "V1" in content
        assert ".end" in content

    def test_correct_values(self, tmp_path):
        path = generate_spice_netlist(RC_FILTER, tmp_path / "test.cir")
        content = path.read_text()
        assert "10000" in content  # 10k resistance
        assert "1e-08" in content  # 10n capacitance


class TestKicadNetlist:
    def test_generates_xml(self, tmp_path):
        path = generate_kicad_netlist(RC_FILTER, tmp_path / "test.net")
        assert path.exists()
        content = path.read_text()
        assert "export" in content
        assert "R1" in content
        assert "C1" in content

    def test_contains_nets(self, tmp_path):
        path = generate_kicad_netlist(RC_FILTER, tmp_path / "test.net")
        content = path.read_text()
        assert "<nets>" in content
        assert "GND" in content


class TestBOM:
    def test_generates_csv(self, tmp_path):
        path = generate_bom(RC_FILTER, tmp_path / "bom.csv")
        assert path.exists()
        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 4  # header + 3 components
        assert rows[0][0] == "Reference"

    def test_bom_summary(self):
        summary = generate_bom_summary(RC_FILTER)
        assert summary["total_components"] == 3
        assert summary["unique_types"] == 3


class TestComponentSuggester:
    def test_selection_guide(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize(seed=True)
        suggester = ComponentSuggester(db)
        guides = suggester.get_selection_guide("resistor")
        assert len(guides) > 0
        assert "selection_guide" in guides[0]

    def test_suggest_returns_empty_when_no_models(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()
        suggester = ComponentSuggester(db)
        results = suggester.suggest("resistor", "10k")
        assert isinstance(results, list)
