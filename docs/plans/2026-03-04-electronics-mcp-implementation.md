# ElectronicsMCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete MCP server that gives LLM agents real electronic engineering capabilities -- circuit modeling, SPICE simulation, symbolic analysis, schematic rendering, fabrication output, and a persistent knowledge base.

**Architecture:** Layered Python library with independent engine modules (simulation, rendering, fabrication, knowledge) and thin interface layers (FastMCP tools, Dazzle web UI). SQLite database with FTS5 for the knowledge base. All outputs as files in the project directory.

**Tech Stack:** Python 3.12, FastMCP, PySpice/Ngspice, lcapy, schemdraw, matplotlib, Pydantic v2, SQLite/FTS5, Dazzle (FastAPI + HTMX + Jinja2), weasyprint, pytest

**Design doc:** `docs/plans/2026-03-04-electronics-mcp-design.md`
**Source specs:** `electronics-mcp-master-spec-v1_0.pdf`, `electronics-mcp-spec-v2.pdf`, `electronics-mcp-seed-data-strategy.pdf`

---

## Prerequisites

Before starting, install system dependencies:

```bash
brew install ngspice
```

---

## Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `electronics_mcp/__init__.py`
- Create: `electronics_mcp/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.mcp.json`
- Create: `.gitignore`
- Create: `CLAUDE.md`

**Step 1: Initialize git repo and create pyproject.toml**

```toml
[project]
name = "electronics-mcp"
version = "0.1.0"
description = "MCP server providing electronic engineering context and skills to LLM agents"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0",
    "pydantic>=2.0",
    "PySpice>=1.5",
    "lcapy>=1.0",
    "schemdraw>=0.19",
    "matplotlib>=3.8",
    "numpy>=1.26",
    "sympy>=1.12",
    "weasyprint>=62.0",
    "jinja2>=3.1",
    "aiosqlite>=0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
]
web = [
    "fastapi>=0.110",
    "uvicorn>=0.27",
    "httpx>=0.27",
]

[project.scripts]
electronics-mcp = "electronics_mcp.mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create config.py**

```python
# electronics_mcp/config.py
from pathlib import Path
import os

