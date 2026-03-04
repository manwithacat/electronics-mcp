"""Schematic rendering using schemdraw."""
from pathlib import Path
from collections import defaultdict

import schemdraw
import schemdraw.elements as elm

from electronics_mcp.core.schema import CircuitSchema, ComponentBase

# Map component types to schemdraw elements
COMPONENT_MAP = {
    "resistor": elm.Resistor,
    "capacitor": elm.Capacitor,
    "inductor": elm.Inductor,
    "voltage_source": elm.SourceV,
    "current_source": elm.SourceI,
    "diode": elm.Diode,
    "zener": elm.Zener,
    "led": elm.LED,
    "opamp": elm.Opamp,
    "switch": elm.Switch,
    "fuse": elm.Fuse,
}


class SchematicRenderer:
    """Renders circuit schematics to SVG using schemdraw."""

    def render(self, schema: CircuitSchema, output_path: Path | str) -> Path:
        """Render a circuit schema to SVG.

        Uses a simple layout algorithm: arrange components in a path
        following node connections, placing ground-connected components
        vertically downward.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        d = schemdraw.Drawing()

        # Build adjacency info for layout
        node_components = defaultdict(list)
        for comp in schema.components:
            for node in comp.nodes:
                node_components[node].append(comp)

        # Track which components have been drawn
        drawn = set()

        # Find signal path components (not connected to ground on both sides)
        signal_comps = []
        ground_comps = []

        for comp in schema.components:
            if comp.type == "voltage_source":
                ground_comps.append(comp)
            elif schema.ground_node in comp.nodes and comp.type in ("capacitor",):
                ground_comps.append(comp)
            else:
                signal_comps.append(comp)

        # Draw signal path components left-to-right
        for comp in signal_comps:
            if comp.id in drawn:
                continue
            element_cls = COMPONENT_MAP.get(comp.type, elm.ResistorIEC)
            label = self._make_label(comp)
            d += element_cls().label(label)
            drawn.add(comp.id)

        # Draw ground-connected components going down then back
        for comp in ground_comps:
            if comp.id in drawn:
                continue
            element_cls = COMPONENT_MAP.get(comp.type, elm.ResistorIEC)
            label = self._make_label(comp)

            if comp.type == "voltage_source":
                # Draw voltage source as a vertical element with ground
                d += element_cls().down().label(label)
                d += elm.Ground()
                d += elm.Line().up().length(d.unit)
            else:
                d += element_cls().down().label(label)
                d += elm.Ground()
                # Return to the signal path
                d += elm.Line().up().length(d.unit)

            drawn.add(comp.id)

        d.save(str(output_path))
        return output_path

    def _make_label(self, comp: ComponentBase) -> str:
        """Create a label string for a component."""
        # Get the primary parameter value
        param_val = ""
        param_keys = {
            "resistor": "resistance",
            "capacitor": "capacitance",
            "inductor": "inductance",
            "voltage_source": "voltage",
        }
        key = param_keys.get(comp.type)
        if key and key in comp.parameters:
            param_val = comp.parameters[key]
        elif comp.parameters:
            # Use first parameter value
            param_val = next(iter(comp.parameters.values()), "")

        if param_val:
            return f"{comp.id}\n{param_val}"
        return comp.id
