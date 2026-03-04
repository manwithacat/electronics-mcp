"""FastMCP server for ElectronicsMCP."""
from fastmcp import FastMCP
from electronics_mcp.config import ProjectConfig
from electronics_mcp.core.database import Database

mcp = FastMCP(
    "ElectronicsMCP",
    instructions="Electronic engineering context and skills for LLM agents",
)

# Lazy initialization
_config: ProjectConfig | None = None
_db: Database | None = None


def get_config() -> ProjectConfig:
    global _config
    if _config is None:
        _config = ProjectConfig()
        _config.ensure_dirs()
    return _config


def get_db() -> Database:
    global _db
    if _db is None:
        config = get_config()
        _db = Database(config.db_path)
        _db.initialize()
    return _db


# Import tool modules to register them
from electronics_mcp.mcp import tools_circuit  # noqa: E402, F401


def main():
    mcp.run()


if __name__ == "__main__":
    main()