class ProjectConfig:
    """Configuration for an ElectronicsMCP project."""

    def __init__(self, project_dir: str | Path | None = None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.data_dir = self.project_dir / "data"
        self.db_path = self.data_dir / "ee.db"
        self.output_dir = self.project_dir / "output"
        self.schematics_dir = self.output_dir / "schematics"
        self.plots_dir = self.output_dir / "plots"
        self.reports_dir = self.output_dir / "reports"
        self.netlists_dir = self.output_dir / "netlists"
        self.bom_dir = self.output_dir / "bom"
        self.models_dir = self.project_dir / "models"

    def ensure_dirs(self):
        """Create all project directories."""
        for d in [self.data_dir, self.schematics_dir, self.plots_dir,
                  self.reports_dir, self.netlists_dir, self.bom_dir,
                  self.models_dir]:
            d.mkdir(parents=True, exist_ok=True)
```

**Step 3: Create .mcp.json, .gitignore, CLAUDE.md**

`.mcp.json`:
```json
{
  "mcpServers": {
    "electronics": {
      "command": "python",
      "args": ["-m", "electronics_mcp.mcp.server"],
      "cwd": "."
    }
  }
}
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
data/ee.db
output/
seed/sources/
seed/staging.db
.venv/
```

**Step 4: Create tests/conftest.py**

```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path
from electronics_mcp.config import ProjectConfig


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with config."""
    config = ProjectConfig(tmp_path)
    config.ensure_dirs()
    return config
```

**Step 5: Install and verify**

```bash
cd /Volumes/SSD/ee_mcp
pip install -e ".[dev,web]"
pytest --co  # Collect tests (should find 0 but not error)
```

**Step 6: Commit**

```bash
git init
git add -A
git commit -m "feat: project scaffolding with dependencies and config"
```

---

## Task 2: Core -- Database Schema & Connection

**Files:**
- Create: `electronics_mcp/core/__init__.py`
- Create: `electronics_mcp/core/database.py`
- Create: `tests/test_core/__init__.py`
- Create: `tests/test_core/test_database.py`

**Step 1: Write failing tests**

```python
# tests/test_core/test_database.py
import pytest
import sqlite3
from electronics_mcp.core.database import Database


class TestDatabase:
    def test_init_creates_tables(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()

        conn = sqlite3.connect(tmp_project.db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        assert "circuits" in tables
        assert "circuit_versions" in tables
        assert "subcircuits" in tables
        assert "component_models" in tables
        assert "component_categories" in tables
        assert "simulation_results" in tables
        assert "knowledge" in tables
        assert "knowledge_fts" in tables
        assert "project_notes" in tables
        assert "design_decisions" in tables
        assert "comparisons" in tables
        assert "provenance" in tables
        conn.close()

    def test_init_is_idempotent(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()
        db.initialize()  # Should not raise

    def test_connection_context_manager(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize()
        with db.connect() as conn:
            conn.execute("SELECT 1")

    def test_seed_data_loaded(self, tmp_project):
        db = Database(tmp_project.db_path)
        db.initialize(seed=True)
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM component_categories").fetchone()[0]
            assert count > 0  # Seed data populated categories
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_core/test_database.py -v
```
Expected: FAIL -- module not found

**Step 3: Implement database.py**

```python
# electronics_mcp/core/database.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA_SQL = """
-- CIRCUIT STORAGE
CREATE TABLE IF NOT EXISTS circuits (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    schema_json     TEXT NOT NULL,
    design_intent   TEXT,
    parent_id       TEXT REFERENCES circuits(id),
    status          TEXT DEFAULT 'draft',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags            TEXT
);

CREATE TABLE IF NOT EXISTS circuit_versions (
    id              TEXT PRIMARY KEY,
    circuit_id      TEXT NOT NULL REFERENCES circuits(id),
    version         INTEGER NOT NULL,
    schema_json     TEXT NOT NULL,
    change_summary  TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(circuit_id, version)
);

-- SUBCIRCUIT LIBRARY
CREATE TABLE IF NOT EXISTS subcircuits (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT,
    description     TEXT,
    schema_json     TEXT NOT NULL,
    ports           TEXT NOT NULL,
    parameters      TEXT,
    design_notes    TEXT,
    source          TEXT DEFAULT 'seed',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- COMPONENT LIBRARY
CREATE TABLE IF NOT EXISTS component_models (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    manufacturer    TEXT,
    part_number     TEXT,
    description     TEXT,
    parameters      TEXT NOT NULL,
    spice_model     TEXT,
    footprint       TEXT,
    datasheet_url   TEXT,
    suppliers       TEXT,
    source          TEXT DEFAULT 'seed',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS component_categories (
    type            TEXT NOT NULL,
    subtype         TEXT,
    selection_guide TEXT,
    typical_values  TEXT,
    PRIMARY KEY (type, subtype)
);

-- SIMULATION RESULTS
CREATE TABLE IF NOT EXISTS simulation_results (
    id              TEXT PRIMARY KEY,
    circuit_id      TEXT NOT NULL REFERENCES circuits(id),
    circuit_version INTEGER,
    analysis_type   TEXT NOT NULL,
    parameters      TEXT NOT NULL,
    results_json    TEXT NOT NULL,
    plots           TEXT,
    passed_checks   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KNOWLEDGE BASE
CREATE TABLE IF NOT EXISTS knowledge (
    id              TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    topic           TEXT NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    formulas        TEXT,
    related_topics  TEXT,
    difficulty      TEXT,
    source          TEXT DEFAULT 'seed',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    topic, title, content,
    content=knowledge,
    content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, topic, title, content)
    VALUES (new.rowid, new.topic, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, title, content)
    VALUES('delete', old.rowid, old.topic, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, title, content)
    VALUES('delete', old.rowid, old.topic, old.title, old.content);
    INSERT INTO knowledge_fts(rowid, topic, title, content)
    VALUES (new.rowid, new.topic, new.title, new.content);
END;

-- PROJECT METADATA
CREATE TABLE IF NOT EXISTS project_notes (
    id              TEXT PRIMARY KEY,
    circuit_id      TEXT REFERENCES circuits(id),
    note            TEXT NOT NULL,
    author          TEXT DEFAULT 'user',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS design_decisions (
    id              TEXT PRIMARY KEY,
    circuit_id      TEXT NOT NULL REFERENCES circuits(id),
    decision        TEXT NOT NULL,
    rationale       TEXT,
    alternatives    TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CIRCUIT COMPARISON
CREATE TABLE IF NOT EXISTS comparisons (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    circuit_ids     TEXT NOT NULL,
    comparison_axes TEXT,
    results         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PROVENANCE TRACKING
CREATE TABLE IF NOT EXISTS provenance (
    record_table    TEXT NOT NULL,
    record_id       TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT,
    licence         TEXT NOT NULL,
    original_path   TEXT,
    extraction_date TIMESTAMP,
    notes           TEXT,
    PRIMARY KEY (record_table, record_id)
);
"""

# Minimal seed data for component_categories
SEED_CATEGORIES_SQL = """
INSERT OR IGNORE INTO component_categories (type, subtype, selection_guide, typical_values) VALUES
('resistor', NULL, 'Choose based on power rating and tolerance. Carbon film for general use, metal film for precision.', '["10", "22", "47", "100", "220", "470", "1k", "2.2k", "4.7k", "10k", "22k", "47k", "100k", "1M"]'),
('capacitor', 'ceramic', 'C0G/NP0 for precision, X7R for general bypass, Y5V for bulk. Watch for DC bias derating.', '["10p", "22p", "47p", "100p", "1n", "10n", "100n", "1u"]'),
('capacitor', 'electrolytic', 'Aluminum for bulk bypass, tantalum for low-ESR. Watch voltage derating (50% recommended).', '["1u", "10u", "47u", "100u", "470u", "1000u"]'),
('inductor', NULL, 'Check saturation current vs operating current. Shielded for noise-sensitive applications.', '["1u", "2.2u", "4.7u", "10u", "22u", "47u", "100u", "1m", "10m"]'),
('diode', NULL, 'Check forward voltage, reverse recovery time, and current rating.', NULL),
('bjt', 'npn', 'Check hFE range, fT, and power dissipation. 2N2222 for general purpose.', NULL),
('bjt', 'pnp', 'Check hFE range, fT, and power dissipation. 2N2907 for general purpose.', NULL),
('mosfet', 'nmos', 'Check Vgs(th), Rds(on), and gate charge. Logic-level gate for MCU drive.', NULL),
('mosfet', 'pmos', 'Check Vgs(th), Rds(on). Often used for high-side switching.', NULL),
('opamp', NULL, 'Check GBW, slew rate, input offset voltage, supply range. Rail-to-rail for low-voltage.', NULL),
('voltage_regulator', 'linear', 'Simple, low noise. Efficiency = Vout/Vin. Check dropout voltage.', NULL),
('voltage_regulator', 'switching', 'High efficiency. Check switching frequency, inductor requirements, EMI.', NULL);
"""


class Database:
    """SQLite database manager for ElectronicsMCP."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self, seed: bool = True):
        """Create schema and optionally load seed data."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            if seed:
                conn.executescript(SEED_CATEGORIES_SQL)

    @contextmanager
    def connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

**Step 4: Run tests**

```bash
pytest tests/test_core/test_database.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: SQLite database schema with FTS5 knowledge base"
```

---

## Task 3: Core -- EE Unit Parser

**Files:**
- Create: `electronics_mcp/core/units.py`
- Create: `tests/test_core/test_units.py`

**Step 1: Write failing tests**

```python
# tests/test_core/test_units.py
import pytest
from electronics_mcp.core.units import parse_value, format_value


class TestParseValue:
    """Test EE unit string -> float conversion."""

    @pytest.mark.parametrize("input_str,expected", [
        # SI prefix shorthand
        ("100", 100.0),
        ("10k", 10_000.0),
        ("4.7k", 4_700.0),
        ("47u", 47e-6),
        ("10n", 10e-9),
        ("100p", 100e-12),
        ("2.2m", 2.2e-3),
        ("1M", 1e6),
        # Explicit units
        ("10kohm", 10_000.0),
        ("100nF", 100e-9),
        ("2.2mH", 2.2e-3),
        ("1uA", 1e-6),
        ("3.3V", 3.3),
        ("47uF", 47e-6),
        # Edge cases
        ("0", 0.0),
        ("0V", 0.0),
        ("1", 1.0),
    ])
    def test_parse_value(self, input_str, expected):
        result = parse_value(input_str)
        assert abs(result - expected) < expected * 1e-9 + 1e-15


class TestFormatValue:
    """Test float -> EE unit string conversion."""

    @pytest.mark.parametrize("value,expected", [
        (10_000.0, "10k"),
        (47e-6, "47u"),
        (100e-9, "100n"),
        (2.2e-3, "2.2m"),
        (1e6, "1M"),
        (100.0, "100"),
        (100e-12, "100p"),
    ])
    def test_format_value(self, value, expected):
        assert format_value(value) == expected
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_core/test_units.py -v
```

**Step 3: Implement units.py**

```python
# electronics_mcp/core/units.py
"""EE unit parsing and formatting.

Handles SI prefix shorthand (10k, 47u, 100n) and explicit units (10kohm, 100nF).
"""
import re

SI_PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "µ": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
}

# Units to strip before prefix parsing
UNIT_SUFFIXES = [
    "ohm", "ohms", "Ohm", "Ohms",
    "F", "H", "V", "A", "W",
    "Hz", "hz", "s", "S",
]

# For formatting: ordered by magnitude
FORMAT_PREFIXES = [
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "u"),
    (1e-3, "m"),
    (1, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]

_PARSE_PATTERN = re.compile(
    r"^([+-]?\d+\.?\d*)\s*([pnuµmkKMG])?\s*("
    + "|".join(re.escape(s) for s in UNIT_SUFFIXES)
    + r")?$"
)


def parse_value(s: str) -> float:
    """Parse an EE value string to a float.

    Examples: '10k' -> 10000.0, '47u' -> 47e-6, '100nF' -> 100e-9
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty value string")

    match = _PARSE_PATTERN.match(s)
    if match:
        number = float(match.group(1))
        prefix = match.group(2)
        multiplier = SI_PREFIXES.get(prefix, 1.0) if prefix else 1.0
        return number * multiplier

    # Fallback: try plain float
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Cannot parse EE value: {s!r}")


def format_value(value: float) -> str:
    """Format a float as an EE value string.

    Examples: 10000.0 -> '10k', 47e-6 -> '47u'
    """
    if value == 0:
        return "0"

    abs_val = abs(value)
    for magnitude, prefix in reversed(FORMAT_PREFIXES):
        if abs_val >= magnitude * 0.999:
            scaled = value / magnitude
            # Format without trailing zeros
            if scaled == int(scaled):
                return f"{int(scaled)}{prefix}"
            else:
                return f"{scaled:g}{prefix}"

    # Very small values
    scaled = value / 1e-12
    if scaled == int(scaled):
        return f"{int(scaled)}p"
    return f"{scaled:g}p"
```

**Step 4: Run tests**

```bash
pytest tests/test_core/test_units.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: EE unit parser and formatter (SI prefixes + explicit units)"
```

---

## Task 4: Core -- Circuit Schema Models (Pydantic)

**Files:**
- Create: `electronics_mcp/core/schema.py`
- Create: `tests/test_core/test_schema.py`

**Step 1: Write failing tests**

```python
# tests/test_core/test_schema.py
import pytest
from electronics_mcp.core.schema import (
    CircuitSchema, ComponentBase, SubcircuitInstance,
    DesignIntent, Probe, CircuitModification, ComponentUpdate,
    VALID_COMPONENT_TYPES,
)


class TestCircuitSchema:
    def test_minimal_circuit(self):
        circuit = CircuitSchema(
            name="Test",
            components=[
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"},
                              nodes=["input", "output"]),
            ],
        )
        assert circuit.name == "Test"
        assert circuit.ground_node == "gnd"
        assert len(circuit.components) == 1

    def test_full_rc_filter(self):
        circuit = CircuitSchema(
            name="RC Low-Pass Filter",
            description="First-order low-pass filter with 1.59kHz cutoff",
            design_intent=DesignIntent(
                topology="low_pass_filter",
                target_specs={"cutoff_frequency_hz": 1590},
            ),
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="ac",
                              parameters={"amplitude": "1V", "offset": "0V"},
                              nodes=["input", "gnd"]),
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"},
                              nodes=["input", "output"]),
                ComponentBase(id="C1", type="capacitor",
                              parameters={"capacitance": "10n"},
                              nodes=["output", "gnd"]),
            ],
            probes=[
                Probe(node="output", label="Vout"),
            ],
        )
        assert circuit.design_intent.topology == "low_pass_filter"
        assert len(circuit.probes) == 1

    def test_subcircuit_instance(self):
        circuit = CircuitSchema(
            name="With Subcircuit",
            components=[],
            subcircuit_instances=[
                SubcircuitInstance(
                    id="U_BUCK",
                    reference="buck_output_stage",
                    parameters={"inductance": "22u", "capacitance": "47u"},
                    port_connections={"vin": "switch_node", "vout": "output", "gnd": "gnd"},
                ),
            ],
        )
        assert circuit.subcircuit_instances[0].reference == "buck_output_stage"

    def test_invalid_component_type_rejected(self):
        with pytest.raises(ValueError):
            ComponentBase(id="X1", type="invalid_type",
                          parameters={}, nodes=["a", "b"])

    def test_component_needs_at_least_two_nodes(self):
        with pytest.raises(ValueError):
            ComponentBase(id="R1", type="resistor",
                          parameters={"resistance": "10k"}, nodes=["a"])


class TestCircuitModification:
    def test_add_component(self):
        mod = CircuitModification(
            add=[ComponentBase(id="C2", type="capacitor",
                               parameters={"capacitance": "100n"},
                               nodes=["output", "gnd"])],
        )
        assert len(mod.add) == 1

    def test_remove_and_update(self):
        mod = CircuitModification(
            remove=["R3"],
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        assert mod.remove == ["R3"]

    def test_rename_node(self):
        mod = CircuitModification(
            rename_node={"old_output": "filtered_output"},
        )
        assert "old_output" in mod.rename_node
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_core/test_schema.py -v
```

**Step 3: Implement schema.py**

```python
# electronics_mcp/core/schema.py
"""Pydantic models for the circuit description schema.

Implements Master Spec Section 4: Circuit Description Schema.
"""
from pydantic import BaseModel, field_validator, model_validator
from typing import Any

# Valid component types from the type hierarchy
VALID_COMPONENT_TYPES = {
    # Passive
    "resistor", "capacitor", "inductor", "potentiometer", "fuse", "crystal",
    # Source
    "voltage_source", "current_source", "dependent_source",
    # Semiconductor
    "diode", "zener", "led", "bjt", "mosfet", "jfet", "igbt",
    # Integrated circuit
    "opamp", "comparator", "voltage_regulator", "timer_555", "custom_ic",
    # Subcircuit
    "subcircuit",
    # Transformer
    "transformer",
    # Electromechanical
    "relay", "switch", "connector",
}


class Probe(BaseModel):
    node: str
    label: str


class DesignIntent(BaseModel):
    topology: str | None = None
    target_specs: dict[str, float | str] = {}


class ComponentBase(BaseModel):
    id: str
    type: str
    subtype: str | None = None
    parameters: dict[str, str] = {}
    nodes: list[str] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_COMPONENT_TYPES:
            raise ValueError(
                f"Invalid component type: {v!r}. "
                f"Valid types: {sorted(VALID_COMPONENT_TYPES)}"
            )
        return v

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("Component must connect to at least 2 nodes")
        return v


class Connection(BaseModel):
    from_node: str  # Using from_node instead of from (reserved keyword)
    to: str


class SubcircuitInstance(BaseModel):
    id: str
    reference: str
    parameters: dict[str, str] = {}
    port_connections: dict[str, str] = {}


class CircuitSchema(BaseModel):
    name: str
    description: str | None = None
    design_intent: DesignIntent | None = None
    ground_node: str = "gnd"
    components: list[ComponentBase] = []
    subcircuit_instances: list[SubcircuitInstance] = []
    probes: list[Probe] = []


class ComponentUpdate(BaseModel):
    id: str
    parameters: dict[str, str] = {}
    nodes: list[str] | None = None


class CircuitModification(BaseModel):
    add: list[ComponentBase] = []
    remove: list[str] = []
    update: list[ComponentUpdate] = []
    rename_node: dict[str, str] = {}
    connect: list[Connection] = []
```

**Step 4: Run tests**

```bash
pytest tests/test_core/test_schema.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: Pydantic circuit schema models with validation"
```

---

## Task 5: Core -- Circuit Manager (CRUD + Versioning)

**Files:**
- Create: `electronics_mcp/core/circuit_manager.py`
- Create: `tests/test_core/test_circuit_manager.py`

**Step 1: Write failing tests**

```python
# tests/test_core/test_circuit_manager.py
import pytest
import json
from electronics_mcp.core.database import Database
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, ComponentBase, CircuitModification, ComponentUpdate


@pytest.fixture
def cm(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize()
    return CircuitManager(db)


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    description="Test filter",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestCircuitManager:
    def test_create_circuit(self, cm):
        circuit_id = cm.create(RC_FILTER)
        assert circuit_id is not None

        retrieved = cm.get(circuit_id)
        assert retrieved["name"] == "RC Low-Pass"

    def test_list_circuits(self, cm):
        cm.create(RC_FILTER)
        circuits = cm.list_all()
        assert len(circuits) == 1
        assert circuits[0]["name"] == "RC Low-Pass"

    def test_modify_circuit_creates_version(self, cm):
        circuit_id = cm.create(RC_FILTER)

        mod = CircuitModification(
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        version = cm.modify(circuit_id, mod)
        assert version == 2

        schema = cm.get_schema(circuit_id)
        r1 = next(c for c in schema.components if c.id == "R1")
        assert r1.parameters["resistance"] == "22k"

    def test_clone_circuit(self, cm):
        original_id = cm.create(RC_FILTER)
        clone_id = cm.clone(original_id, "RC Clone")
        assert clone_id != original_id
        clone = cm.get(clone_id)
        assert clone["name"] == "RC Clone"

    def test_delete_circuit(self, cm):
        circuit_id = cm.create(RC_FILTER)
        cm.delete(circuit_id)
        assert cm.get(circuit_id) is None

    def test_validate_circuit_finds_floating_nodes(self, cm):
        # A circuit with a node connected to only one component
        schema = CircuitSchema(
            name="Bad Circuit",
            components=[
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"},
                              nodes=["input", "floating_node"]),
            ],
        )
        circuit_id = cm.create(schema)
        warnings = cm.validate(circuit_id)
        assert any("floating" in w.lower() or "unconnected" in w.lower()
                    for w in warnings)

    def test_get_version_history(self, cm):
        circuit_id = cm.create(RC_FILTER)
        mod = CircuitModification(
            update=[ComponentUpdate(id="R1", parameters={"resistance": "22k"})],
        )
        cm.modify(circuit_id, mod)
        versions = cm.get_versions(circuit_id)
        assert len(versions) == 2
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_core/test_circuit_manager.py -v
```

**Step 3: Implement circuit_manager.py**

This is a substantial module. Key methods:
- `create(schema: CircuitSchema) -> str` -- generate UUID, store in DB, create version 1
- `get(circuit_id: str) -> dict | None` -- retrieve circuit metadata
- `get_schema(circuit_id: str) -> CircuitSchema` -- parse stored JSON to Pydantic model
- `modify(circuit_id: str, mod: CircuitModification) -> int` -- apply modification, bump version
- `clone(circuit_id: str, new_name: str) -> str` -- deep copy with new ID
- `delete(circuit_id: str)` -- remove circuit and related data
- `validate(circuit_id: str) -> list[str]` -- check for floating nodes, missing ground, shorted sources
- `list_all() -> list[dict]` -- all circuits with status
- `get_versions(circuit_id: str) -> list[dict]` -- version history
- `generate_netlist(circuit_id: str) -> str` -- expand subcircuits, produce SPICE netlist string

The `modify` method applies the modification to the current schema: adds new components, removes by ID, updates parameters, renames nodes, creates new connections. Then stores the new schema as the next version.

The `validate` method checks:
- Every node is connected to at least 2 components (no floating nodes)
- Ground node exists
- No voltage sources in parallel (short)
- Every component has required parameters for its type

**Step 4: Run tests**

```bash
pytest tests/test_core/test_circuit_manager.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: circuit manager with CRUD, versioning, and validation"
```

---

## Task 6: Core -- Netlist Generation

**Files:**
- Modify: `electronics_mcp/core/circuit_manager.py` (add `generate_netlist` method)
- Create: `tests/test_core/test_netlist.py`

**Step 1: Write failing tests**

```python
# tests/test_core/test_netlist.py
import pytest
from electronics_mcp.core.database import Database
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, ComponentBase, SubcircuitInstance


@pytest.fixture
def cm(tmp_project):
    db = Database(tmp_project.db_path)
    db.initialize()
    return CircuitManager(db)


class TestNetlistGeneration:
    def test_simple_rc_netlist(self, cm):
        schema = CircuitSchema(
            name="RC Filter",
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="dc",
                              parameters={"voltage": "5V"}, nodes=["input", "gnd"]),
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"}, nodes=["input", "output"]),
                ComponentBase(id="C1", type="capacitor",
                              parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
            ],
        )
        circuit_id = cm.create(schema)
        netlist = cm.generate_netlist(circuit_id)

        assert "R1" in netlist
        assert "C1" in netlist
        assert "V1" in netlist
        # Verify it's valid SPICE-ish syntax
        assert ".end" in netlist.lower() or "END" in netlist

    def test_subcircuit_expansion(self, cm):
        # First, store a subcircuit in the DB
        cm.db.connect().__enter__().execute(
            "INSERT INTO subcircuits (id, name, category, schema_json, ports, parameters) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("sub1", "voltage_divider", "passive",
             '{"components": [{"id": "R1", "type": "resistor", "parameters": {"resistance": "PARAM_r_top"}, "nodes": ["vin", "vout"]}, {"id": "R2", "type": "resistor", "parameters": {"resistance": "PARAM_r_bottom"}, "nodes": ["vout", "gnd"]}]}',
             '[{"name": "vin"}, {"name": "vout"}, {"name": "gnd"}]',
             '[{"name": "r_top", "default": "10k"}, {"name": "r_bottom", "default": "10k"}]')
        )

        schema = CircuitSchema(
            name="With Subcircuit",
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="dc",
                              parameters={"voltage": "12V"}, nodes=["input", "gnd"]),
            ],
            subcircuit_instances=[
                SubcircuitInstance(
                    id="U1", reference="voltage_divider",
                    parameters={"r_top": "20k", "r_bottom": "10k"},
                    port_connections={"vin": "input", "vout": "output", "gnd": "gnd"},
                ),
            ],
        )
        circuit_id = cm.create(schema)
        netlist = cm.generate_netlist(circuit_id)

        # Subcircuit should be expanded inline
        assert "20k" in netlist or "20000" in netlist
```

**Step 2-5: Implement, test, commit**

```bash
pytest tests/test_core/test_netlist.py -v
git add -A
git commit -m "feat: SPICE netlist generation with subcircuit expansion"
```

---

## Task 7: Simulation Engine -- Numerical (PySpice)

**Files:**
- Create: `electronics_mcp/engines/__init__.py`
- Create: `electronics_mcp/engines/simulation/__init__.py`
- Create: `electronics_mcp/engines/simulation/numerical.py`
- Create: `tests/test_engines/__init__.py`
- Create: `tests/test_engines/test_numerical.py`

**Step 1: Write failing tests**

Test a simple RC filter DC operating point and AC analysis. These tests require Ngspice installed.

```python
# tests/test_engines/test_numerical.py
import pytest
import math
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.simulation.numerical import NumericalSimulator


@pytest.fixture
def simulator():
    return NumericalSimulator()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V", "offset": "0V"},
                      nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)

