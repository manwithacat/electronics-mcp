# ElectronicsMCP -- Design Document

**Date:** 2026-03-04
**Status:** Approved
**Based on:** Master Spec v1.0, Spec v2, Seed Data Strategy

## Summary

An MCP server providing electronic engineering context and skills to LLM agents. Enables circuit modeling, SPICE simulation, symbolic analysis, schematic rendering, fabrication output, and a persistent knowledge base -- all exposed via MCP tools. Includes a Dazzle-based web UI for interactive parameter exploration.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Layered library with thin interfaces | Engines testable independently; MCP and web UI are thin wrappers |
| MCP framework | FastMCP (Python) | Spec requirement; Python ecosystem for PySpice/lcapy/schemdraw |
| Database | SQLite with FTS5 | Project-scoped, offline-first, no external dependencies |
| Web UI | Dazzle + custom stubs | Dazzle handles CRUD views; custom stubs for parameter explorer, waveform viewer |
| Seed data | Full ingestion pipeline from real sources | Kuphaldt HTML, Ngspice models, KiCad symbols |
| Build scope | All 4 phases at once | Complete system in initial build |

---

## 1. Project Structure

```
electronics-mcp/
├── pyproject.toml
├── electronics_mcp/
│   ├── __init__.py
│   ├── config.py                  # Project paths, DB location, settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite connection, schema init, migrations
│   │   ├── schema.py              # Circuit JSON schema validation (Pydantic)
│   │   ├── models.py              # Pydantic models for all DB entities
│   │   ├── units.py               # EE unit parsing (10k -> 10000, 47u -> 47e-6)
│   │   └── circuit_manager.py     # CRUD, versioning, netlist generation
│   ├── engines/
│   │   ├── simulation/
│   │   │   ├── numerical.py       # PySpice wrapper (DC, AC, transient, sweep, Monte Carlo)
│   │   │   └── symbolic.py        # lcapy wrapper (transfer function, impedance, poles/zeros)
│   │   ├── rendering/
│   │   │   ├── schematic.py       # schemdraw -> SVG
│   │   │   ├── plots.py           # matplotlib -> PNG/SVG (Bode, waveform, phasor, pole-zero)
│   │   │   └── reports.py         # Markdown + PDF generation (weasyprint)
│   │   ├── fabrication/
│   │   │   ├── spice_netlist.py   # .cir export
│   │   │   ├── kicad_netlist.py   # .net export
│   │   │   ├── bom.py             # BOM generation (.csv)
│   │   │   └── components.py      # Component suggestion/matching
│   │   └── knowledge/
│   │       ├── manager.py         # Knowledge CRUD, FTS5 search
│   │       ├── topology.py        # Topology explanations
│   │       └── design_guide.py    # Step-by-step design procedures
│   ├── mcp/
│   │   ├── server.py              # FastMCP server entry point
│   │   ├── tools_circuit.py       # define_circuit, modify_circuit, get, validate, list, clone, delete
│   │   ├── tools_simulation.py    # dc_operating_point, dc_sweep, ac_analysis, transient, parametric_sweep, monte_carlo
│   │   ├── tools_symbolic.py      # transfer_function, impedance, node_voltage_expression, simplify_network, poles_and_zeros, step_response
│   │   ├── tools_rendering.py     # draw_schematic, draw_bode, draw_waveform, draw_phasor, draw_pole_zero, generate_report, generate_pdf
│   │   ├── tools_fabrication.py   # generate_spice_netlist, generate_kicad_netlist, generate_bom, suggest_components, breadboard_layout
│   │   ├── tools_knowledge.py     # search_knowledge, get_topic, explain_topology, design_guide, component_info, list_formulas, what_if, check_design, learn_pattern
│   │   ├── tools_comparison.py    # create_comparison, compare_simulations, compare_boms, rank_designs
│   │   ├── tools_db.py            # init_project, import_spice_model, export_project, query_db
│   │   └── resources.py           # MCP resource URI handlers (electronics://...)
│   ├── web/                       # Dazzle project for interactive web UI
│   │   ├── dazzle.toml
│   │   ├── dsl/
│   │   │   └── app.dsl            # Entity/surface definitions
│   │   ├── stubs/
│   │   │   ├── parameter_explorer.py
│   │   │   ├── waveform_viewer.py
│   │   │   └── circuit_comparison.py
│   │   └── templates/
│   └── ingestion/
│       ├── ingest_kuphaldt.py     # HTML -> knowledge articles + formulas
│       ├── ingest_spice_models.py # .lib/.model -> component_models
│       ├── ingest_kicad_symbols.py# .kicad_sym -> component_models + categories
│       ├── build_subcircuits.py   # Authored JSON -> subcircuits table
│       ├── build_design_rules.py  # Authored Markdown -> knowledge table
│       ├── build_formulas.py      # Extracted + authored -> knowledge formulas
│       └── qa.py                  # Validation pipeline for seed data
├── seed/
│   ├── sources/                   # Downloaded source materials
│   ├── staging.db                 # Staging DB before promotion
│   └── seed_data.sql              # Final seed SQL shipped with the server
├── tests/
│   ├── test_core/
│   ├── test_engines/
│   ├── test_mcp/
│   └── test_ingestion/
└── .mcp.json                      # MCP server configuration
```

