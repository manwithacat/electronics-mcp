"""Ingest SPICE .model and .subckt definitions into the component database."""
import re
import json
import uuid
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import record_provenance


# Common SPICE model types
MODEL_TYPES = {
    "D": "diode",
    "NPN": "bjt",
    "PNP": "bjt",
    "NJF": "jfet",
    "PJF": "jfet",
    "NMOS": "mosfet",
    "PMOS": "mosfet",
    "R": "resistor",
    "C": "capacitor",
    "L": "inductor",
}


def parse_model_statement(text: str) -> dict | None:
    """Parse a .model statement into structured data.

    Format: .model <name> <type> (<params>)
    """
    # Match .model name type (params)
    pattern = re.compile(
        r'\.model\s+(\S+)\s+(\S+)\s*\(([^)]*)\)',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        # Try without parentheses
        pattern2 = re.compile(
            r'\.model\s+(\S+)\s+(\S+)\s+(.*?)(?:\n\.|\Z)',
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern2.search(text)
        if not match:
            return None

    name = match.group(1)
    model_type = match.group(2).upper()
    params_text = match.group(3)

    # Parse parameters
    params = _parse_params(params_text)

    component_type = MODEL_TYPES.get(model_type, "other")

    return {
        "name": name,
        "model_type": model_type,
        "component_type": component_type,
        "parameters": params,
        "raw_text": text.strip(),
    }


def parse_subckt_statement(text: str) -> dict | None:
    """Parse a .subckt definition.

    Format: .subckt <name> <nodes...>
    ...
    .ends
    """
    pattern = re.compile(
        r'\.subckt\s+(\S+)\s+(.*?)\n(.*?)\.ends',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return None

    name = match.group(1)
    nodes = match.group(2).strip().split()
    body = match.group(3).strip()

    return {
        "name": name,
        "nodes": nodes,
        "body": body,
        "raw_text": text.strip(),
    }


def _parse_params(text: str) -> dict:
    """Parse SPICE parameter string into dict."""
    params = {}
    # Match key=value pairs
    for match in re.finditer(r'(\w+)\s*=\s*([^\s,)+]+)', text):
        key = match.group(1)
        value = match.group(2)
        try:
            params[key] = float(value)
        except ValueError:
            params[key] = value
    return params


def ingest_spice_file(file_path: Path | str, db: Database) -> dict:
    """Ingest SPICE models from a .lib or .model file.

    Returns dict with counts of models and subcircuits ingested.
    """
    file_path = Path(file_path)
    content = file_path.read_text(errors="replace")
    stats = {"models": 0, "subcircuits": 0, "errors": 0}

    # Extract .model statements
    model_pattern = re.compile(
        r'(\.model\s+\S+\s+\S+\s*(?:\([^)]*\)|[^\n]*(?:\n\+[^\n]*)*))',
        re.IGNORECASE,
    )
    for match in model_pattern.finditer(content):
        parsed = parse_model_statement(match.group(1))
        if not parsed:
            stats["errors"] += 1
            continue

        model_id = str(uuid.uuid4())
        created = False
        with db.connect() as conn:
            # Skip duplicates
            existing = conn.execute(
                "SELECT id FROM component_models WHERE part_number = ?",
                (parsed["name"],),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO component_models (id, type, part_number, description, "
                "parameters, spice_model, source) VALUES (?, ?, ?, ?, ?, ?, 'spice_import')",
                (model_id, parsed["component_type"], parsed["name"],
                 f"SPICE {parsed['model_type']} model",
                 json.dumps(parsed["parameters"]),
                 parsed["raw_text"]),
            )
            created = True

        if created:
            record_provenance(
                db, "component_models", model_id, "spice_import",
                licence="varies",
                original_path=str(file_path),
                notes=f"SPICE {parsed['model_type']} model: {parsed['name']}",
            )
            stats["models"] += 1

    # Extract .subckt definitions
    subckt_pattern = re.compile(
        r'(\.subckt\s+.*?\.ends\s*\S*)',
        re.IGNORECASE | re.DOTALL,
    )
    for match in subckt_pattern.finditer(content):
        parsed = parse_subckt_statement(match.group(1))
        if not parsed:
            stats["errors"] += 1
            continue

        sc_id = str(uuid.uuid4())
        schema = {"name": parsed["name"], "components": []}
        created = False
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM subcircuits WHERE name = ?",
                (parsed["name"],),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO subcircuits (id, name, description, schema_json, "
                "ports, design_notes, source) VALUES (?, ?, ?, ?, ?, ?, 'spice_import')",
                (sc_id, parsed["name"], f"Imported from {file_path.name}",
                 json.dumps(schema), json.dumps(parsed["nodes"]),
                 parsed["raw_text"]),
            )
            created = True

        if created:
            record_provenance(
                db, "subcircuits", sc_id, "spice_import",
                licence="varies",
                original_path=str(file_path),
                notes=f"SPICE subcircuit: {parsed['name']}",
            )
            stats["subcircuits"] += 1

    return stats


def ingest_spice_directory(source_dir: Path | str, db: Database) -> dict:
    """Ingest all SPICE model files from a directory.

    Returns aggregate stats.
    """
    source_dir = Path(source_dir)
    total = {"models": 0, "subcircuits": 0, "errors": 0, "files": 0}

    for f in sorted(source_dir.glob("**/*")):
        if f.suffix.lower() in (".lib", ".mod", ".model", ".spice"):
            stats = ingest_spice_file(f, db)
            total["models"] += stats["models"]
            total["subcircuits"] += stats["subcircuits"]
            total["errors"] += stats["errors"]
            total["files"] += 1

    return total
