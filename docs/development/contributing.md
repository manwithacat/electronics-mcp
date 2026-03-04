# Contributing

## Development Setup

```bash
git clone https://github.com/manwithacat/electronics-mcp.git
cd electronics-mcp
pip install -e ".[dev,web]"
brew install ngspice  # or apt-get install ngspice
```

## Running Tests

```bash
pytest -v                              # All tests
pytest tests/test_core/ -v             # Core module tests
pytest tests/test_engines/ -v          # Engine tests
pytest --cov=electronics_mcp -v        # With coverage
```

## Code Style

We use `ruff` for linting and formatting:

```bash
ruff check electronics_mcp/ tests/
ruff format electronics_mcp/ tests/
```

## Architecture

See [Architecture](architecture.md) for the layered design. Key principle: **engine modules must not depend on MCP or web frameworks**.

## Adding a New Tool

1. Implement the logic in the appropriate engine module
2. Write tests for the engine function
3. Add the MCP tool wrapper in the corresponding `mcp/tools_*.py` file
4. Add documentation to `docs/reference/tools.md`

## Adding Seed Data

1. Add source material to `seed/sources/`
2. Create or update the ingestion script in `electronics_mcp/ingestion/`
3. Run `python -m electronics_mcp.ingestion.qa` to validate
4. Regenerate `seed/seed_data.sql`
5. Add provenance entries for all new records
