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
