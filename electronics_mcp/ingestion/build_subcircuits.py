"""Build standard subcircuit library from JSON definitions."""
import json
import uuid
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import CircuitSchema


# Standard subcircuit definitions
STANDARD_SUBCIRCUITS = [
    # Passive circuits
    {"name": "voltage_divider", "category": "passive",
     "description": "Resistive voltage divider",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R1": "10k", "R2": "10k"},
     "schema": {"name": "voltage_divider", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vout = Vin * R2/(R1+R2). Output impedance = R1||R2."},

    {"name": "rc_lowpass", "category": "passive",
     "description": "First-order RC low-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "rc_lowpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = 1/(2*pi*R*C). -20dB/decade rolloff."},

    {"name": "rc_highpass", "category": "passive",
     "description": "First-order RC high-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "rc_highpass", "components": [
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["input", "output"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = 1/(2*pi*R*C). Blocks DC, passes AC."},

    {"name": "rl_lowpass", "category": "passive",
     "description": "First-order RL low-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "10m"},
     "schema": {"name": "rl_lowpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "output"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10m"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = R/(2*pi*L)."},

    {"name": "rlc_bandpass", "category": "passive",
     "description": "Series RLC bandpass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "1m", "C": "100n"},
     "schema": {"name": "rlc_bandpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "mid"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "1m"}, "nodes": ["mid", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "f0 = 1/(2*pi*sqrt(L*C)). Q = (1/R)*sqrt(L/C)."},

    # Amplifiers
    {"name": "inverting_opamp", "category": "amplifier",
     "description": "Inverting operational amplifier",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"Rf": "100k", "Rin": "10k"},
     "schema": {"name": "inverting_opamp", "components": [
         {"id": "R_in", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "inv_in"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["inv_in", "output"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "gnd", "output"]},
     ]},
     "design_notes": "Gain = -Rf/Rin. Input impedance = Rin."},

    {"name": "non_inverting_opamp", "category": "amplifier",
     "description": "Non-inverting operational amplifier",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"Rf": "90k", "Rg": "10k"},
     "schema": {"name": "non_inverting_opamp", "components": [
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "gnd"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "90k"}, "nodes": ["inv_in", "output"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "input", "output"]},
     ]},
     "design_notes": "Gain = 1 + Rf/Rg. Very high input impedance."},

    {"name": "common_emitter", "category": "amplifier",
     "description": "Common emitter BJT amplifier",
     "ports": ["input", "output", "vcc", "gnd"],
     "parameters": {"Rc": "4.7k", "Rb": "100k", "Re": "1k"},
     "schema": {"name": "common_emitter", "components": [
         {"id": "R_b", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["input", "base"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base", "output", "emitter"]},
         {"id": "R_c", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "output"]},
         {"id": "R_e", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["emitter", "gnd"]},
     ]},
     "design_notes": "Av ≈ -Rc/Re (with emitter degeneration)."},

    # Power
    {"name": "led_driver", "category": "digital_interface",
     "description": "LED driver with current limiting resistor",
     "ports": ["input", "gnd"],
     "parameters": {"R": "330", "Vf": "2V"},
     "schema": {"name": "led_driver", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "330"}, "nodes": ["input", "anode"]},
         {"id": "D1", "type": "led", "parameters": {"forward_voltage": "2V"}, "nodes": ["anode", "gnd"]},
     ]},
     "design_notes": "R = (Vcc - Vf) / If. Typical If = 10-20mA."},

    {"name": "relay_driver", "category": "digital_interface",
     "description": "Relay driver with flyback diode",
     "ports": ["input", "vcc", "gnd"],
     "parameters": {"R_base": "1k"},
     "schema": {"name": "relay_driver", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["input", "base"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base", "coil_low", "gnd"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["coil_low", "vcc"]},
     ]},
     "design_notes": "Flyback diode D1 protects transistor from back-EMF."},
]


def build_subcircuits(db: Database, definitions: list[dict] | None = None) -> dict:
    """Build subcircuit library from definitions.

    Args:
        db: Database to populate
        definitions: List of subcircuit definitions. Uses STANDARD_SUBCIRCUITS if None.

    Returns:
        Stats dict with counts.
    """
    if definitions is None:
        definitions = STANDARD_SUBCIRCUITS

    stats = {"created": 0, "skipped": 0, "errors": 0}

    for defn in definitions:
        try:
            # Validate schema
            CircuitSchema.model_validate(defn["schema"])

            sc_id = str(uuid.uuid4())
            with db.connect() as conn:
                existing = conn.execute(
                    "SELECT id FROM subcircuits WHERE name = ?",
                    (defn["name"],),
                ).fetchone()
                if existing:
                    stats["skipped"] += 1
                    continue

                conn.execute(
                    "INSERT INTO subcircuits (id, name, category, description, "
                    "schema_json, ports, parameters, design_notes, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'builder')",
                    (sc_id, defn["name"], defn.get("category", ""),
                     defn.get("description", ""),
                     json.dumps(defn["schema"]),
                     json.dumps(defn["ports"]),
                     json.dumps(defn.get("parameters", {})),
                     defn.get("design_notes", "")),
                )
                stats["created"] += 1

        except Exception as e:
            stats["errors"] += 1

    return stats


def build_from_directory(source_dir: Path | str, db: Database) -> dict:
    """Build subcircuits from JSON files in a directory."""
    source_dir = Path(source_dir)
    definitions = []
    for f in sorted(source_dir.glob("*.json")):
        defn = json.loads(f.read_text())
        if isinstance(defn, list):
            definitions.extend(defn)
        else:
            definitions.append(defn)
    return build_subcircuits(db, definitions)
