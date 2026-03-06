"""Bill of Materials generation from CircuitSchema."""

import csv
from pathlib import Path

from electronics_mcp.core.schema import CircuitSchema


def generate_bom(
    schema: CircuitSchema,
    output_path: Path | str,
    include_suppliers: bool = False,
) -> Path:
    """Generate a CSV Bill of Materials.

    Returns the path to the generated CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = ["Reference", "Type", "Value", "Footprint", "Quantity"]
    if include_suppliers:
        headers.extend(["Manufacturer", "MPN", "Supplier"])

    rows = []
    for comp in schema.components:
        value = _get_display_value(comp)
        footprint = _suggest_footprint(comp)
        row = [comp.id, comp.type, value, footprint, "1"]
        if include_suppliers:
            row.extend(["", "", ""])
        rows.append(row)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return output_path


def generate_bom_summary(schema: CircuitSchema) -> dict:
    """Generate a BOM summary with component counts and grouping.

    Returns dict with grouped components and totals.
    """
    groups: dict[str, list[dict]] = {}
    for comp in schema.components:
        key = f"{comp.type}"
        if key not in groups:
            groups[key] = []
        groups[key].append(
            {
                "id": comp.id,
                "value": _get_display_value(comp),
                "type": comp.type,
            }
        )

    return {
        "groups": groups,
        "total_components": len(schema.components),
        "unique_types": len(groups),
    }


def _get_display_value(comp) -> str:
    """Get a human-readable value string for a component."""
    key_map = {
        "resistor": "resistance",
        "capacitor": "capacitance",
        "inductor": "inductance",
        "voltage_source": "voltage",
        "current_source": "current",
    }
    key = key_map.get(comp.type)
    if key and key in comp.parameters:
        return comp.parameters[key]
    if comp.parameters:
        return next(iter(comp.parameters.values()))
    return comp.type


def _suggest_footprint(comp) -> str:
    """Suggest a default footprint."""
    footprints = {
        "resistor": "0805",
        "capacitor": "0805",
        "inductor": "0805",
        "diode": "SOD-123",
        "led": "0805",
    }
    return footprints.get(comp.type, "")
