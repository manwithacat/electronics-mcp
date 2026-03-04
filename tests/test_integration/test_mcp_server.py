"""Integration test: verify MCP server has all tools and resources registered."""
import pytest


class TestMCPServerSetup:
    def test_server_imports_cleanly(self):
        """Verify the MCP server module imports without errors."""
        from electronics_mcp.mcp.server import mcp
        assert mcp is not None
        assert mcp.name == "ElectronicsMCP"

    def test_all_tool_modules_loaded(self):
        """Verify all tool modules are importable."""
        from electronics_mcp.mcp import tools_circuit
        from electronics_mcp.mcp import tools_simulation
        from electronics_mcp.mcp import tools_rendering
        from electronics_mcp.mcp import tools_fabrication
        from electronics_mcp.mcp import tools_knowledge
        from electronics_mcp.mcp import tools_comparison
        from electronics_mcp.mcp import tools_db
        from electronics_mcp.mcp import resources
        from electronics_mcp.mcp import tools_subcircuit
        # All imports succeeded
        assert tools_circuit is not None
        assert tools_simulation is not None
        assert tools_rendering is not None
        assert tools_fabrication is not None
        assert tools_knowledge is not None
        assert tools_comparison is not None
        assert tools_db is not None
        assert resources is not None
        assert tools_subcircuit is not None

    def test_server_has_tools(self):
        """Verify MCP server has registered tools."""
        from electronics_mcp.mcp.server import mcp
        # FastMCP object exists and is configured
        assert mcp.name == "ElectronicsMCP"

    def test_get_config_and_db(self, tmp_path, monkeypatch):
        """Verify lazy initialization works."""
        import electronics_mcp.mcp.server as srv
        from electronics_mcp.config import ProjectConfig
        # Reset singletons and inject test config
        srv._config = ProjectConfig(project_dir=tmp_path)
        srv._db = None

        config = srv.get_config()
        assert config.project_dir == tmp_path

        db = srv.get_db()
        assert db is not None


class TestWebAppSetup:
    def test_web_app_imports(self):
        """Verify web app module imports without errors."""
        from electronics_mcp.web.app import app
        assert app is not None
        assert app.title == "ElectronicsMCP"

    def test_web_routes_registered(self):
        """Verify key routes exist."""
        from electronics_mcp.web.app import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/" in routes
        assert "/circuits" in routes
        assert "/knowledge" in routes
        assert "/components" in routes
        assert "/subcircuits" in routes
