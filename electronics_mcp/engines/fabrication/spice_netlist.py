"""SPICE netlist file generation from CircuitSchema."""
from pathlib import Path

from electronics_mcp.core.schema import CircuitSchema
from electronics_mcp.core.units import parse_value


def generate_spice_netlist(schema: CircuitSchema, output_path: Path | str) -> Path:
    """Generate a .cir SPICE netlist file from a CircuitSchema.

    Returns the path to the generated file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"* {schema.name}"]
    if schema.description:
        lines.append(f"* {schema.description}")
    lines.append("")

    def spice_node(node: str) -> str:
        return "0" if node == schema.ground_node else node

    for comp in schema.components:
        nodes_str = " ".join(spice_node(n) for n in comp.nodes)
        line = _component_line(comp, nodes_str)
        lines.append(line)

    lines.append("")
    lines.append(".end")

    output_path.write_text("\n".join(lines))
    return output_path


def _spice_val(val: str) -> str:
    """Convert EE value to SPICE-compatible number."""
    try:
        n = parse_value(val)
        if n == int(n) and abs(n) < 1e15:
            return str(int(n))
        return f"{n:g}"
    except ValueError:
        return val


def _component_line(comp, nodes_str: str) -> str:
    """Generate a SPICE netlist line for a component."""
    if comp.type == "resistor":
        return f"R{comp.id.lstrip('R')} {nodes_str} {_spice_val(comp.parameters.get('resistance', '1k'))}"
    elif comp.type == "capacitor":
        return f"C{comp.id.lstrip('C')} {nodes_str} {_spice_val(comp.parameters.get('capacitance', '1n'))}"
    elif comp.type == "inductor":
        return f"L{comp.id.lstrip('L')} {nodes_str} {_spice_val(comp.parameters.get('inductance', '1u'))}"
    elif comp.type == "voltage_source":
        v = comp.parameters.get("voltage", comp.parameters.get("amplitude", "0"))
        if comp.subtype == "ac":
            return f"V{comp.id.lstrip('V')} {nodes_str} AC {_spice_val(v)}"
        return f"V{comp.id.lstrip('V')} {nodes_str} DC {_spice_val(v)}"
    elif comp.type == "current_source":
        return f"I{comp.id.lstrip('I')} {nodes_str} {_spice_val(comp.parameters.get('current', '1m'))}"
    elif comp.type == "diode":
        return f"D{comp.id.lstrip('D')} {nodes_str} D1N4148"
    return f"* {comp.id} ({comp.type})"