VOLTAGE_DIVIDER = CircuitSchema(
    name="Voltage Divider",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="dc",
                      parameters={"voltage": "10V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="R2", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["output", "gnd"]),
    ],
)


class TestDCOperatingPoint:
    def test_voltage_divider(self, simulator):
        results = simulator.dc_operating_point(VOLTAGE_DIVIDER)
        # With equal resistors, output should be half of input
        assert abs(results["node_voltages"]["output"] - 5.0) < 0.01
        assert abs(results["node_voltages"]["input"] - 10.0) < 0.01


class TestACAnalysis:
    def test_rc_filter_cutoff(self, simulator, tmp_path):
        results = simulator.ac_analysis(
            RC_FILTER,
            start_freq=1,
            stop_freq=1e6,
            points_per_decade=100,
            output_node="output",
            plot_dir=tmp_path,
        )
        # Cutoff frequency should be ~1/(2*pi*R*C) = ~1591 Hz
        assert "bandwidth_hz" in results
        assert abs(results["bandwidth_hz"] - 1591) < 200  # Within ~12%


class TestTransientAnalysis:
    def test_rc_step_response(self, simulator, tmp_path):
        step_circuit = CircuitSchema(
            name="RC Step",
            components=[
                ComponentBase(id="V1", type="voltage_source", subtype="pulse",
                              parameters={"v1": "0V", "v2": "5V",
                                          "rise_time": "1n", "pulse_width": "10m"},
                              nodes=["input", "gnd"]),
                ComponentBase(id="R1", type="resistor",
                              parameters={"resistance": "10k"}, nodes=["input", "output"]),
                ComponentBase(id="C1", type="capacitor",
                              parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
            ],
        )
        results = simulator.transient_analysis(
            step_circuit,
            duration=1e-3,
            step_size=1e-6,
            output_node="output",
            plot_dir=tmp_path,
        )
        assert "rise_time" in results or "final_value" in results
```

**Step 2-5: Implement NumericalSimulator, test, commit**

The `NumericalSimulator` class:
- Converts `CircuitSchema` to a PySpice `Circuit` object
- Dispatches to Ngspice for analysis
- Extracts results as Python dicts
- Generates plots to specified directory
- Computes derived metrics (bandwidth, rise time, overshoot, etc.)

Key implementation pattern: a `_build_pyspice_circuit(schema: CircuitSchema) -> PySpice.Circuit` method that maps our component types to PySpice elements.

```bash
pytest tests/test_engines/test_numerical.py -v
git add -A
git commit -m "feat: numerical simulation engine (DC op, AC analysis, transient)"
```

---

## Task 8: Simulation Engine -- DC Sweep, Parametric Sweep, Monte Carlo

**Files:**
- Modify: `electronics_mcp/engines/simulation/numerical.py`
- Create: `tests/test_engines/test_numerical_advanced.py`

Add `dc_sweep`, `parametric_sweep`, and `monte_carlo` methods to the `NumericalSimulator`.

**Tests cover:**
- DC sweep of a voltage source across a range
- Parametric sweep of a resistor value across multiple AC analyses
- Monte Carlo with ±5% tolerances on all passives

```bash
pytest tests/test_engines/test_numerical_advanced.py -v
git add -A
git commit -m "feat: DC sweep, parametric sweep, and Monte Carlo simulation"
```

---

## Task 9: Simulation Engine -- Symbolic (lcapy)

**Files:**
- Create: `electronics_mcp/engines/simulation/symbolic.py`
- Create: `tests/test_engines/test_symbolic.py`

**Step 1: Write failing tests**

```python
# tests/test_engines/test_symbolic.py
import pytest
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.simulation.symbolic import SymbolicAnalyzer


@pytest.fixture
def analyzer():
    return SymbolicAnalyzer()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "R"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "C"}, nodes=["output", "gnd"]),
    ],
)


