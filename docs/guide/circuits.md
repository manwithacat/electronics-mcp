# Working with Circuits

## Creating a Circuit

Use `create_circuit` to start a new design:

```
create_circuit(name="voltage-divider", description="Simple resistive divider")
```

This creates a circuit with an empty component list and stores it in the project database.

## Adding Components

Add components one at a time with `add_component`:

```
add_component(circuit_id=1, component={
    "id": "R1",
    "type": "resistor",
    "value": "10k",
    "nodes": ["vin", "vout"]
})
```

The value field accepts EE shorthand: `10k`, `4.7u`, `100n`, `1M`.

## Connecting Components

Components connect through shared node names. Use descriptive names:

- `vin`, `vout` -- signal nodes
- `vcc`, `vdd` -- power rails
- `gnd`, `0` -- ground reference
- `net1`, `net2` -- internal nets

## Modifying Circuits

Use `modify_circuit` for incremental changes without resending the entire design:

```
modify_circuit(circuit_id=1, modifications={
    "add": [{"id": "C1", "type": "capacitor", "value": "100n", "nodes": ["vout", "gnd"]}],
    "update": [{"id": "R1", "value": "22k"}],
    "remove": ["R_old"]
})
```

## Versioning

Every modification creates an immutable version snapshot. Use `list_versions` and `get_version` to browse history, or `restore_version` to revert.

## Subcircuit Instances

Reference library subcircuits with `add_subcircuit_instance`:

```
add_subcircuit_instance(circuit_id=1, instance={
    "id": "U1",
    "subcircuit": "non_inverting_amp",
    "parameters": {"gain": 10},
    "connections": {"in": "vin", "out": "vout", "vcc": "vcc", "vee": "vee"}
})
```

## Probes and Design Intent

Add probes to mark measurement points for simulation:

```
modify_circuit(circuit_id=1, modifications={
    "add_probes": [
        {"node": "vout", "type": "voltage"},
        {"component": "R1", "type": "current"}
    ]
})
```

Set design intent to guide automated analysis:

```
modify_circuit(circuit_id=1, modifications={
    "set_design_intent": {
        "function": "low_pass_filter",
        "target_specs": {"cutoff_hz": 1000, "gain_db": 0}
    }
})
```