**Layering principle:** Engine modules are pure Python with no MCP or web dependencies. MCP tools and web routes are thin wrappers that call engine functions, format results for their respective consumers (LLM vs browser).

---

## 2. Database Schema

Direct implementation of Master Spec Section 3.2. Tables:

- **circuits** -- project circuit designs with JSON schema, design intent, status, versioning
- **circuit_versions** -- immutable version snapshots for each circuit modification
- **subcircuits** -- reusable circuit blocks with named ports and tuneable parameters
- **component_models** -- SPICE models with electrical parameters, footprints, supplier refs
- **component_categories** -- selection guides and typical value ranges by type/subtype
- **simulation_results** -- cached results keyed by circuit_id + analysis_type + parameters
- **knowledge** -- articles with category, topic, difficulty, formulas, related topics
- **knowledge_fts** -- FTS5 virtual table over knowledge for full-text search
- **project_notes** -- user/agent annotations on circuits
- **design_decisions** -- recorded design rationale with alternatives considered
- **comparisons** -- circuit comparison setups with axes and results
- **provenance** -- source tracking for every seeded record (source_name, licence, original_path)

---

## 3. Circuit Description Schema

Pydantic model hierarchy implementing Master Spec Section 4:

### Core Models

```python
class Probe(BaseModel):
    node: str
    label: str

class DesignIntent(BaseModel):
    topology: str | None = None
    target_specs: dict[str, float | str] = {}

class ComponentBase(BaseModel):
    id: str                          # Reference designator (R1, C1, U1, etc.)
    type: str                        # From component type hierarchy
    subtype: str | None = None       # e.g., "ac" for voltage_source
    parameters: dict[str, str]       # Values as strings with EE units
    nodes: list[str]                 # Connection nodes

class SubcircuitInstance(BaseModel):
    id: str
    reference: str                   # Name in subcircuits table
    parameters: dict[str, str] = {}  # Parameter overrides
    port_connections: dict[str, str] # Port name -> circuit node

class CircuitSchema(BaseModel):
    name: str
    description: str | None = None
    design_intent: DesignIntent | None = None
    ground_node: str = "gnd"
    components: list[ComponentBase] = []
    subcircuit_instances: list[SubcircuitInstance] = []
    probes: list[Probe] = []
```

### Component Type Hierarchy

```
passive:     resistor, capacitor, inductor, potentiometer, fuse, crystal
source:      voltage_source, current_source, dependent_source
semiconductor: diode, zener, led, bjt, mosfet, jfet, igbt
integrated_circuit: opamp, comparator, voltage_regulator, timer_555, custom_ic
subcircuit:  (reference to subcircuits table)
transformer: transformer
electromechanical: relay, switch, connector
```

### Engineering Units

Parser handles: `10k` -> 10000, `47u` -> 4.7e-5, `100nF` -> 1e-7, `2.2mH` -> 2.2e-3. Both SI prefix shorthand and explicit unit suffixes.

### Incremental Modification

```python
class CircuitModification(BaseModel):
    add: list[ComponentBase] = []
    remove: list[str] = []           # Component IDs to remove
    update: list[ComponentUpdate] = []
    rename_node: dict[str, str] = {} # old_name -> new_name
    connect: list[Connection] = []   # Explicit new connections
```

---

## 4. Engines

### 4.1 Numerical Simulation (PySpice/Ngspice)

**Flow:** Circuit JSON -> netlist generation (expand subcircuits, resolve SPICE models from DB) -> PySpice circuit object -> Ngspice execution -> results extraction -> plot generation + DB caching.

**Netlist generation** in `circuit_manager.py`:
- Flatten subcircuit references recursively with cycle detection
- Pull SPICE models from `component_models.spice_model`
- Write temporary `.lib` file for referenced models
- Produce clean PySpice circuit programmatically

