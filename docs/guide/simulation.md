# Simulation

ElectronicsMCP provides both numerical (SPICE) and symbolic circuit analysis.

## Numerical Simulation (SPICE)

### DC Operating Point

Find the steady-state voltages and currents:

```
simulate(circuit_id=1, analysis="dc_operating_point")
```

### AC Analysis

Sweep frequency to get magnitude and phase response:

```
simulate(circuit_id=1, analysis="ac", parameters={
    "start_freq": 1,
    "stop_freq": 1e6,
    "points_per_decade": 20
})
```

### Transient Analysis

Time-domain simulation:

```
simulate(circuit_id=1, analysis="transient", parameters={
    "stop_time": "10m",
    "step": "10u"
})
```

### DC Sweep

Sweep a source value and observe circuit response:

```
simulate(circuit_id=1, analysis="dc_sweep", parameters={
    "source": "V1",
    "start": 0,
    "stop": 5,
    "step": 0.1
})
```

### Parameter Sweep

Vary a component value across a range:

```
simulate(circuit_id=1, analysis="parameter_sweep", parameters={
    "component": "R1",
    "values": ["1k", "10k", "100k"],
    "analysis": "ac"
})
```

## Symbolic Analysis

### Transfer Function

Get the symbolic transfer function in the Laplace domain:

```
symbolic_analysis(circuit_id=1, analysis="transfer_function", parameters={
    "input_node": "vin",
    "output_node": "vout"
})
```

Returns expressions like `H(s) = 1/(1 + s*R*C)` with identified poles and zeros.

### Component Sensitivity

Analyse how component variations affect circuit behaviour:

```
symbolic_analysis(circuit_id=1, analysis="sensitivity", parameters={
    "output": "vout",
    "component": "R1"
})
```

## Working with Results

Simulation results are cached in the database. Use `get_simulation_results` to retrieve previous runs, and `render_plot` to visualise them:

```
render_plot(simulation_id=1, plot_type="bode")
render_plot(simulation_id=1, plot_type="waveform", signals=["V(vout)"])
```
