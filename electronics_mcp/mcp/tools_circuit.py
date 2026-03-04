"""MCP tools for circuit definition and management."""
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, CircuitModification


@mcp.tool()
def define_circuit(schema_json: str) -> str:
    """Create a new circuit from a full JSON schema and store it in the database.

    Args:
        schema_json: Full circuit JSON schema (see Circuit Description Schema)

    Returns:
        Circuit ID, summary, and any validation warnings
    """
    schema = CircuitSchema.model_validate_json(schema_json)
    cm = CircuitManager(get_db())
    circuit_id = cm.create(schema)
    warnings = cm.validate(circuit_id)

    result = f"Circuit '{schema.name}' created with ID: {circuit_id}\n"
    result += f"Components: {len(schema.components)}, "
    result += f"Subcircuits: {len(schema.subcircuit_instances)}\n"
    if warnings:
        result += "Warnings:\n" + "\n".join(f"  - {w}" for w in warnings)
    return result


@mcp.tool()
def modify_circuit(circuit_id: str, modification_json: str) -> str:
    """Apply incremental changes to a stored circuit.

    Args:
        circuit_id: ID of the circuit to modify
        modification_json: JSON with add/remove/update/rename_node/connect operations

    Returns:
        Updated summary and new version number
    """
    mod = CircuitModification.model_validate_json(modification_json)
    cm = CircuitManager(get_db())
    version = cm.modify(circuit_id, mod)
    schema = cm.get_schema(circuit_id)
    return f"Circuit updated to version {version}. Components: {len(schema.components)}"


@mcp.tool()
def get_circuit(circuit_id: str) -> str:
    """Return a circuit's current schema as JSON."""
    cm = CircuitManager(get_db())
    schema = cm.get_schema(circuit_id)
    return schema.model_dump_json(indent=2)


@mcp.tool()
def validate_circuit(circuit_id: str) -> str:
    """Check a circuit for errors (floating nodes, shorted sources, missing ground)."""
    cm = CircuitManager(get_db())
    warnings = cm.validate(circuit_id)
    if not warnings:
        return "Circuit validation passed -- no issues found."
    return "Validation issues:\n" + "\n".join(f"  - {w}" for w in warnings)


@mcp.tool()
def list_circuits() -> str:
    """List all circuits in the project."""
    cm = CircuitManager(get_db())
    circuits = cm.list_all()
    if not circuits:
        return "No circuits in this project. Use define_circuit to create one."
    lines = ["| ID | Name | Status | Components |", "|---|------|--------|------------|"]
    for c in circuits:
        lines.append(f"| {c['id'][:8]}... | {c['name']} | {c['status']} | {c['component_count']} |")
    return "\n".join(lines)


@mcp.tool()
def clone_circuit(circuit_id: str, new_name: str) -> str:
    """Copy a circuit for variant exploration."""
    cm = CircuitManager(get_db())
    new_id = cm.clone(circuit_id, new_name)
    return f"Cloned as '{new_name}' with ID: {new_id}"


@mcp.tool()
def delete_circuit(circuit_id: str) -> str:
    """Remove a circuit and its simulation results."""
    cm = CircuitManager(get_db())
    cm.delete(circuit_id)
    return f"Circuit {circuit_id} deleted."
