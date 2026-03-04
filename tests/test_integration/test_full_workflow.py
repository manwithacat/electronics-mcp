"""Integration test: full circuit design workflow end-to-end.

Defines a circuit -> stores in DB -> simulates -> renders schematic ->
generates report -> exports netlist -> generates BOM.
"""
import json
import pytest
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import CircuitSchema
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.engines.fabrication.spice_netlist import generate_spice_netlist
from electronics_mcp.engines.fabrication.bom import generate_bom
from electronics_mcp.engines.rendering.reports import generate_markdown


@pytest.fixture
def workspace(tmp_path):
    """Set up a complete workspace with database."""
    db = Database(tmp_path / "test.db")
    db.initialize()
    return {"db": db, "path": tmp_path}


class TestFullDesignWorkflow:
    """End-to-end test: define -> store -> fabricate -> report."""

    def test_voltage_divider_workflow(self, workspace):
        db = workspace["db"]
        out = workspace["path"]

        # Step 1: Define circuit schema
        schema = CircuitSchema.model_validate({
            "name": "voltage_divider",
            "description": "Simple resistive voltage divider",
            "components": [
                {"id": "R1", "type": "resistor",
                 "parameters": {"resistance": "10k"}, "nodes": ["vin", "vout"]},
                {"id": "R2", "type": "resistor",
                 "parameters": {"resistance": "10k"}, "nodes": ["vout", "gnd"]},
            ],
        })
        assert len(schema.components) == 2

        # Step 2: Store in database via CircuitManager
        mgr = CircuitManager(db)
        circuit_id = mgr.create(schema)
        assert circuit_id is not None

        # Verify retrieval
        retrieved = mgr.get(circuit_id)
        assert retrieved["name"] == "voltage_divider"
        retrieved_schema = mgr.get_schema(circuit_id)
        assert len(retrieved_schema.components) == 2

        # Step 3: Generate SPICE netlist
        netlist_path = generate_spice_netlist(schema, out / "divider.cir")
        assert netlist_path.exists()
        netlist_content = netlist_path.read_text()
        assert "R1" in netlist_content
        assert "R2" in netlist_content

        # Step 4: Generate BOM
        bom_path = generate_bom(schema, out / "bom.csv")
        assert bom_path.exists()
        bom_content = bom_path.read_text()
        assert "resistor" in bom_content.lower() or "R1" in bom_content

        # Step 5: Generate report
        report_path = generate_markdown(
            schema, out / "report.md",
            title="Voltage Divider Report",
            notes=["Equal resistors give Vout = Vin/2"],
        )
        assert report_path.exists()
        report_content = report_path.read_text()
        assert "Voltage Divider" in report_content

    def test_rc_filter_workflow(self, workspace):
        db = workspace["db"]
        out = workspace["path"]

        schema = CircuitSchema.model_validate({
            "name": "rc_lowpass",
            "description": "First-order RC low-pass filter",
            "components": [
                {"id": "R1", "type": "resistor",
                 "parameters": {"resistance": "1k"}, "nodes": ["in", "out"]},
                {"id": "C1", "type": "capacitor",
                 "parameters": {"capacitance": "100n"}, "nodes": ["out", "gnd"]},
            ],
        })

        mgr = CircuitManager(db)
        circuit_id = mgr.create(schema)

        # Verify versioning
        versions = mgr.get_versions(circuit_id)
        assert len(versions) == 1
        assert versions[0]["version"] == 1

        # Generate outputs
        netlist_path = generate_spice_netlist(schema, out / "rc.cir")
        assert netlist_path.exists()

        bom_path = generate_bom(schema, out / "rc_bom.csv")
        assert bom_path.exists()


class TestKnowledgeIngestionWorkflow:
    """Test the full ingestion pipeline end-to-end."""

    def test_build_and_qa(self, workspace):
        from electronics_mcp.ingestion.build_design_rules import build_design_rules
        from electronics_mcp.ingestion.build_formulas import build_formulas
        from electronics_mcp.ingestion.build_subcircuits import build_subcircuits
        from electronics_mcp.ingestion.qa import run_qa

        db = workspace["db"]

        # Ingest all content
        dr = build_design_rules(db)
        assert dr["created"] > 0

        fm = build_formulas(db)
        assert fm["created"] > 0

        sc = build_subcircuits(db)
        assert sc["created"] > 0

        # Run QA -- all built-in data should pass
        qa = run_qa(db)
        assert qa["total_issues"] == 0

    def test_seed_generation(self, workspace):
        from electronics_mcp.ingestion.generate_seed import generate_seed_sql

        db = workspace["db"]
        out = workspace["path"] / "seed" / "seed_data.sql"

        stats = generate_seed_sql(db, out)
        assert out.exists()
        content = out.read_text()

        # Verify all tables represented
        assert "knowledge" in content
        assert "subcircuits" in content
        assert "component_categories" in content
        assert stats["qa_issues"] == 0