class TestTransferFunction:
    def test_rc_lowpass_transfer_function(self, analyzer):
        result = analyzer.transfer_function(RC_FILTER, "input", "output")
        assert "latex" in result
        assert "python_expr" in result
        # Should contain 1/(1 + sRC) or equivalent
        assert "s" in result["latex"] or "omega" in result["latex"]


class TestImpedance:
    def test_rc_parallel_impedance(self, analyzer):
        result = analyzer.impedance(RC_FILTER, "output", "gnd")
        assert "latex" in result
        assert "expression" in result


class TestPolesAndZeros:
    def test_rc_filter_has_one_pole(self, analyzer, tmp_path):
        result = analyzer.poles_and_zeros(
            RC_FILTER, "input", "output", plot_dir=tmp_path
        )
        assert len(result["poles"]) == 1
        assert len(result["zeros"]) == 0
```

**Step 2-5: Implement SymbolicAnalyzer, test, commit**

The `SymbolicAnalyzer` converts our `CircuitSchema` to an lcapy circuit description, then uses lcapy's symbolic analysis methods. Returns LaTeX strings + Python-evaluable SymPy expressions.

```bash
pytest tests/test_engines/test_symbolic.py -v
git add -A
git commit -m "feat: symbolic analysis engine (transfer function, impedance, poles/zeros)"
```

---

## Task 10: Rendering Engine -- Schematics (schemdraw)

**Files:**
- Create: `electronics_mcp/engines/rendering/__init__.py`
- Create: `electronics_mcp/engines/rendering/schematic.py`
- Create: `tests/test_engines/test_schematic.py`

**Step 1: Write failing tests**

```python
# tests/test_engines/test_schematic.py
import pytest
from pathlib import Path
from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.engines.rendering.schematic import SchematicRenderer


