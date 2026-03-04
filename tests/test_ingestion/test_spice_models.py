import pytest
from pathlib import Path
from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_spice_models import (
    parse_model_statement, parse_subckt_statement, ingest_spice_file,
)


class TestModelParsing:
    def test_parse_diode_model(self):
        text = ".model 1N4148 D(Is=2.52e-9 Rs=0.568 N=1.752 Bv=100 Ibv=100e-6)"
        result = parse_model_statement(text)
        assert result is not None
        assert result["name"] == "1N4148"
        assert result["model_type"] == "D"
        assert result["component_type"] == "diode"
        assert "Is" in result["parameters"]
        assert result["parameters"]["Is"] == pytest.approx(2.52e-9)

    def test_parse_npn_model(self):
        text = ".model 2N2222 NPN(Is=14.34e-15 Bf=255.9 Vaf=74.03)"
        result = parse_model_statement(text)
        assert result is not None
        assert result["name"] == "2N2222"
        assert result["component_type"] == "bjt"

    def test_parse_mosfet_model(self):
        text = ".model IRF540 NMOS(Level=1 Kp=20.53 Vto=3.5)"
        result = parse_model_statement(text)
        assert result is not None
        assert result["component_type"] == "mosfet"

    def test_invalid_returns_none(self):
        result = parse_model_statement("This is not a model statement")
        assert result is None


class TestSubcktParsing:
    def test_parse_subckt(self):
        text = """.subckt opamp in+ in- out vcc vee
R1 in+ mid 10k
R2 mid out 100k
.ends opamp"""
        result = parse_subckt_statement(text)
        assert result is not None
        assert result["name"] == "opamp"
        assert len(result["nodes"]) == 5
        assert "R1" in result["body"]

    def test_invalid_returns_none(self):
        result = parse_subckt_statement("Not a subcircuit")
        assert result is None


class TestIngestion:
    def test_ingest_spice_file(self, tmp_path):
        spice_content = """\
* Test SPICE Library
.model 1N4148 D(Is=2.52e-9 Rs=0.568 N=1.752)
.model 2N2222 NPN(Is=14.34e-15 Bf=255.9 Vaf=74.03)
.subckt voltage_ref in out gnd
R1 in mid 10k
D1 mid gnd 1N4148
.ends voltage_ref
"""
        lib_file = tmp_path / "test.lib"
        lib_file.write_text(spice_content)

        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = ingest_spice_file(lib_file, db)

        assert stats["models"] == 2
        assert stats["subcircuits"] == 1

        # Verify data in DB
        with db.connect() as conn:
            models = conn.execute("SELECT COUNT(*) FROM component_models").fetchone()[0]
            assert models == 2
            subcircuits = conn.execute("SELECT COUNT(*) FROM subcircuits").fetchone()[0]
            assert subcircuits == 1
