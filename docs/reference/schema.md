# Circuit Description Schema

Circuits are described as JSON objects following a structured schema. This is the core data model that all tools operate on.

## Core Schema

```json
{
  "circuit": {
    "name": "RC Low-Pass Filter",
    "description": "First-order low-pass filter with 1.59kHz cutoff",
    "design_intent": {
      "topology": "low_pass_filter",
      "target_specs": {
        "cutoff_frequency_hz": 1590,
        "input_impedance_min_ohms": 10000
      }
    },
    "ground_node": "gnd",
    "components": [...],
    "subcircuit_instances": [...],
    "probes": [
      {"node": "output", "label": "Vout"}
    ]
  }
}
```

## Component Types

### Passive

| Type | Required Parameters | Optional Parameters |
|------|-------------------|-------------------|
| `resistor` | `resistance` | `tolerance`, `power_rating`, `temp_coeff` |
| `capacitor` | `capacitance` | `esr`, `voltage_rating`, `dielectric` |
| `inductor` | `inductance` | `dcr`, `saturation_current`, `srf` |
| `potentiometer` | `resistance` | `wiper_position` |
| `fuse` | `rating` | `type` (fast/slow) |
| `crystal` | `frequency` | `load_capacitance` |

### Source

| Type | Subtypes | Parameters |
|------|----------|-----------|
| `voltage_source` | `dc`, `ac`, `pulse`, `pwl`, `custom` | Varies by subtype |
| `current_source` | `dc`, `ac`, `pulse`, `pwl`, `custom` | Varies by subtype |
| `dependent_source` | `vcvs`, `vccs`, `ccvs`, `cccs` | `gain` |

### Semiconductor

| Type | Parameters |
|------|-----------|
| `diode` | `model` or `is`, `n`, `bv` |
| `zener` | `breakdown_voltage`, optional `model` |
| `led` | `forward_voltage`, `colour` |
| `bjt` | `npn`/`pnp`, `model` or `beta`, `vbe` |
| `mosfet` | `nmos`/`pmos`, `model` or `vth`, `rds_on`, `ciss` |
| `jfet` | `n`/`p`, `model` or `idss`, `vp` |
| `igbt` | `model` |

### Integrated Circuit

| Type | Parameters |
|------|-----------|
| `opamp` | `model`, optional `gbw`, `slew_rate`, `vos`, `ib` |
| `comparator` | `model`, optional `response_time` |
| `voltage_regulator` | `type` (linear/switching), `model`, optional `vin_range`, `vout`, `iout_max` |
| `timer_555` | (none -- behaviour from circuit topology) |
| `custom_ic` | `model`, `pinout` |

## Engineering Units

Values accept standard EE shorthand with SI prefixes:

| Suffix | Multiplier | Example |
|--------|-----------|---------|
| `p` | 10^-12 | `100p` (100 pF) |
| `n` | 10^-9 | `10n` (10 nF) |
| `u` or `µ` | 10^-6 | `47u` (47 uF) |
| `m` | 10^-3 | `2.2m` (2.2 mH) |
| (none) | 1 | `100` (100 Ohm) |
| `k` | 10^3 | `10k` (10 kOhm) |
| `M` | 10^6 | `1M` (1 MOhm) |

Also accepts explicit units: `10kohm`, `100nF`, `2.2mH`, `1uA`.

## Incremental Modification

Modify circuits without redefining them entirely:

```json
{
  "modify": {
    "add": [
      {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["output", "gnd"]}
    ],
    "remove": ["R3"],
    "update": [
      {"id": "R1", "parameters": {"resistance": "22k"}}
    ],
    "rename_node": {"old_output": "filtered_output"},
    "connect": [{"from": "U1.output", "to": "feedback"}]
  }
}
```

## Node Naming Conventions

- `gnd` -- always the reference node (node 0 in SPICE)
- Named nodes preferred over numbers: `input`, `output`, `vcc`, `feedback`, `gate_drive`
- For ICs with many pins, use dot notation: `U1.inverting`, `U1.output`
- Implicit connections: components sharing a node name are connected