@pytest.fixture
def renderer():
    return SchematicRenderer()


RC_FILTER = CircuitSchema(
    name="RC Low-Pass",
    components=[
        ComponentBase(id="V1", type="voltage_source", subtype="ac",
                      parameters={"amplitude": "1V"}, nodes=["input", "gnd"]),
        ComponentBase(id="R1", type="resistor",
                      parameters={"resistance": "10k"}, nodes=["input", "output"]),
        ComponentBase(id="C1", type="capacitor",
                      parameters={"capacitance": "10n"}, nodes=["output", "gnd"]),
    ],
)


class TestSchematicRenderer:
    def test_renders_svg(self, renderer, tmp_path):
        output_path = renderer.render(RC_FILTER, tmp_path / "test.svg")
        assert output_path.exists()
        assert output_path.suffix == ".svg"
        content = output_path.read_text()
        assert "<svg" in content

    def test_includes_component_labels(self, renderer, tmp_path):
        output_path = renderer.render(RC_FILTER, tmp_path / "test.svg")
        content = output_path.read_text()
        assert "R1" in content
        assert "C1" in content
```

**Step 2-5: Implement, test, commit**

The `SchematicRenderer` maps component types to schemdraw elements via a lookup dict:
```python
COMPONENT_MAP = {
    "resistor": elm.Resistor,
    "capacitor": elm.Capacitor,
    "inductor": elm.Inductor,
    "voltage_source": elm.SourceV,
    "current_source": elm.SourceI,
    "diode": elm.Diode,
    "opamp": elm.Opamp,
    # ... etc
}
```

Auto-layout: arrange components following node connections, trying to produce a readable left-to-right or top-to-bottom flow.

```bash
pytest tests/test_engines/test_schematic.py -v
git add -A
git commit -m "feat: schematic rendering engine (schemdraw -> SVG)"
```

---

## Task 11: Rendering Engine -- Plots (matplotlib)

**Files:**
- Create: `electronics_mcp/engines/rendering/plots.py`
- Create: `tests/test_engines/test_plots.py`

Implement `draw_bode`, `draw_waveform`, `draw_phasor`, `draw_pole_zero` functions. Each takes simulation result data + output path, returns the file path.

```bash
pytest tests/test_engines/test_plots.py -v
git add -A
git commit -m "feat: plot rendering (Bode, waveform, phasor, pole-zero)"
```

---

## Task 12: Rendering Engine -- Reports (Markdown + PDF)

**Files:**
- Create: `electronics_mcp/engines/rendering/reports.py`
- Create: `electronics_mcp/engines/rendering/templates/report.md.j2`
- Create: `tests/test_engines/test_reports.py`

Jinja2 template produces Markdown with embedded image references. `generate_pdf` converts via weasyprint.

```bash
pytest tests/test_engines/test_reports.py -v
git add -A
git commit -m "feat: report generation (Markdown + PDF)"
```

---

## Task 13: Fabrication Engine

**Files:**
- Create: `electronics_mcp/engines/fabrication/__init__.py`
- Create: `electronics_mcp/engines/fabrication/spice_netlist.py`
- Create: `electronics_mcp/engines/fabrication/kicad_netlist.py`
- Create: `electronics_mcp/engines/fabrication/bom.py`
- Create: `electronics_mcp/engines/fabrication/components.py`
- Create: `tests/test_engines/test_fabrication.py`

Four sub-modules:
- `spice_netlist.py`: circuit JSON -> `.cir` file
- `kicad_netlist.py`: circuit JSON -> KiCad `.net` XML format
- `bom.py`: circuit -> CSV with component values, MPNs, suppliers
- `components.py`: query component_models DB to suggest real parts matching ideal values

```bash
pytest tests/test_engines/test_fabrication.py -v
git add -A
git commit -m "feat: fabrication engine (SPICE/KiCad netlists, BOM, component suggestions)"
```

---

## Task 14: Knowledge Engine

**Files:**
- Create: `electronics_mcp/engines/knowledge/__init__.py`
- Create: `electronics_mcp/engines/knowledge/manager.py`
- Create: `electronics_mcp/engines/knowledge/topology.py`
- Create: `electronics_mcp/engines/knowledge/design_guide.py`
- Create: `tests/test_engines/test_knowledge.py`

**Key methods in `KnowledgeManager`:**
- `search(query: str, category: str = None) -> list[dict]` -- FTS5 search
- `get_topic(topic: str) -> dict` -- retrieve full article
- `get_formulas(topic: str) -> list[dict]` -- formulas for a topic
- `learn_pattern(category, topic, title, content, formulas)` -- store new knowledge
- `component_info(type: str, model: str = None) -> dict` -- component details from DB

**`TopologyExplainer`:** retrieves topology knowledge + linked subcircuit + relevant formulas.

**`DesignGuide`:** step-by-step design procedure using knowledge + formulas + design rules.

```bash
pytest tests/test_engines/test_knowledge.py -v
git add -A
git commit -m "feat: knowledge engine (FTS search, topology explanation, design guides)"
```

---

## Task 15: MCP Server -- Setup & Circuit Tools

**Files:**
- Create: `electronics_mcp/mcp/__init__.py`
- Create: `electronics_mcp/mcp/server.py`
- Create: `electronics_mcp/mcp/tools_circuit.py`
- Create: `tests/test_mcp/__init__.py`
- Create: `tests/test_mcp/test_tools_circuit.py`

**Step 1: Set up the FastMCP server**

```python
# electronics_mcp/mcp/server.py
from fastmcp import FastMCP
from electronics_mcp.config import ProjectConfig
from electronics_mcp.core.database import Database

