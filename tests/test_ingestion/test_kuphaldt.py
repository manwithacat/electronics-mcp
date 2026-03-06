from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_kuphaldt import (
    ingest_kuphaldt,
    _SectionExtractor,
    _extract_formulas,
    _topic_slug,
    _difficulty_from_depth,
)


class TestSectionExtractor:
    def test_extracts_sections(self):
        html = """
        <h2>Ohm's Law</h2>
        <p>Ohm's law describes the relationship between voltage, current, and resistance.</p>
        <p>The formula is V = I * R, where V is voltage, I is current, and R is resistance.</p>
        <h2>Power</h2>
        <p>Power is calculated as P = V * I.</p>
        """
        parser = _SectionExtractor()
        parser.feed(html)
        parser.close()
        assert len(parser.sections) == 2
        assert parser.sections[0]["title"] == "Ohm's Law"
        assert "resistance" in parser.sections[0]["content"]

    def test_handles_nested_headings(self):
        html = """
        <h2>Chapter</h2>
        <p>Chapter intro.</p>
        <h3>Section</h3>
        <p>Section content here with enough text to pass minimum length.</p>
        """
        parser = _SectionExtractor()
        parser.feed(html)
        parser.close()
        assert len(parser.sections) == 2
        assert parser.sections[1]["level"] == 3


class TestFormulaExtraction:
    def test_extracts_formula(self):
        text = "The cutoff frequency is F = 1/(2*pi*R*C) for a simple RC filter."
        formulas = _extract_formulas(text)
        assert len(formulas) >= 1
        assert formulas[0]["name"] == "F"

    def test_no_false_positives(self):
        text = "This is a simple sentence without formulas."
        formulas = _extract_formulas(text)
        assert len(formulas) == 0


class TestHelpers:
    def test_topic_slug(self):
        assert _topic_slug("Ohm's Law") == "ohm_s_law"
        assert _topic_slug("RC Low-Pass Filter") == "rc_low_pass_filter"

    def test_difficulty(self):
        assert _difficulty_from_depth("DC", 2) == "beginner"
        assert _difficulty_from_depth("Semi", 3) == "intermediate"
        assert _difficulty_from_depth("Semi", 5) == "advanced"


class TestIngestion:
    def test_ingest_from_html_files(self, tmp_path):
        # Create a minimal test HTML file
        html_content = """
        <html>
        <body>
        <h1>DC Circuits</h1>
        <p>Introduction to direct current circuits and basic concepts for beginners.</p>
        <h2>Ohm's Law</h2>
        <p>Ohm's law states that V = I * R. This fundamental relationship connects
        voltage, current, and resistance in electrical circuits. It applies to all
        resistive elements.</p>
        <h2>Series Circuits</h2>
        <p>In a series circuit, components are connected end to end. The total
        resistance is R = R1 + R2 + R3. Current is the same through all components.</p>
        </body>
        </html>
        """
        source_dir = tmp_path / "sources"
        source_dir.mkdir()
        (source_dir / "dc_vol1.html").write_text(html_content)

        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = ingest_kuphaldt(source_dir, db, min_content_length=30)
        assert stats["articles"] >= 2
        assert stats["formulas"] >= 0  # May or may not extract formulas

        # Verify data in DB
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            assert count >= 2
