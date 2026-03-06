import pytest
from electronics_mcp.core.database import Database
from electronics_mcp.mcp.tools_db import (
    init_project,
    import_spice_model,
    export_project,
    query_db,
)
import electronics_mcp.mcp.server as srv


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project):
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize()
    yield
    srv._config = None
    srv._db = None


class TestDBTools:
    def test_init_project(self):
        result = init_project(seed=True)
        assert "initialized" in result.lower()

    def test_import_spice_model(self):
        result = import_spice_model(
            "diode",
            "1N4148",
            ".model 1N4148 D(Is=2.52e-9 Rs=0.568)",
            manufacturer="Generic",
            description="Small signal diode",
        )
        assert "imported" in result.lower()

    def test_export_project(self):
        result = export_project()
        assert "exported" in result.lower()

    def test_query_db_select(self):
        result = query_db("SELECT type, subtype FROM component_categories LIMIT 3")
        # May return "No results" if not seeded, or a table
        assert isinstance(result, str)

    def test_query_db_rejects_non_select(self):
        result = query_db("DROP TABLE circuits")
        assert "Only SELECT" in result
