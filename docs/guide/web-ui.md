# Web UI

ElectronicsMCP includes a web interface for interactive circuit exploration alongside the conversational MCP interface.

## Starting the Web Server

```bash
python -m electronics_mcp.web
```

The web UI runs at `http://localhost:8080` by default.

## Views

### Circuit Browser

Browse, search, and inspect all circuits in the project database. View schematics inline, compare versions, and see component details.

### Component Library

Search the component database with parametric filters. View SPICE model parameters, datasheets, and selection guides.

### Knowledge Browser

Browse and search the knowledge base. Articles are rendered with formula formatting and cross-references.

### Simulation Viewer

Interactive display of simulation results with waveform cursors, measurement tools, and overlay comparisons.

### Subcircuit Library

Browse available subcircuits with port diagrams and parameter documentation.

## Architecture

The web UI uses:

- **Dazzle** -- Generates CRUD views (circuit browser, component library, knowledge browser) from a DSL specification
- **Custom FastAPI routes** -- Handle interactive features (simulation viewer, parameter explorer, circuit comparison)
- **HTMX + Jinja2** -- Server-rendered pages with dynamic updates
- **Alpine.js** -- Lightweight client-side interactivity

## Shared Database

Both the MCP server and web UI operate on the same project-scoped SQLite database (`data/ee.db`). Changes made through either interface are immediately visible in the other.
