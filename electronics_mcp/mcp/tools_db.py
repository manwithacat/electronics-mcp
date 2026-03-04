"""MCP tools for database and project management."""
import json
from electronics_mcp.mcp.server import mcp, get_db, get_config
from electronics_mcp.core.database import Database


@mcp.tool()
def init_project(seed: bool = True) -> str:
    """Initialize or reset the project database.

    Args:
        seed: Whether to seed with component categories and reference data
    """
    config = get_config()
    config.ensure_dirs()
    db = get_db()
    db.initialize(seed=seed)
    return f"Project initialized at {config.project_dir}\nDatabase: {config.db_path}\nSeeded: {seed}"


@mcp.tool()
def import_spice_model(
    model_type: str,
    part_number: str,
    spice_model: str,
    manufacturer: str = "",
    description: str = "",
    parameters_json: str = "{}",
) -> str:
    """Import a SPICE model into the component database.

    Args:
        model_type: Component type (resistor, capacitor, diode, etc.)
        part_number: Part number
        spice_model: SPICE model text
        manufacturer: Manufacturer name
        description: Component description
        parameters_json: JSON object with component parameters
    """
    import uuid
    db = get_db()
    model_id = str(uuid.uuid4())

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO component_models (id, type, manufacturer, part_number, "
            "description, parameters, spice_model, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'imported')",
            (model_id, model_type, manufacturer, part_number,
             description, parameters_json, spice_model),
        )
    return f"SPICE model '{part_number}' imported with ID: {model_id}"


@mcp.tool()
def export_project(format: str = "json") -> str:
    """Export project data (circuits, simulations, knowledge) as JSON.

    Args:
        format: Export format (json)
    """
    db = get_db()
    config = get_config()
    output_path = config.output_dir / "project_export.json"

    export_data: dict = {"circuits": [], "knowledge": [], "simulations": []}

    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM circuits").fetchall():
            export_data["circuits"].append(dict(row))
        for row in conn.execute("SELECT * FROM knowledge").fetchall():
            export_data["knowledge"].append(dict(row))
        for row in conn.execute("SELECT * FROM simulation_results").fetchall():
            export_data["simulations"].append(dict(row))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export_data, indent=2, default=str))
    return f"Project exported to {output_path}\n" \
           f"Circuits: {len(export_data['circuits'])}, " \
           f"Knowledge: {len(export_data['knowledge'])}, " \
           f"Simulations: {len(export_data['simulations'])}"


@mcp.tool()
def query_db(sql: str) -> str:
    """Run a read-only SQL query against the project database.

    Only SELECT statements are allowed for safety.

    Args:
        sql: SQL SELECT query
    """
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    db = get_db()
    with db.connect() as conn:
        try:
            rows = conn.execute(sql).fetchall()
        except Exception as e:
            return f"Query error: {e}"

    if not rows:
        return "No results."

    # Format as table
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows[:50]:  # Limit output
        vals = [str(row[h])[:40] for h in headers]
        lines.append("| " + " | ".join(vals) + " |")

    if len(rows) > 50:
        lines.append(f"\n... and {len(rows) - 50} more rows")
    return "\n".join(lines)
