# Fabrication & Export

ElectronicsMCP supports exporting designs for real-world fabrication.

## Netlist Export

Generate SPICE netlists for use in external simulators:

```
export_netlist(circuit_id=1, format="spice")
```

Supported formats:

| Format | Use Case |
|--------|----------|
| `spice` | Standard SPICE netlist (`.cir`) |
| `subcircuit` | Wrapped as `.subckt` for reuse |

Output: `output/exports/circuit_1.cir`

## Bill of Materials

Generate a BOM with component specifications:

```
generate_bom(circuit_id=1)
```

Returns a structured table with component IDs, types, values, and quantities. Components with identical values are grouped.

Options:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `format` | `json` | Output format: `json`, `csv` |
| `include_alternates` | `false` | Include substitute components |

## Component Matching

Find real components that match your design values:

```
match_components(type="capacitor", value="100n", constraints={
    "voltage_rating_min": 25,
    "dielectric": "C0G",
    "package": "0805"
})
```

Searches the component database for matching parts with parametric filtering.

## Design Rule Checks

Validate a circuit against common design rules:

```
check_design_rules(circuit_id=1)
```

Checks include:

- Floating nodes (unconnected pins)
- Missing bypass capacitors on ICs
- Resistor power rating violations
- Voltage rating exceedances
- Missing pull-up/pull-down resistors