mcp = FastMCP(
    "ElectronicsMCP",
    description="Electronic engineering context and skills for LLM agents",
)

# Lazy initialization
_config: ProjectConfig | None = None
_db: Database | None = None


def get_config() -> ProjectConfig:
    global _config
    if _config is None:
        _config = ProjectConfig()
        _config.ensure_dirs()
    return _config


def get_db() -> Database:
    global _db
    if _db is None:
        config = get_config()
        _db = Database(config.db_path)
        _db.initialize()
    return _db


# Import tool modules to register them
from electronics_mcp.mcp import tools_circuit  # noqa
# ... other tool imports added as modules are created


def main():
    mcp.run()


if __name__ == "__main__":
    main()
```

**Step 2: Implement circuit tools**

```python
# electronics_mcp/mcp/tools_circuit.py
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.schema import CircuitSchema, CircuitModification
import json


@mcp.tool()
def define_circuit(schema_json: str) -> str:
    """Create a new circuit from a full JSON schema and store it in the database.

    Args:
        schema_json: Full circuit JSON schema (see Circuit Description Schema)

    Returns:
        Circuit ID, summary, and any validation warnings
    """
    schema = CircuitSchema.model_validate_json(schema_json)
    cm = CircuitManager(get_db())
    circuit_id = cm.create(schema)
    warnings = cm.validate(circuit_id)

    result = f"Circuit '{schema.name}' created with ID: {circuit_id}\n"
    result += f"Components: {len(schema.components)}, "
    result += f"Subcircuits: {len(schema.subcircuit_instances)}\n"
    if warnings:
        result += f"Warnings:\n" + "\n".join(f"  - {w}" for w in warnings)
    return result


@mcp.tool()
def modify_circuit(circuit_id: str, modification_json: str) -> str:
    """Apply incremental changes to a stored circuit.

    Args:
        circuit_id: ID of the circuit to modify
        modification_json: JSON with add/remove/update/rename_node/connect operations

    Returns:
        Updated summary and new version number
    """
    mod = CircuitModification.model_validate_json(modification_json)
    cm = CircuitManager(get_db())
    version = cm.modify(circuit_id, mod)
    schema = cm.get_schema(circuit_id)
    return f"Circuit updated to version {version}. Components: {len(schema.components)}"


@mcp.tool()
def get_circuit(circuit_id: str) -> str:
    """Return a circuit's current schema as JSON."""
    cm = CircuitManager(get_db())
    schema = cm.get_schema(circuit_id)
    return schema.model_dump_json(indent=2)


@mcp.tool()
def validate_circuit(circuit_id: str) -> str:
    """Check a circuit for errors (floating nodes, shorted sources, missing ground)."""
    cm = CircuitManager(get_db())
    warnings = cm.validate(circuit_id)
    if not warnings:
        return "Circuit validation passed -- no issues found."
    return "Validation issues:\n" + "\n".join(f"  - {w}" for w in warnings)


@mcp.tool()
def list_circuits() -> str:
    """List all circuits in the project."""
    cm = CircuitManager(get_db())
    circuits = cm.list_all()
    if not circuits:
        return "No circuits in this project. Use define_circuit to create one."
    lines = ["| ID | Name | Status | Components |", "|---|------|--------|------------|"]
    for c in circuits:
        lines.append(f"| {c['id'][:8]}... | {c['name']} | {c['status']} | {c['component_count']} |")
    return "\n".join(lines)


@mcp.tool()
def clone_circuit(circuit_id: str, new_name: str) -> str:
    """Copy a circuit for variant exploration."""
    cm = CircuitManager(get_db())
    new_id = cm.clone(circuit_id, new_name)
    return f"Cloned as '{new_name}' with ID: {new_id}"


@mcp.tool()
def delete_circuit(circuit_id: str) -> str:
    """Remove a circuit and its simulation results."""
    cm = CircuitManager(get_db())
    cm.delete(circuit_id)
    return f"Circuit {circuit_id} deleted."
```

**Step 3: Test with FastMCP test client**

```python
# tests/test_mcp/test_tools_circuit.py
import pytest
import json
from electronics_mcp.mcp.server import mcp, get_db, _config, _db
from electronics_mcp.core.database import Database
from electronics_mcp.config import ProjectConfig


@pytest.fixture(autouse=True)
def reset_server_state(tmp_project, monkeypatch):
    """Point the MCP server at a temp project."""
    import electronics_mcp.mcp.server as srv
    srv._config = tmp_project
    srv._db = Database(tmp_project.db_path)
    srv._db.initialize()
    yield
    srv._config = None
    srv._db = None