**Analysis types:**
- `dc_operating_point(circuit)` -> dict of node voltages and branch currents
- `dc_sweep(circuit, source, start, stop, step)` -> sweep data + plot
- `ac_analysis(circuit, start_freq, stop_freq, points_per_decade)` -> Bode data + plot + key metrics (bandwidth, gain margin, phase margin)
- `transient_analysis(circuit, duration, step_size, initial_conditions)` -> waveform data + plot + measurements (rise time, overshoot, settling time)
- `parametric_sweep(circuit, component, values, analysis_type)` -> overlaid plots
- `monte_carlo(circuit, num_runs, tolerance_spec)` -> distribution plot + statistics

**Design intent checking:** After simulation, compare results against `design_intent.target_specs`. Report pass/fail with measured vs target values.

**Caching:** Results stored in `simulation_results` keyed by (circuit_id, circuit_version, analysis_type, parameters_hash). Unchanged circuits return cached results.

### 4.2 Symbolic Analysis (lcapy)

- `transfer_function(circuit, input_node, output_node)` -> LaTeX expression + Python-evaluable SymPy expression
- `impedance(circuit, node_a, node_b)` -> symbolic impedance expression
- `node_voltage_expression(circuit, node)` -> symbolic voltage in terms of component values
- `simplify_network(circuit)` -> series/parallel reduction to equivalent circuit
- `poles_and_zeros(circuit, input_node, output_node)` -> pole/zero locations + s-plane plot
- `step_response(circuit, input_node, output_node)` -> time-domain expression + plot

### 4.3 Rendering

**Schematics** (`schemdraw`):
- Component-type-to-schemdraw-element registry maps our JSON types to drawing elements
- Auto-layout based on node connections
- SVG output to `./output/schematics/`

**Plots** (`matplotlib`):
- Bode plot (magnitude + phase subplots)
- Waveform plot (time-domain, multiple traces)
- Phasor diagram
- Pole-zero plot (s-plane with unit circle)
- All output to `./output/plots/` as PNG/SVG

**Reports** (`Jinja2` + `weasyprint`):
- Markdown template with embedded image references
- Design rationale, component selection, simulation results
- PDF conversion via weasyprint

### 4.4 Fabrication

- **SPICE netlist** (`.cir`): Flatten circuit JSON to standard SPICE format
- **KiCad netlist** (`.net`): Map components to KiCad footprints from component library
- **BOM** (`.csv`): Component values, MPN, supplier refs, quantities
- **Component suggestion**: Query `component_models` to match ideal parameters to real parts. Optional live search via API enrichment (Phase 4).

---

## 5. MCP Interface

### 5.1 Tools (47 total)

All tools follow the pattern: parse inputs -> call engine -> format result for LLM.

**Circuit Definition (7):** define_circuit, modify_circuit, get_circuit, validate_circuit, list_circuits, clone_circuit, delete_circuit

**Subcircuit Library (4):** list_subcircuits, get_subcircuit, create_subcircuit, import_subcircuit

**Simulation - Numerical (6):** dc_operating_point, dc_sweep, ac_analysis, transient_analysis, parametric_sweep, monte_carlo

**Simulation - Symbolic (6):** transfer_function, impedance, node_voltage_expression, simplify_network, poles_and_zeros, step_response

**Rendering (7):** draw_schematic, draw_bode, draw_waveform, draw_phasor, draw_pole_zero, generate_report, generate_pdf

**Fabrication (5):** generate_spice_netlist, generate_kicad_netlist, generate_bom, suggest_components, breadboard_layout

**Knowledge (9):** search_knowledge, get_topic, explain_topology, design_guide, component_info, list_formulas, what_if, check_design, learn_pattern

**Comparison (4):** create_comparison, compare_simulations, compare_boms, rank_designs

**Database Management (4):** init_project, import_spice_model, export_project, query_db

### 5.2 Resources (6 URI schemes)

| URI | Description |
|-----|-------------|
| `electronics://topologies/{name}` | Topology reference material |
| `electronics://components/{type}` | Component reference (characteristics, selection) |
| `electronics://design-rules/{domain}` | Design heuristics (e.g., power -> thermal mgmt) |
| `electronics://formulas/{topic}` | Key formulas with derivations |
| `electronics://safety/{topic}` | Safety guidance (mains isolation, ESD, battery) |
| `electronics://standards/{name}` | Relevant standards references |

Backed by knowledge base queries. Structured alternative to full-text search.

---

## 6. Web UI (Dazzle + Custom Stubs)

### 6.1 Dazzle-Managed Views

DSL entities and surfaces for standard CRUD/browse operations:

- **Circuit** entity -> list surface (circuit browser with status), detail surface
- **ComponentModel** entity -> list surface (searchable by type, parameters), detail surface
- **Knowledge** entity -> list surface (browseable by category/topic), detail with related topics
- **Subcircuit** entity -> list surface (grouped by category), detail with schema/ports

