"""KiCad netlist generation from CircuitSchema."""
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from electronics_mcp.core.schema import CircuitSchema


# Map our types to KiCad library references
KICAD_LIB_MAP = {
    "resistor": ("Device", "R"),
    "capacitor": ("Device", "C"),
    "inductor": ("Device", "L"),
    "voltage_source": ("Simulation_SPICE", "VDC"),
    "current_source": ("Simulation_SPICE", "IDC"),
    "diode": ("Device", "D"),
    "led": ("Device", "LED"),
    "bjt": ("Device", "Q_NPN_BCE"),
    "mosfet": ("Device", "Q_NMOS_GDS"),
    "opamp": ("Amplifier_Operational", "LM358"),
}


def generate_kicad_netlist(schema: CircuitSchema, output_path: Path | str) -> Path:
    """Generate a KiCad .net XML netlist.

    Returns the path to the generated file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    root = Element("export", version="E")

    # Design section
    design = SubElement(root, "design")
    source = SubElement(design, "source")
    source.text = schema.name

    # Components section
    components = SubElement(root, "components")
    for comp in schema.components:
        comp_el = SubElement(components, "comp", ref=comp.id)
        value_el = SubElement(comp_el, "value")
        # Get primary parameter value
        param_val = _get_primary_value(comp)
        value_el.text = param_val

        lib_info = KICAD_LIB_MAP.get(comp.type)
        if lib_info:
            libsource = SubElement(comp_el, "libsource",
                                   lib=lib_info[0], part=lib_info[1])

        footprint_el = SubElement(comp_el, "footprint")
        footprint_el.text = _suggest_footprint(comp)

    # Nets section
    nets = SubElement(root, "nets")
    node_map = _build_node_map(schema)
    for i, (node_name, pins) in enumerate(sorted(node_map.items()), 1):
        net_name = "GND" if node_name == schema.ground_node else node_name
        net = SubElement(nets, "net", code=str(i), name=net_name)
        for comp_id, pin_num in pins:
            SubElement(net, "node", ref=comp_id, pin=str(pin_num))

    tree = ElementTree(root)
    indent(tree, space="  ")
    tree.write(str(output_path), encoding="unicode", xml_declaration=True)

    return output_path


def _get_primary_value(comp) -> str:
    """Get the primary parameter value for display."""
    key_map = {
        "resistor": "resistance",
        "capacitor": "capacitance",
        "inductor": "inductance",
        "voltage_source": "voltage",
    }
    key = key_map.get(comp.type)
    if key and key in comp.parameters:
        return comp.parameters[key]
    if comp.parameters:
        return next(iter(comp.parameters.values()))
    return comp.type


def _suggest_footprint(comp) -> str:
    """Suggest a default footprint for a component."""
    footprints = {
        "resistor": "Resistor_SMD:R_0805_2012Metric",
        "capacitor": "Capacitor_SMD:C_0805_2012Metric",
        "inductor": "Inductor_SMD:L_0805_2012Metric",
        "diode": "Diode_SMD:D_SOD-123",
        "led": "LED_SMD:LED_0805_2012Metric",
    }
    return footprints.get(comp.type, "")


def _build_node_map(schema: CircuitSchema) -> dict[str, list[tuple[str, int]]]:
    """Map node names to (component_id, pin_number) pairs."""
    node_map: dict[str, list[tuple[str, int]]] = {}
    for comp in schema.components:
        for pin_num, node in enumerate(comp.nodes, 1):
            if node not in node_map:
                node_map[node] = []
            node_map[node].append((comp.id, pin_num))
    return node_map
