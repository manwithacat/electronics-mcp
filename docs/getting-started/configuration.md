# Configuration

## MCP Server Configuration

ElectronicsMCP is configured via `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "electronics": {
      "command": "python",
      "args": ["-m", "electronics_mcp.mcp.server"],
      "cwd": "."
    }
  }
}
```

The server automatically:

- Creates `data/ee.db` with the knowledge base on first run
- Creates output directories as needed
- Seeds the database with component libraries, formulas, and design rules

## Project Directory

The server operates within the current working directory. All paths are relative to this:

| Path | Purpose |
|------|---------|
| `data/ee.db` | SQLite database (circuits, knowledge, simulation cache) |
| `output/schematics/` | Generated circuit diagrams (SVG) |
| `output/plots/` | Simulation plots (PNG/SVG) |
| `output/reports/` | Design documents (Markdown, PDF) |
| `output/netlists/` | SPICE and KiCad netlist exports |
| `output/bom/` | Bills of materials (CSV) |
| `models/` | User-imported SPICE model files |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ELECTRONICS_MCP_DB` | `data/ee.db` | Override database path |
| `ELECTRONICS_MCP_OUTPUT` | `output/` | Override output directory |
| `ELECTRONICS_MCP_WEB_PORT` | `8080` | Web UI port |

## Web UI

The web UI runs as a companion process:

```bash
python -m electronics_mcp.web.run
```

It shares the same database as the MCP server, so changes made interactively are visible to the agent and vice versa.
