# ElectronicsMCP

MCP server providing electronic engineering context and skills to LLM agents.

## Architecture

- `electronics_mcp/core/` -- Database, schema models, circuit manager, unit parser
- `electronics_mcp/engines/` -- Simulation (numerical + symbolic), rendering, fabrication, knowledge
- `electronics_mcp/mcp/` -- FastMCP server and tool modules
- `electronics_mcp/ingestion/` -- Data ingestion pipelines (Kuphaldt, SPICE models, KiCad, subcircuits)
- `electronics_mcp/web/` -- Dazzle web UI
- `tests/` -- Mirrors source structure

## Commands

```bash
# Run tests
pytest -v

# Run MCP server
python -m electronics_mcp.mcp.server

# Install (editable)
pip install -e ".[dev,web]"
```

## Conventions

- TDD: write failing tests first, then implement
- Pydantic v2 for all data models
- SQLite with FTS5 for knowledge base
- EE unit shorthand: 10k, 47u, 100n (use `core.units.parse_value`)
- Circuit descriptions use the `CircuitSchema` Pydantic model
- All file outputs go to `output/` subdirectories
