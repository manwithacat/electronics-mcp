from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_kicad_symbols import (
    parse_sexpr,
    extract_symbols,
    ingest_kicad_symbols,
)


class TestSexprParser:
    def test_parse_simple(self):
        result = parse_sexpr("(kicad_symbol_lib (version 20220914))")
        assert len(result) == 1
        assert result[0][0] == "kicad_symbol_lib"

    def test_parse_nested(self):
        result = parse_sexpr("(a (b c) (d (e f)))")
        assert result[0][0] == "a"
        assert result[0][1] == ["b", "c"]

    def test_parse_quoted_strings(self):
        result = parse_sexpr('(property "Reference" "R")')
        assert result[0][1] == "Reference"
        assert result[0][2] == "R"


class TestSymbolExtraction:
    def test_extract_symbol(self):
        parsed = parse_sexpr("""
        (kicad_symbol_lib
          (symbol "R_Small"
            (property "Reference" "R")
            (property "Description" "Resistor, small symbol")
            (property "Footprint" "Resistor_SMD:R_0805")
            (symbol "R_Small_0_1"
              (pin passive line (name "1") (number "1"))
              (pin passive line (name "2") (number "2"))
            )
          )
        )
        """)
        symbols = extract_symbols(parsed[0])
        assert len(symbols) == 1
        assert symbols[0]["name"] == "R_Small"
        assert symbols[0]["reference"] == "R"
        assert len(symbols[0]["pins"]) == 2

    def test_skip_power_symbols(self):
        parsed = parse_sexpr("""
        (kicad_symbol_lib
          (symbol "power:GND" (property "Reference" "#PWR"))
          (symbol "R_10k" (property "Reference" "R"))
        )
        """)
        symbols = extract_symbols(parsed[0])
        assert len(symbols) == 1
        assert symbols[0]["name"] == "R_10k"


class TestIngestion:
    def test_ingest_kicad_file(self, tmp_path):
        kicad_content = """(kicad_symbol_lib (version 20220914)
  (symbol "C_Small"
    (property "Reference" "C")
    (property "Description" "Capacitor, small symbol")
    (property "Footprint" "Capacitor_SMD:C_0805")
    (property "Datasheet" "~")
    (symbol "C_Small_0_1"
      (pin passive line (name "1") (number "1"))
      (pin passive line (name "2") (number "2"))
    )
  )
  (symbol "LED"
    (property "Reference" "LED")
    (property "Description" "Light emitting diode")
    (property "Footprint" "LED_SMD:LED_0805")
    (symbol "LED_0_1"
      (pin passive line (name "A") (number "1"))
      (pin passive line (name "K") (number "2"))
    )
  )
)"""
        sym_file = tmp_path / "test.kicad_sym"
        sym_file.write_text(kicad_content)

        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = ingest_kicad_symbols(sym_file, db)

        assert stats["symbols"] == 2

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM component_models").fetchone()[0]
            assert count == 2
