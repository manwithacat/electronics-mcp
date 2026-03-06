from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.rendering.reports import generate_markdown, generate_pdf


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    description="First-order low-pass filter",
    components=[
        ComponentBase(
            id="V1",
            type="voltage_source",
            subtype="ac",
            parameters={"amplitude": "1V"},
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


class TestMarkdownReport:
    def test_generates_markdown(self, tmp_path):
        path = generate_markdown(RC_FILTER, tmp_path / "report.md")
        assert path.exists()
        content = path.read_text()
        assert "RC Low-Pass" in content
        assert "R1" in content
        assert "10k" in content

    def test_includes_simulation_results(self, tmp_path):
        sim_results = [
            {"analysis_type": "dc", "node_voltages": {"output": 5.0, "input": 10.0}},
        ]
        path = generate_markdown(
            RC_FILTER,
            tmp_path / "report.md",
            simulation_results=sim_results,
        )
        content = path.read_text()
        assert "5.0000" in content

    def test_includes_warnings(self, tmp_path):
        path = generate_markdown(
            RC_FILTER,
            tmp_path / "report.md",
            validation_warnings=["Floating node: test_node"],
        )
        content = path.read_text()
        assert "Floating node" in content


class TestPDFReport:
    def test_generates_pdf(self, tmp_path):
        md_path = generate_markdown(RC_FILTER, tmp_path / "report.md")
        pdf_path = generate_pdf(md_path, tmp_path / "report.pdf")
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 100  # Not empty
        # PDF starts with %PDF
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"
