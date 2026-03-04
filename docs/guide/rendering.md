# Rendering & Visualisation

ElectronicsMCP generates schematics, plots, and reports as files in the `output/` directory.

## Schematic Generation

Render a circuit as an SVG schematic:

```
render_schematic(circuit_id=1)
```

Options:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `style` | `default` | Visual style: `default`, `iec`, `ieee` |
| `show_values` | `true` | Display component values on schematic |
| `show_nodes` | `false` | Label all node names |
| `orientation` | `auto` | Layout direction: `auto`, `horizontal`, `vertical` |

Output: `output/schematics/circuit_1_v3.svg`

## Plot Types

### Bode Plot

Magnitude and phase vs frequency from AC analysis:

```
render_plot(simulation_id=1, plot_type="bode")
```

### Waveform Plot

Time-domain signals from transient analysis:

```
render_plot(simulation_id=1, plot_type="waveform", signals=["V(vout)", "V(vin)"])
```

### Pole-Zero Map

From symbolic analysis results:

```
render_plot(simulation_id=1, plot_type="pole_zero")
```

### Phasor Diagram

AC steady-state phasor relationships:

```
render_plot(simulation_id=1, plot_type="phasor", frequency=1000)
```

## PDF Reports

Generate a comprehensive PDF report combining schematics, simulation results, and analysis:

```
generate_report(circuit_id=1, sections=["schematic", "dc_operating_point", "ac_analysis", "bom"])
```

Output: `output/reports/circuit_1_report.pdf`

## Output Directory Structure

```
output/
  schematics/     # SVG circuit diagrams
  plots/          # PNG/SVG simulation plots
  reports/        # PDF comprehensive reports
  exports/        # Netlists, BOMs, other exports
```

All output files are referenced by path in tool responses, allowing Claude Code to present them directly to the user.
