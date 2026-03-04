"""MCP tools for fabrication output (netlists, BOM, components)."""
from electronics_mcp.mcp.server import mcp, get_db, get_config
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.engines.fabrication.spice_netlist import generate_spice_netlist
from electronics_mcp.engines.fabrication.kicad_netlist import generate_kicad_netlist
from electronics_mcp.engines.fabrication.bom import generate_bom, generate_bom_summary
from electronics_mcp.engines.fabrication.components import ComponentSuggester


def _get_schema(circuit_id: str):
    cm = CircuitManager(get_db())
    return cm.get_schema(circuit_id)


@mcp.tool()
def export_spice_netlist(circuit_id: str) -> str:
    """Generate a SPICE .cir netlist file for a circuit.

    Returns the file path of the generated netlist.
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    output_path = config.output_dir / f"{circuit_id[:8]}.cir"
    path = generate_spice_netlist(schema, output_path)
    return f"SPICE netlist saved: {path}"


@mcp.tool()
def export_kicad_netlist(circuit_id: str) -> str:
    """Generate a KiCad .net XML netlist for PCB layout.

    Returns the file path of the generated netlist.
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    output_path = config.output_dir / f"{circuit_id[:8]}.net"
    path = generate_kicad_netlist(schema, output_path)
    return f"KiCad netlist saved: {path}"


@mcp.tool()
def export_bom(circuit_id: str, include_suppliers: bool = False) -> str:
    """Generate a CSV Bill of Materials.

    Args:
        circuit_id: Circuit to generate BOM for
        include_suppliers: Include supplier columns
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    output_path = config.output_dir / f"bom_{circuit_id[:8]}.csv"
    path = generate_bom(schema, output_path, include_suppliers)

    summary = generate_bom_summary(schema)
    lines = [f"BOM saved: {path}"]
    lines.append(f"Total components: {summary['total_components']}")
    lines.append(f"Unique types: {summary['unique_types']}")
    return "\n".join(lines)


@mcp.tool()
def suggest_components(
    component_type: str,
    target_value: str | None = None,
    limit: int = 5,
) -> str:
    """Search the component database for real parts matching requirements.

    Args:
        component_type: Type of component (resistor, capacitor, etc.)
        target_value: Target value (e.g. "10k", "100nF")
        limit: Maximum number of suggestions
    """
    db = get_db()
    db.initialize(seed=True)
    suggester = ComponentSuggester(db)
    results = suggester.suggest(component_type, target_value, limit)

    if not results:
        return f"No {component_type} components found in database."

    lines = [f"Component suggestions for {component_type}" +
             (f" ({target_value})" if target_value else "") + ":", ""]
    for i, comp in enumerate(results, 1):
        lines.append(f"  {i}. {comp.get('manufacturer', '?')} {comp.get('part_number', '?')}")
        if comp.get("description"):
            lines.append(f"     {comp['description']}")
        if comp.get("footprint"):
            lines.append(f"     Footprint: {comp['footprint']}")
    return "\n".join(lines)


@mcp.tool()
def component_selection_guide(component_type: str) -> str:
    """Get a selection guide for choosing a component type.

    Provides typical values, subtypes, and selection criteria.
    """
    db = get_db()
    db.initialize(seed=True)
    suggester = ComponentSuggester(db)
    guides = suggester.get_selection_guide(component_type)

    if not guides:
        return f"No selection guide found for {component_type}."

    lines = [f"Selection Guide: {component_type}", ""]
    for g in guides:
        if g.get("subtype"):
            lines.append(f"  Subtype: {g['subtype']}")
        if g.get("selection_guide"):
            lines.append(f"  Guide: {g['selection_guide']}")
        if g.get("typical_values"):
            lines.append(f"  Typical values: {', '.join(str(v) for v in g['typical_values'])}")
        lines.append("")
    return "\n".join(lines)
