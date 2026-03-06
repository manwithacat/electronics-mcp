from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.build_design_rules import (
    build_design_rules,
    DESIGN_RULES,
)
from electronics_mcp.ingestion.build_formulas import (
    build_formulas,
    FORMULAS,
)


class TestBuildDesignRules:
    def test_build_all_rules(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = build_design_rules(db)
        assert stats["created"] == len(DESIGN_RULES)

        with db.connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE source = 'design_rules'"
            ).fetchone()[0]
            assert count == len(DESIGN_RULES)

    def test_skip_duplicates(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_design_rules(db)
        stats2 = build_design_rules(db)
        assert stats2["skipped"] == len(DESIGN_RULES)

    def test_fts_searchable(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_design_rules(db)

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT k.topic FROM knowledge k "
                "JOIN knowledge_fts fts ON k.rowid = fts.rowid "
                "WHERE knowledge_fts MATCH '\"decoupling\"'",
            ).fetchall()
            assert len(rows) >= 1


class TestBuildFormulas:
    def test_build_all_formulas(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = build_formulas(db)
        assert stats["created"] == len(FORMULAS)
        assert stats["formulas"] > 0

        with db.connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE source = 'formula_builder'"
            ).fetchone()[0]
            assert count == len(FORMULAS)

    def test_formulas_have_content(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_formulas(db)

        with db.connect() as conn:
            row = conn.execute(
                "SELECT formulas FROM knowledge WHERE topic = 'ohms_law'"
            ).fetchone()
            assert row is not None
            import json

            formulas = json.loads(row["formulas"])
            assert len(formulas) == 3
            assert formulas[0]["name"] == "V"

    def test_skip_duplicates(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_formulas(db)
        stats2 = build_formulas(db)
        assert stats2["skipped"] == len(FORMULAS)
