from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.build_subcircuits import (
    build_subcircuits,
    STANDARD_SUBCIRCUITS,
)


class TestBuildSubcircuits:
    def test_build_standard_subcircuits(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        stats = build_subcircuits(db)

        assert stats["created"] == len(STANDARD_SUBCIRCUITS)
        assert stats["errors"] == 0

        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM subcircuits").fetchone()[0]
            assert count == len(STANDARD_SUBCIRCUITS)

    def test_skip_duplicates(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        build_subcircuits(db)
        stats2 = build_subcircuits(db)
        assert stats2["skipped"] == len(STANDARD_SUBCIRCUITS)
        assert stats2["created"] == 0

    def test_custom_definitions(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.initialize()
        custom = [
            {
                "name": "test_divider",
                "category": "passive",
                "description": "Test",
                "ports": ["in", "out", "gnd"],
                "parameters": {},
                "schema": {
                    "name": "test_divider",
                    "components": [
                        {
                            "id": "R1",
                            "type": "resistor",
                            "parameters": {"resistance": "1k"},
                            "nodes": ["in", "out"],
                        },
                        {
                            "id": "R2",
                            "type": "resistor",
                            "parameters": {"resistance": "1k"},
                            "nodes": ["out", "gnd"],
                        },
                    ],
                },
                "design_notes": "Test only.",
            }
        ]
        stats = build_subcircuits(db, custom)
        assert stats["created"] == 1

    def test_all_standard_schemas_valid(self):
        """Verify all standard subcircuit schemas pass Pydantic validation."""
        from electronics_mcp.core.schema import CircuitSchema

        for defn in STANDARD_SUBCIRCUITS:
            schema = CircuitSchema.model_validate(defn["schema"])
            assert len(schema.components) > 0
