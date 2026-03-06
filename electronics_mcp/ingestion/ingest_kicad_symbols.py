"""Ingest KiCad symbol library (.kicad_sym) files into the component database."""
import re
import json
import uuid
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import record_provenance


def parse_sexpr(text: str) -> list:
    """Parse S-expression format used by KiCad into nested lists."""
    tokens = _tokenize(text)
    return _parse_tokens(tokens)


def _tokenize(text: str) -> list[str]:
    """Tokenize S-expression text."""
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in '(':
            tokens.append('(')
            i += 1
        elif c == ')':
            tokens.append(')')
            i += 1
        elif c == '"':
            # Quoted string
            j = i + 1
            while j < len(text) and text[j] != '"':
                if text[j] == '\\':
                    j += 1
                j += 1
            tokens.append(text[i+1:j])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            # Unquoted token
            j = i
            while j < len(text) and text[j] not in '() \t\n\r"':
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def _parse_tokens(tokens: list[str]) -> list:
    """Parse tokenized S-expression into nested lists."""
    result = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '(':
            # Find matching close
            depth = 1
            j = i + 1
            while j < len(tokens) and depth > 0:
                if tokens[j] == '(':
                    depth += 1
                elif tokens[j] == ')':
                    depth -= 1
                j += 1
            inner = _parse_tokens(tokens[i+1:j-1])
            result.append(inner)
            i = j
        elif tokens[i] == ')':
            i += 1
        else:
            result.append(tokens[i])
            i += 1
    return result


def extract_symbols(parsed: list) -> list[dict]:
    """Extract component symbols from parsed KiCad S-expression."""
    symbols = []
    for item in parsed:
        if isinstance(item, list) and len(item) > 0 and item[0] == "symbol":
            symbol = _extract_symbol(item)
            if symbol:
                symbols.append(symbol)
    return symbols


def _extract_symbol(node: list) -> dict | None:
    """Extract a single symbol definition."""
    if len(node) < 2:
        return None

    name = node[1] if isinstance(node[1], str) else str(node[1])

    # Skip power symbols and sub-units
    if name.startswith("power:") or "_" in name and name.split("_")[-1].isdigit():
        return None

    symbol = {
        "name": name,
        "description": "",
        "reference": "",
        "footprint": "",
        "datasheet": "",
        "pins": [],
    }

    for item in node[2:]:
        if not isinstance(item, list) or len(item) < 2:
            continue

        if item[0] == "property":
            prop_name = item[1] if isinstance(item[1], str) else ""
            prop_value = item[2] if len(item) > 2 and isinstance(item[2], str) else ""

            if prop_name == "Reference":
                symbol["reference"] = prop_value
            elif prop_name == "Value":
                pass  # already have name
            elif prop_name == "Footprint":
                symbol["footprint"] = prop_value
            elif prop_name == "Datasheet":
                symbol["datasheet"] = prop_value
            elif prop_name == "Description":
                symbol["description"] = prop_value
            elif prop_name == "ki_description":
                if not symbol["description"]:
                    symbol["description"] = prop_value

        elif item[0] == "pin":
            pin = _extract_pin(item)
            if pin:
                symbol["pins"].append(pin)

        # Recurse into sub-symbols for pins
        elif item[0] == "symbol":
            for sub in item[2:]:
                if isinstance(sub, list) and len(sub) > 0 and sub[0] == "pin":
                    pin = _extract_pin(sub)
                    if pin:
                        symbol["pins"].append(pin)

    return symbol


def _extract_pin(node: list) -> dict | None:
    """Extract pin definition."""
    if len(node) < 3:
        return None

    pin = {"type": "", "name": "", "number": ""}

    # pin type is usually node[1]
    if isinstance(node[1], str):
        pin["type"] = node[1]

    for item in node[2:]:
        if isinstance(item, list) and len(item) >= 2:
            if item[0] == "name":
                pin["name"] = item[1] if isinstance(item[1], str) else ""
            elif item[0] == "number":
                pin["number"] = item[1] if isinstance(item[1], str) else ""

    return pin if pin["name"] or pin["number"] else None


def _ref_to_type(ref: str) -> str:
    """Map KiCad reference designator to component type."""
    ref_map = {
        "R": "resistor", "C": "capacitor", "L": "inductor",
        "D": "diode", "Q": "bjt", "U": "ic",
        "J": "connector", "K": "relay", "F": "fuse",
        "LED": "led", "SW": "switch",
    }
    for prefix, ctype in ref_map.items():
        if ref.startswith(prefix):
            return ctype
    return "other"


def ingest_kicad_symbols(file_path: Path | str, db: Database) -> dict:
    """Ingest KiCad symbol library into the database.

    Returns stats dict with counts.
    """
    file_path = Path(file_path)
    content = file_path.read_text(errors="replace")
    stats = {"symbols": 0, "skipped": 0}

    parsed = parse_sexpr(content)
    if not parsed:
        return stats
    # parse_sexpr returns a list of top-level nodes; the library is the first
    lib_node = parsed[0]
    symbols = extract_symbols(lib_node)

    for sym in symbols:
        component_type = _ref_to_type(sym.get("reference", ""))
        model_id = str(uuid.uuid4())

        params = {}
        if sym["pins"]:
            params["pin_count"] = len(sym["pins"])
            params["pins"] = [{"name": p["name"], "number": p["number"],
                               "type": p["type"]} for p in sym["pins"]]

        created = False
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM component_models WHERE part_number = ?",
                (sym["name"],),
            ).fetchone()
            if existing:
                stats["skipped"] += 1
                continue

            conn.execute(
                "INSERT INTO component_models (id, type, part_number, description, "
                "parameters, footprint, datasheet_url, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'kicad_import')",
                (model_id, component_type, sym["name"], sym["description"],
                 json.dumps(params), sym["footprint"], sym["datasheet"]),
            )
            created = True

        if created:
            record_provenance(
                db, "component_models", model_id, "kicad_import",
                source_url="https://gitlab.com/kicad/libraries/kicad-symbols",
                licence="CC-BY-SA-4.0",
                original_path=str(file_path),
                notes=f"KiCad symbol: {sym['name']}",
            )
            stats["symbols"] += 1

    return stats
