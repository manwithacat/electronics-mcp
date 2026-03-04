import pytest
import sqlite3
from electronics_mcp.core.database import Database


class TestDatabase:
    def test_init_creates_tables(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()

        conn = sqlite3.connect(tmp_project.db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        assert "circuits" in tables
        assert "circuit_versions" in tables
        assert "subcircuits" in tables
        assert "component_models" in tables
        assert "component_categories" in tables
        assert "simulation_results" in tables
        assert "knowledge" in tables
        assert "knowledge_fts" in tables
        assert "project_notes" in tables
        assert "design_decisions" in tables
        assert "comparisons" in tables
        assert "provenance" in tables
        conn.close()

    def test_init_is_idempotent(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()
        db.initialize()  # Should not raise

    def test_connection_context_manager(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()
        with db.connect() as conn:
            conn.execute("SELECT 1")

    def test_seed_data_loaded(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize(seed=True)
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM component_categories").fetchone()[0]
            assert count > 0  # Seed data populated categories
