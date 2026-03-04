import pytest
from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.qa import (
    check_knowledge, check_components, check_subcircuits,
    check_formulas, run_qa,
)
from electronics_mcp.ingestion.build_design_rules import build_design_rules
from electronics_mcp.ingestion.build_formulas import build_formulas
from electronics_mcp.ingestion.build_subcircuits import build_subcircuits
from electronics_mcp.ingestion.generate_seed import generate_seed_sql


class TestQAChecks:
    def test_knowledge_passes_for_valid_data(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_design_rules(db)
        issues = check_knowledge(db)
        assert len(issues) == 0

    def test_knowledge_catches_missing_title(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES ('bad1', 'test', 'bad_topic', '', 'some content here for testing words count', "
                "'[]', '[]', 'beginner', 'test')"
            )
        issues = check_knowledge(db)
        assert len(issues) == 1
        assert "missing title" in issues[0]["issues"]

    def test_components_catches_missing_type(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        import json
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO component_models (id, type, part_number, description, "
                "parameters, source) VALUES (?, ?, ?, ?, ?, ?)",
                ("c1", "", "TEST001", "", json.dumps({}), "test"),
            )
        issues = check_components(db)
        assert len(issues) == 1
        assert "missing type" in issues[0]["issues"]

    def test_subcircuits_passes_for_valid_data(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_subcircuits(db)
        issues = check_subcircuits(db)
        assert len(issues) == 0

    def test_formulas_all_evaluate(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_formulas(db)
        issues = check_formulas(db)
        assert len(issues) == 0

    def test_run_qa_returns_summary(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_design_rules(db)
        build_formulas(db)
        build_subcircuits(db)
        result = run_qa(db)
        assert "total_issues" in result
        assert "checks" in result


class TestSeedGeneration:
    def test_generate_seed_sql(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        output = tmp_path / "seed" / "seed_data.sql"
        stats = generate_seed_sql(db, output)
        assert output.exists()
        content = output.read_text()
        assert "INSERT OR IGNORE INTO knowledge" in content
        assert "INSERT OR IGNORE INTO subcircuits" in content
        assert stats["qa_issues"] >= 0

    def test_seed_sql_has_categories(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        output = tmp_path / "seed.sql"
        generate_seed_sql(db, output)
        content = output.read_text()
        assert "component_categories" in content
