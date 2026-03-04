# MCP Tools Reference

ElectronicsMCP exposes 47 tools across 9 categories.

## Circuit Definition Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `define_circuit` | Create a new circuit from full JSON schema | Circuit ID, summary, validation warnings |
| `modify_circuit` | Apply incremental changes to a stored circuit | Updated summary, new version number |
| `get_circuit` | Return a circuit's current schema | Full JSON |
| `validate_circuit` | Check for errors (floating nodes, shorted sources) | Structured error/warning list |
| `list_circuits` | List all circuits in the project | Table of circuits with status |
| `clone_circuit` | Copy a circuit for variant exploration | New circuit ID |
| `delete_circuit` | Remove a circuit and its simulation results | Confirmation |

## Subcircuit Library Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `list_subcircuits` | List available subcircuits, optionally filtered by category | Table with ports and parameters |
| `get_subcircuit` | Retrieve a subcircuit's full definition | Schema JSON with documentation |
| `create_subcircuit` | Promote a circuit (or part of one) to a reusable subcircuit | Subcircuit ID |
| `import_subcircuit` | Import from a SPICE .subckt definition | Subcircuit ID |

## Simulation Tools (Numerical -- PySpice)

| Tool | Description | Key Parameters | Returns |
|------|-------------|----------------|---------|
| `dc_operating_point` | All node voltages and branch currents | `circuit_id` | Table of voltages/currents |
| `dc_sweep` | Sweep a source or component value | `source, start, stop, step` | Plot file path + data summary |
| `ac_analysis` | Frequency response | `start_freq, stop_freq, points_per_decade` | Bode plot file path + key metrics |
| `transient_analysis` | Time-domain simulation | `duration, step_size, [initial_conditions]` | Waveform plot file path + measurements |
| `parametric_sweep` | Sweep a component value across analyses | `component, values, analysis_type` | Overlaid plot file path |
| `monte_carlo` | Statistical analysis with component tolerances | `num_runs, tolerance_spec` | Distribution plot + statistics |

## Simulation Tools (Symbolic -- lcapy)

| Tool | Description | Returns |
|------|-------------|---------|
| `transfer_function` | Derive H(s) between two nodes | LaTeX + Python-evaluable form |
| `impedance` | Calculate impedance between two nodes | Symbolic expression |
| `node_voltage_expression` | Symbolic voltage at a node | Expression in terms of component values |
| `simplify_network` | Series/parallel reduction | Simplified equivalent circuit |
| `poles_and_zeros` | Extract poles and zeros | Pole-zero locations + s-plane plot |
| `step_response` | Symbolic step response | Time-domain expression + plot |

## Rendering Tools

| Tool | Description | Output |
|------|-------------|--------|
| `draw_schematic` | Circuit schematic from current definition | SVG in `./output/schematics/` |
| `draw_bode` | Bode plot from AC analysis | PNG/SVG in `./output/plots/` |
| `draw_waveform` | Time-domain plot | PNG/SVG in `./output/plots/` |
| `draw_phasor` | Phasor diagram | PNG/SVG in `./output/plots/` |
| `draw_pole_zero` | Pole-zero plot in s-plane | PNG/SVG in `./output/plots/` |
| `generate_report` | Comprehensive Markdown with embedded images | `.md` in `./output/reports/` |
| `generate_pdf` | PDF version of a report | `.pdf` in `./output/reports/` |

## Fabrication Tools

| Tool | Description | Output |
|------|-------------|--------|
| `generate_spice_netlist` | SPICE netlist for external tools | `.cir` file |
| `generate_kicad_netlist` | KiCad-compatible netlist | `.net` file |
| `generate_bom` | Bill of materials with supplier references | `.csv` + formatted table |
| `suggest_components` | Real components matching parameters | Component list from DB + optional live search |
| `breadboard_layout` | Physical breadboard arrangement | Visual layout image |

## Knowledge Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `search_knowledge` | Full-text search across the knowledge base | Ranked results |
| `get_topic` | Retrieve a specific knowledge article | Markdown content |
| `explain_topology` | Describe a circuit topology with theory | Structured explanation |
| `design_guide` | Step-by-step design procedure | Design walkthrough |
| `component_info` | Detailed info about a component type/model | Specs, usage, gotchas |
| `list_formulas` | Formulas for a given topic | LaTeX + Python expressions |
| `what_if` | Predict qualitative effect of a change | Analysis of expected behaviour |
| `check_design` | Compare simulation results against design intent | Pass/fail with recommendations |
| `learn_pattern` | Store a new design pattern or insight | Confirmation |

## Comparison Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `create_comparison` | Set up a comparison between circuits | Comparison ID |
| `compare_simulations` | Run same analysis on multiple circuits | Comparison table + overlaid plots |
| `compare_boms` | Compare bills of materials | Cost/component count comparison |
| `rank_designs` | Score designs against weighted criteria | Ranked table with rationale |

## Database Management Tools

| Tool | Description |
|------|-------------|
| `init_project` | Initialise a new project database with seed data |
| `import_spice_model` | Import a SPICE model from a `.lib` file |
| `export_project` | Export project data as a portable archive |
| `query_db` | Execute a read-only SQL query (advanced users / debugging) |
