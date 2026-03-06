"""Tests for provenance tracking and QA-based seed filtering."""
from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import (
    record_provenance,
    record_bulk_provenance,
)
from electronics_mcp.ingestion.build_design_rules import build_design_rules
from electronics_mcp.ingestion.generate_seed import generate_seed_sql


class TestProvenance:
    def test_record_single(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        record_provenance(
            db, "knowledge", "abc-123", "test_source",
            licence="MIT", notes="test note",
        )
        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM provenance WHERE record_id = 'abc-123'"
            ).fetchone()
        assert row is not None
        assert row["record_table"] == "knowledge"
        assert row["source_name"] == "test_source"
        assert row["licence"] == "MIT"
        assert row["notes"] == "test note"
        assert row["extraction_date"] is not None

    def test_record_bulk(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        count = record_bulk_provenance(
            db, "subcircuits", ["id1", "id2", "id3"], "builder",
            licence="original",
        )
        assert count == 3
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM provenance WHERE record_table = 'subcircuits'"
            ).fetchall()
        assert len(rows) == 3

    def test_bulk_empty_list(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        count = record_bulk_provenance(db, "knowledge", [], "test")
        assert count == 0

    def test_upsert_on_duplicate(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        record_provenance(db, "knowledge", "dup-1", "source_a", licence="MIT")
        record_provenance(db, "knowledge", "dup-1", "source_b", licence="Apache-2.0")
        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM provenance WHERE record_id = 'dup-1'"
            ).fetchone()
        assert row["source_name"] == "source_b"
        assert row["licence"] == "Apache-2.0"


class TestProvenanceIntegration:
    def test_design_rules_create_provenance(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = build_design_rules(db)
        assert stats["created"] > 0

        with db.connect() as conn:
            prov_rows = conn.execute(
                "SELECT * FROM provenance WHERE source_name = 'design_rules'"
            ).fetchall()
        assert len(prov_rows) == stats["created"]


class TestSeedSqlFiltering:
    def test_qa_failed_records_excluded(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()

        # Insert a bad knowledge entry (no title, short content)
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES ('bad-1', 'test', 'bad_topic', '', 'short', "
                "'[]', '[]', '', 'test')"
            )
            # Insert a good entry
            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES ('good-1', 'test', 'good_topic', 'Good Title', "
                "'This is a long enough content with more than five words here', "
                "'[]', '[]', 'beginner', 'test')"
            )

        output = tmp_path / "seed.sql"
        generate_seed_sql(db, output)
        sql = output.read_text()

        # Good entry should be in seed, bad should not
        assert "good-1" in sql
        assert "bad-1" not in sql