### 6.2 Custom Stubs

**Parameter Explorer** (`/explorer/{circuit_id}`):
- Load circuit, render slider for each component value
- On slider change: debounced HTMX call -> re-simulate -> swap plot images
- Display: schematic, Bode plot, transient waveform, key metrics table
- Same `engines/simulation` module as MCP tools

**Waveform Viewer** (`/waveform/{simulation_id}`):
- Interactive plot using Plotly.js (loaded from CDN, no build step)
- Zoom, pan, cursors, measurements
- Time-domain and frequency-domain views

**Circuit Comparison** (`/compare/{comparison_id}`):
- Side-by-side circuit display
- Synchronized parameter sweeps
- Overlaid frequency responses
- Tabulated metric comparison

### 6.3 UI-Agent Integration

Web UI and MCP server share the same `data/ee.db`. Workflow:
1. Agent designs circuit via conversation -> stored in DB
2. User opens web UI -> sees circuit, adjusts parameters interactively
3. User returns to conversation -> agent queries DB for current state
4. Web UI "share with agent" button writes to `project_notes`

---

## 7. Ingestion Pipeline

### 7.1 Scripts

| Script | Source | Target | Method |
|--------|--------|--------|--------|
| `ingest_kuphaldt.py` | Lessons in Electric Circuits HTML | `knowledge`, `knowledge_fts` | Parse headings -> topics, extract formulas, tag difficulty |
| `ingest_spice_models.py` | Ngspice `.lib`/`.model` files | `component_models` | PySpice parser, extract parameters, normalize units |
| `ingest_kicad_symbols.py` | KiCad `.kicad_sym` files | `component_models`, `component_categories` | Parse S-expressions, extract pin data, footprint refs |
| `build_subcircuits.py` | Authored JSON definitions | `subcircuits` | Validated against circuit schema, ~50 topologies |
| `build_design_rules.py` | Authored Markdown | `knowledge` (category='design_rule') | ~30 core rules |
| `build_formulas.py` | Extracted + authored | `knowledge` (formulas JSON) | LaTeX + Python-evaluable expressions, ~80 formulas |

### 7.2 Quality Assurance (`qa.py`)

Before promotion to `seed_data.sql`:
1. Knowledge articles: title + content > 100 words + related topics + difficulty tag
2. SPICE models: DC operating point converges without error
3. Component data: type + description + (SPICE model or parametric data)
4. Subcircuits: full expansion -> simulation -> rendering pipeline succeeds
5. Formulas: LaTeX renders + Python expression evaluates without error

### 7.3 Provenance

Every seeded record gets a `provenance` entry: source_name, source_url, licence, original_path, extraction_date.

### 7.4 Target Counts

| Category | Count | Primary Source |
|----------|-------|----------------|
| Component models | ~200 | Ngspice distribution + KiCad symbols |
| Subcircuits | ~50 | Authored (topologies from Kuphaldt + reference designs) |
| Knowledge articles | ~100 | Kuphaldt "Lessons in Electric Circuits" (6 volumes) |
| Formulas | ~80 | Extracted from Kuphaldt + authored |
| Design rules | ~30 | Authored (from app notes + domain knowledge) |

---

## 8. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| MCP framework | FastMCP (Python) | Native MCP support, spec requirement |
| Database | SQLite + FTS5 | Offline-first, project-scoped, no dependencies |
| Schema validation | Pydantic v2 | Fast, Python-native, good error messages |
| Numerical simulation | PySpice + Ngspice | Industry-standard SPICE engine |
| Symbolic analysis | lcapy | Purpose-built for linear circuit analysis |
| Schematic rendering | schemdraw | Clean SVG output, good component library |
| Plot generation | matplotlib | Standard, flexible, SVG/PNG output |
| PDF generation | weasyprint | HTML/CSS to PDF, no external dependencies |
| Web UI framework | Dazzle (FastAPI + HTMX + Jinja2) | DSL-driven CRUD views + custom stubs |
| Interactive plots | Plotly.js (CDN) | Zoom/pan/cursor without build step |
| Testing | pytest | Standard Python testing |

---

## 9. Output Directory Structure

```
project/
├── data/
│   └── ee.db                    # SQLite database
├── output/
│   ├── schematics/              # SVG/PNG schematics
│   ├── plots/                   # Simulation plots
│   ├── reports/                 # Generated .md and .pdf
│   ├── netlists/                # .cir and .net exports
│   └── bom/                     # .csv bills of materials
├── models/                      # User-imported SPICE models
└── .mcp.json                    # MCP server configuration
```