RC_FILTER_JSON = json.dumps({
    "name": "RC Low-Pass",
    "components": [
        {"id": "V1", "type": "voltage_source", "subtype": "ac",
         "parameters": {"amplitude": "1V"}, "nodes": ["input", "gnd"]},
        {"id": "R1", "type": "resistor",
         "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
        {"id": "C1", "type": "capacitor",
         "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
    ]
})


class TestCircuitTools:
    def test_define_and_list(self):
        result = define_circuit(RC_FILTER_JSON)
        assert "created" in result.lower()

        listing = list_circuits()
        assert "RC Low-Pass" in listing

    def test_modify_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        mod_json = json.dumps({
            "update": [{"id": "R1", "parameters": {"resistance": "22k"}}]
        })
        mod_result = modify_circuit(circuit_id, mod_json)
        assert "version 2" in mod_result

    def test_get_circuit(self):
        result = define_circuit(RC_FILTER_JSON)
        circuit_id = result.split("ID: ")[1].split("\n")[0].strip()

        schema_json = get_circuit(circuit_id)
        schema = json.loads(schema_json)
        assert schema["name"] == "RC Low-Pass"
```

Note: Import the tool functions directly for testing. In production they're called via MCP protocol.

```bash
pytest tests/test_mcp/test_tools_circuit.py -v
git add -A
git commit -m "feat: MCP server setup + circuit definition tools"
```

---

## Task 16: MCP Tools -- Simulation (Numerical + Symbolic)

**Files:**
- Create: `electronics_mcp/mcp/tools_simulation.py`
- Create: `electronics_mcp/mcp/tools_symbolic.py`
- Create: `tests/test_mcp/test_tools_simulation.py`

12 tools: dc_operating_point, dc_sweep, ac_analysis, transient_analysis, parametric_sweep, monte_carlo, transfer_function, impedance, node_voltage_expression, simplify_network, poles_and_zeros, step_response.

Each tool: parse args -> call engine -> save results to DB -> write plot files -> return formatted text with file paths.

```bash
pytest tests/test_mcp/test_tools_simulation.py -v
git add -A
git commit -m "feat: MCP simulation tools (numerical + symbolic)"
```

---

## Task 17: MCP Tools -- Rendering

**Files:**
- Create: `electronics_mcp/mcp/tools_rendering.py`
- Create: `tests/test_mcp/test_tools_rendering.py`

7 tools: draw_schematic, draw_bode, draw_waveform, draw_phasor, draw_pole_zero, generate_report, generate_pdf.

Each returns the output file path.

```bash
pytest tests/test_mcp/test_tools_rendering.py -v
git add -A
git commit -m "feat: MCP rendering tools (schematics, plots, reports)"
```

---

## Task 18: MCP Tools -- Fabrication

**Files:**
- Create: `electronics_mcp/mcp/tools_fabrication.py`
- Create: `tests/test_mcp/test_tools_fabrication.py`

5 tools: generate_spice_netlist, generate_kicad_netlist, generate_bom, suggest_components, breadboard_layout.

```bash
pytest tests/test_mcp/test_tools_fabrication.py -v
git add -A
git commit -m "feat: MCP fabrication tools (netlists, BOM, component suggestions)"
```

---

## Task 19: MCP Tools -- Knowledge

**Files:**
- Create: `electronics_mcp/mcp/tools_knowledge.py`
- Create: `tests/test_mcp/test_tools_knowledge.py`

9 tools: search_knowledge, get_topic, explain_topology, design_guide, component_info, list_formulas, what_if, check_design, learn_pattern.

```bash
pytest tests/test_mcp/test_tools_knowledge.py -v
git add -A
git commit -m "feat: MCP knowledge tools (search, topology, design guides, learn)"
```

---

## Task 20: MCP Tools -- Comparison & Database Management

**Files:**
- Create: `electronics_mcp/mcp/tools_comparison.py`
- Create: `electronics_mcp/mcp/tools_db.py`
- Create: `tests/test_mcp/test_tools_comparison.py`
- Create: `tests/test_mcp/test_tools_db.py`

8 tools: create_comparison, compare_simulations, compare_boms, rank_designs, init_project, import_spice_model, export_project, query_db.

```bash
pytest tests/test_mcp/test_tools_comparison.py tests/test_mcp/test_tools_db.py -v
git add -A
git commit -m "feat: MCP comparison and database management tools"
```

---

## Task 21: MCP Resources

**Files:**
- Create: `electronics_mcp/mcp/resources.py`
- Create: `tests/test_mcp/test_resources.py`

6 resource URI schemes backed by knowledge base queries:

```python
@mcp.resource("electronics://topologies/{name}")
def get_topology_resource(name: str) -> str:
    """Reference material for standard circuit topologies."""
    km = KnowledgeManager(get_db())
    return km.get_topic(name)

# ... similar for components, design-rules, formulas, safety, standards
```

```bash
pytest tests/test_mcp/test_resources.py -v
git add -A
git commit -m "feat: MCP resource URIs (topologies, components, design rules, etc.)"
```

---

## Task 22: Subcircuit Library Tools

**Files:**
- Create: `electronics_mcp/mcp/tools_subcircuit.py`
- Create: `tests/test_mcp/test_tools_subcircuit.py`

4 tools: list_subcircuits, get_subcircuit, create_subcircuit, import_subcircuit.

```bash
pytest tests/test_mcp/test_tools_subcircuit.py -v
git add -A
git commit -m "feat: MCP subcircuit library tools"
```

---

## Task 23: Ingestion -- Kuphaldt HTML Parser

**Files:**
- Create: `electronics_mcp/ingestion/__init__.py`
- Create: `electronics_mcp/ingestion/ingest_kuphaldt.py`
- Create: `tests/test_ingestion/__init__.py`
- Create: `tests/test_ingestion/test_kuphaldt.py`

Parser for "Lessons in Electric Circuits" HTML:
- Walk HTML heading structure to extract sections as knowledge articles
- Tag each with category (fundamentals, passive_circuits, ac_theory, semiconductor, etc.)
- Extract difficulty level from volume + section depth
- Pull out formulas (identify by LaTeX patterns or equation markup)
- Cross-reference topics with component types
- Populate `knowledge` table + `knowledge_fts` triggers handle FTS indexing

Target: ~185 articles + ~80 formulas from 6 volumes.

Download source before running:
```bash
mkdir -p seed/sources
# Download Kuphaldt HTML volumes to seed/sources/kuphaldt/
```

```bash
pytest tests/test_ingestion/test_kuphaldt.py -v
git add -A
git commit -m "feat: Kuphaldt HTML ingestion pipeline"
```

---

## Task 24: Ingestion -- SPICE Model Parser

**Files:**
- Create: `electronics_mcp/ingestion/ingest_spice_models.py`
- Create: `tests/test_ingestion/test_spice_models.py`

Parse `.lib` and `.model` files:
- Extract `.model` statements (name, type, parameters)
- Extract `.subckt` definitions
- Normalize parameter units
- Populate `component_models` table with structured parameters + raw SPICE text in `spice_model` column
- Handle Ngspice bundled models (Tier 1) as primary source

```bash
pytest tests/test_ingestion/test_spice_models.py -v
git add -A
git commit -m "feat: SPICE model ingestion pipeline"
```

---

## Task 25: Ingestion -- KiCad Symbol Parser

**Files:**
- Create: `electronics_mcp/ingestion/ingest_kicad_symbols.py`
- Create: `tests/test_ingestion/test_kicad_symbols.py`

Parse `.kicad_sym` files (S-expression format):
- Extract component names, descriptions
- Extract pin definitions (name, number, type, position)
- Extract default field values (reference designator, footprint, datasheet URL)
- Populate `component_models` (metadata) and `component_categories` (taxonomy)
- Cross-reference with SPICE models where part numbers match

```bash
pytest tests/test_ingestion/test_kicad_symbols.py -v
git add -A
git commit -m "feat: KiCad symbol ingestion pipeline"
```

---

## Task 26: Ingestion -- Subcircuit Builder

**Files:**
- Create: `electronics_mcp/ingestion/build_subcircuits.py`
- Create: `seed/subcircuits/` (JSON definition files)
- Create: `tests/test_ingestion/test_build_subcircuits.py`

Author ~50 standard circuit topology definitions as JSON:
- **Passive (10):** voltage_divider, RC/RL/RLC low/high-pass, RLC bandpass/band-stop, pi_filter, T_filter, L_network
- **Amplifiers (10):** common_emitter, common_collector, common_base, common_source, common_drain, inverting_opamp, non_inverting_opamp, differential_amplifier, instrumentation_amplifier, push_pull_output
- **Filters (5):** sallen_key_lowpass, sallen_key_highpass, multiple_feedback_bandpass, state_variable_filter, active_notch
- **Power (10):** linear_regulator, LDO, buck_converter, boost_converter, buck_boost, flyback, half_bridge, full_bridge, charge_pump, gate_driver
- **Protection (5):** tvs_clamp, reverse_polarity, current_limiter, voltage_level_shifter, i2c_pullup
- **Oscillators (5):** 555_astable, 555_monostable, colpitts, wien_bridge, crystal_oscillator
- **Digital Interface (5):** schmitt_trigger, rs_latch, comparator_hysteresis, led_driver, relay_driver

Each has: schema_json, ports, parameters (with defaults), design_notes, category.

The builder validates each against `CircuitSchema`, inserts into `subcircuits` table.

```bash
pytest tests/test_ingestion/test_build_subcircuits.py -v
git add -A
git commit -m "feat: subcircuit builder with 50 standard topologies"
```

---

## Task 27: Ingestion -- Design Rules & Formulas

**Files:**
- Create: `electronics_mcp/ingestion/build_design_rules.py`
- Create: `electronics_mcp/ingestion/build_formulas.py`
- Create: `seed/design_rules/` (Markdown files)
- Create: `seed/formulas/` (JSON definition files)
- Create: `tests/test_ingestion/test_build_rules_formulas.py`

**Design rules (~30):** Authored Markdown entries covering:
- Decoupling (100nF per IC, bulk caps on power rails)
- Grounding (star ground, ground planes, return paths)
- Thermal management (power dissipation, heatsink sizing, thermal resistance)
- Voltage derating (capacitors: 50%, semiconductors: 80%)
- Trace width vs current (IPC-2221 tables)
- Component placement (bypass caps close to IC, input/output separation)
- EMI considerations (loop area, filtering, shielding)
- Power supply sequencing
- Signal integrity basics (impedance matching, termination)
- Safety (mains isolation, creepage/clearance, fuse selection)

**Formulas (~80):** Each has name, LaTeX expression, Python-evaluable expression, topic, description.
Categories: Ohm's law family, impedance, resonance, filter cutoffs, gain equations, power, thermal, timing, signal processing.

```bash
pytest tests/test_ingestion/test_build_rules_formulas.py -v
git add -A
git commit -m "feat: design rules and formula builders"
```

---

## Task 28: Ingestion -- QA Pipeline & Seed SQL Generation

**Files:**
- Create: `electronics_mcp/ingestion/qa.py`
- Create: `electronics_mcp/ingestion/generate_seed.py`
- Create: `tests/test_ingestion/test_qa.py`

**QA checks (`qa.py`):**
1. Knowledge articles: has title, content > 100 words, at least one related topic, difficulty tag
2. SPICE models: DC operating point runs without error (convergence check)
3. Component data: has type, description, and either SPICE model or parametric data
4. Subcircuits: full expansion -> simulation -> rendering pipeline succeeds
5. Formulas: LaTeX renders, Python expression evaluates for sample inputs

**Seed generation (`generate_seed.py`):**
- Run all ingestion scripts against a staging database
- Run QA pipeline, report failures
- Export passing records as `seed/seed_data.sql`
- Include provenance records for all entries

```bash
pytest tests/test_ingestion/test_qa.py -v
git add -A
git commit -m "feat: QA pipeline and seed SQL generation"
```

---

## Task 29: Web UI -- Dazzle Setup & Entity Views

**Files:**
- Create: `electronics_mcp/web/dazzle.toml`
- Create: `electronics_mcp/web/dsl/app.dsl`
- Create: `tests/test_web/__init__.py`
- Create: `tests/test_web/test_dazzle_views.py`

Set up the Dazzle project with entity definitions for Circuit, ComponentModel, Knowledge, Subcircuit. Define list and detail surfaces for each.

The Dazzle app connects to the same `data/ee.db` database.

```bash
pytest tests/test_web/test_dazzle_views.py -v
git add -A
git commit -m "feat: Dazzle web UI setup with entity views"
```

---

## Task 30: Web UI -- Parameter Explorer (Custom Stub)

**Files:**
- Create: `electronics_mcp/web/stubs/parameter_explorer.py`
- Create: `electronics_mcp/web/templates/parameter_explorer.html`
- Create: `tests/test_web/test_parameter_explorer.py`

FastAPI route at `/explorer/{circuit_id}`:
- Load circuit from DB, render component parameter sliders
- HTMX endpoints for debounced re-simulation on slider change
- Returns updated plot images (Bode, transient, schematic)
- Key metrics panel (bandwidth, gain, rise time, etc.)

```bash
pytest tests/test_web/test_parameter_explorer.py -v
git add -A
git commit -m "feat: parameter explorer web UI with real-time simulation"
```

---

## Task 31: Web UI -- Waveform Viewer & Circuit Comparison

**Files:**
- Create: `electronics_mcp/web/stubs/waveform_viewer.py`
- Create: `electronics_mcp/web/stubs/circuit_comparison.py`
- Create: `electronics_mcp/web/templates/waveform_viewer.html`
- Create: `electronics_mcp/web/templates/circuit_comparison.html`
- Create: `tests/test_web/test_waveform_viewer.py`
- Create: `tests/test_web/test_circuit_comparison.py`

**Waveform viewer:** Plotly.js (CDN) for interactive time/frequency plots with zoom/pan/cursors.

**Circuit comparison:** Side-by-side display, synchronized controls, overlaid plots, metric table.

```bash
pytest tests/test_web/ -v
git add -A
git commit -m "feat: waveform viewer and circuit comparison web UI"
```

---

## Task 32: Integration Tests & End-to-End Workflow

**Files:**
- Create: `tests/test_integration/test_full_workflow.py`
- Create: `tests/test_integration/test_mcp_server.py`

**Full workflow test:** Define a circuit -> simulate -> render -> generate report -> export netlist -> generate BOM. Verifies the entire pipeline works end-to-end.

**MCP server test:** Start the FastMCP server, call tools via the MCP protocol, verify responses.

```bash
pytest tests/test_integration/ -v
git add -A
git commit -m "feat: integration tests for full design workflow"
```

---

## Task 33: Final Assembly & Documentation

**Files:**
- Modify: `electronics_mcp/mcp/server.py` (ensure all tool imports)
- Modify: `CLAUDE.md` (project-specific instructions)
- Modify: `.mcp.json` (final configuration)
- Create: `electronics_mcp/web/run.py` (web UI entry point)

**Step 1: Verify all tool imports in server.py**

Ensure all tool modules are imported so FastMCP registers them.

**Step 2: Run full test suite**

```bash
pytest --cov=electronics_mcp -v
```

**Step 3: Test MCP server manually**

```bash
python -m electronics_mcp.mcp.server
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: final assembly -- all 47 MCP tools, 6 resource URIs, web UI"
```

---

## Task Summary

| # | Task | Key Output | Dependencies |
|---|------|-----------|--------------|
| 1 | Project scaffolding | pyproject.toml, config, git init | None |
| 2 | Database schema | SQLite with FTS5, all tables | 1 |
| 3 | Unit parser | EE value parsing/formatting | 1 |
| 4 | Circuit schema | Pydantic models | 1 |
| 5 | Circuit manager | CRUD + versioning | 2, 3, 4 |
| 6 | Netlist generation | Subcircuit expansion, SPICE netlist | 5 |
| 7 | Numerical simulation | DC op, AC, transient via PySpice | 4, 6 |
| 8 | Advanced simulation | Sweep, parametric, Monte Carlo | 7 |
| 9 | Symbolic analysis | Transfer function, impedance via lcapy | 4 |
| 10 | Schematic rendering | schemdraw -> SVG | 4 |
| 11 | Plot rendering | Bode, waveform, phasor, pole-zero | 7, 9 |
| 12 | Report generation | Markdown + PDF | 10, 11 |
| 13 | Fabrication engine | SPICE/KiCad netlists, BOM | 5, 6 |
| 14 | Knowledge engine | FTS search, topology, design guide | 2 |
| 15 | MCP server + circuit tools | FastMCP with 7 circuit tools | 5 |
| 16 | MCP simulation tools | 12 simulation tools | 7, 8, 9, 15 |
| 17 | MCP rendering tools | 7 rendering tools | 10, 11, 12, 15 |
| 18 | MCP fabrication tools | 5 fabrication tools | 13, 15 |
| 19 | MCP knowledge tools | 9 knowledge tools | 14, 15 |
| 20 | MCP comparison + DB tools | 8 tools | 15 |
| 21 | MCP resources | 6 URI schemes | 14, 15 |
| 22 | Subcircuit library tools | 4 tools | 5, 15 |
| 23 | Kuphaldt ingestion | ~185 articles + ~80 formulas | 2 |
| 24 | SPICE model ingestion | ~50-70 component models | 2 |
| 25 | KiCad symbol ingestion | Component metadata + categories | 2, 24 |
| 26 | Subcircuit builder | ~50 standard topologies | 4, 5 |
| 27 | Design rules + formulas | ~30 rules + ~80 formulas | 2 |
| 28 | QA + seed SQL generation | Validated seed_data.sql | 23-27 |
| 29 | Dazzle web UI setup | Entity views for browse/search | 2 |
| 30 | Parameter explorer | Interactive simulation UI | 7, 29 |
| 31 | Waveform viewer + comparison | Interactive plots + comparison | 11, 29 |
| 32 | Integration tests | End-to-end workflow validation | All |
| 33 | Final assembly | Complete MCP server | All |

## Parallelization Opportunities

Tasks that can run in parallel (no dependencies on each other):
- **Group A (core engines):** Tasks 7+8, 9, 10, 11 can run in parallel after Task 6
- **Group B (ingestion):** Tasks 23, 24, 25, 26, 27 can all run in parallel after Task 2
- **Group C (MCP tools):** Tasks 16-22 can run in parallel after Task 15 + their respective engines
- **Group D (web UI):** Tasks 29-31 can run in parallel with MCP tools after their engines are done
