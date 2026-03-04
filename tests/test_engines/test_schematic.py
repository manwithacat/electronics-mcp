import pytest
from pathlib import Path
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.rendering.schematic import SchematicRenderer


@pytest.fixture
def renderer():
    return SchematicRenderer()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestSchematicRenderer:
    def test_renders_svg(self, renderer, tmp_path):
        output_path = renderer.render(RC_FILTER, tmp_path / "test.svg")
        assert output_path.exists()
        assert output_path.suffix == ".svg"
        content = output_path.read_text()
        assert "<svg" in content

    def test_includes_component_labels(self, renderer, tmp_path):
        output_path = renderer.render(RC_FILTER, tmp_path / "test.svg")
        content = output_path.read_text()
        assert "R1" in content
        assert "C1" in content
