# Quick Start

## Your First Circuit

Once ElectronicsMCP is configured in Claude Code, start a conversation:

> "Create a simple voltage divider with 10k resistors powered by 12V"

The agent will define the circuit, simulate the DC operating point, and show you the output voltage (6V with equal resistors).

## Explore and Iterate

> "What happens if I change R2 to 22k?"

The agent modifies the circuit, re-simulates, and shows the new output (approximately 8.25V).

## Add Complexity

> "Now add an RC low-pass filter after the voltage divider with a 1kHz cutoff"

The agent adds components, runs AC analysis, draws the Bode plot, and verifies the cutoff frequency.

## Generate Outputs

> "Draw the schematic and generate a BOM"

You get an SVG schematic in `output/schematics/` and a CSV bill of materials in `output/bom/`.

## Interactive Exploration

Open the web UI to adjust component values with sliders and see plots update in real time:

```bash
python -m electronics_mcp.web.run
```

Then tell the agent:

> "I've been tweaking the filter in the web UI -- the version with C1=47uF gives the best response. Save that as the final design and generate a report."

## Project Structure

After working with ElectronicsMCP, your project directory looks like:

```
my-project/
├── data/
│   └── ee.db              # SQLite database (circuits, knowledge, results)
├── output/
│   ├── schematics/        # SVG/PNG circuit diagrams
│   ├── plots/             # Bode plots, waveforms, pole-zero diagrams
│   ├── reports/           # Markdown and PDF design documents
│   ├── netlists/          # SPICE .cir and KiCad .net files
│   └── bom/               # CSV bills of materials
├── models/                # User-imported SPICE models
└── .mcp.json              # MCP server configuration
```
