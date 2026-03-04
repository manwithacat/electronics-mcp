"""MCP tools for subcircuit library management."""
import json
import uuid
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.core.schema import CircuitSchema


@mcp.tool()
def list_subcircuits(category: str | None = None) -> str:
    """List available subcircuit templates.

    Args:
        category: Optional category filter (passive, amplifier, filter, power, etc.)
    """
    db = get_db()
    with db.connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT id, name, category, description, ports "
                "FROM subcircuits WHERE category = ? ORDER BY name",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, category, description, ports "
                "FROM subcircuits ORDER BY category, name",
            ).fetchall()

    if not rows:
        return "No subcircuits found." + (f" (category: {category})" if category else "")

    lines = ["| Name | Category | Description | Ports |",
             "|------|----------|-------------|-------|"]
    for r in rows:
        ports = json.loads(r["ports"]) if r["ports"] else []
        port_str = ", ".join(ports) if isinstance(ports, list) else str(ports)
        lines.append(f"| {r['name']} | {r['category'] or '?'} | "
                     f"{(r['description'] or '')[:50]} | {port_str} |")
    return "\n".join(lines)


@mcp.tool()
def get_subcircuit(name: str) -> str:
    """Get full details of a subcircuit template.

    Args:
        name: Subcircuit name
    """
    db = get_db()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM subcircuits WHERE name = ?",
            (name,),
        ).fetchone()

    if not row:
        return f"Subcircuit '{name}' not found."

    d = dict(row)
    lines = [f"# Subcircuit: {d['name']}", ""]
    lines.append(f"Category: {d.get('category', 'N/A')}")
    lines.append(f"Description: {d.get('description', 'N/A')}")
    lines.append(f"Ports: {d['ports']}")
    if d.get("parameters"):
        lines.append(f"Parameters: {d['parameters']}")
    if d.get("design_notes"):
        lines.append(f"\nDesign Notes: {d['design_notes']}")
    lines.append(f"\nSchema:\n{d['schema_json']}")
    return "\n".join(lines)


@mcp.tool()
def create_subcircuit(
    name: str,
    schema_json: str,
    ports_json: str,
    category: str = "",
    description: str = "",
    parameters_json: str | None = None,
    design_notes: str = "",
) -> str:
    """Create a new subcircuit template.

    Args:
        name: Unique subcircuit name
        schema_json: Circuit schema JSON
        ports_json: JSON array of port names
        category: Category (passive, amplifier, filter, etc.)
        description: Description
        parameters_json: Optional JSON with default parameters
        design_notes: Design notes
    """
    # Validate the schema
    CircuitSchema.model_validate_json(schema_json)

    sc_id = str(uuid.uuid4())
    db = get_db()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO subcircuits (id, name, category, description, "
            "schema_json, ports, parameters, design_notes, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user')",
            (sc_id, name, category, description, schema_json,
             ports_json, parameters_json or "{}", design_notes),
        )
    return f"Subcircuit '{name}' created with ID: {sc_id}"


@mcp.tool()
def import_subcircuit(name: str, spice_subckt: str, ports_json: str) -> str:
    """Import a subcircuit from SPICE .subckt text.

    Args:
        name: Name for the subcircuit
        spice_subckt: Raw SPICE .subckt definition text
        ports_json: JSON array of port names
    """
    sc_id = str(uuid.uuid4())
    db = get_db()

    # Store the raw SPICE as the schema (simplified import)
    schema = {"name": name, "components": [], "description": f"Imported from SPICE: {name}"}

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO subcircuits (id, name, description, schema_json, ports, "
            "design_notes, source) VALUES (?, ?, ?, ?, ?, ?, 'imported')",
            (sc_id, name, f"Imported SPICE subcircuit",
             json.dumps(schema), ports_json, spice_subckt),
        )
    return f"Subcircuit '{name}' imported with ID: {sc_id}"
