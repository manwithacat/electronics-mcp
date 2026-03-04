"""Build design rules knowledge entries from structured definitions."""
import json
import uuid

from electronics_mcp.core.database import Database


DESIGN_RULES = [
    {"topic": "decoupling_capacitors", "title": "Decoupling Capacitor Placement",
     "content": "Place 100nF ceramic capacitors as close as possible to every IC power pin. "
                "Add bulk capacitors (10-100uF) on each power rail. Use low-ESR ceramics for "
                "high-frequency decoupling. Multiple smaller caps are better than one large cap.",
     "category": "design_rule"},

    {"topic": "ground_planes", "title": "Ground Plane Design",
     "content": "Use unbroken ground planes on multilayer PCBs. Avoid splitting ground planes "
                "under high-speed signal traces. Connect analog and digital grounds at a single "
                "point (star ground) to prevent noise coupling.",
     "category": "design_rule"},

    {"topic": "voltage_derating", "title": "Component Voltage Derating",
     "content": "Derate capacitors to 50% of rated voltage for reliability. Derate semiconductors "
                "to 80% of absolute maximum ratings. Resistors should not exceed 75% of rated power "
                "in continuous operation.",
     "category": "design_rule"},

    {"topic": "thermal_management", "title": "Thermal Management Guidelines",
     "content": "Calculate power dissipation for all active components. Use thermal resistance "
                "values (Rth_ja, Rth_jc) to estimate junction temperature. Add heatsinks when "
                "Tj exceeds 80% of Tj_max. Ensure adequate airflow for convection cooling.",
     "category": "design_rule"},

    {"topic": "trace_width_current", "title": "PCB Trace Width vs Current",
     "content": "Use IPC-2221 standard for trace width calculations. For 1oz copper external "
                "layers: 10mil for 0.5A, 20mil for 1A, 50mil for 2A, 100mil for 4A. "
                "Internal layers require wider traces due to reduced cooling.",
     "category": "design_rule"},

    {"topic": "bypass_cap_placement", "title": "Bypass Capacitor Strategy",
     "content": "Place bypass caps on the same layer as the IC when possible. Route power through "
                "the capacitor to the IC pin, not the other way around. Use 100nF + 10nF in parallel "
                "for wide frequency coverage.",
     "category": "design_rule"},

    {"topic": "emi_reduction", "title": "EMI Reduction Techniques",
     "content": "Minimize loop areas in high-current paths. Use ground planes to reduce radiation. "
                "Add ferrite beads on power lines entering/exiting the board. Shield sensitive analog "
                "circuits from digital noise sources.",
     "category": "design_rule"},

    {"topic": "input_protection", "title": "Input Protection",
     "content": "Add TVS diodes on external-facing signal lines. Use series resistors to limit "
                "current into ESD protection structures. Clamp voltages to supply rails with "
                "Schottky diodes for overvoltage protection.",
     "category": "design_rule"},

    {"topic": "power_supply_sequencing", "title": "Power Supply Sequencing",
     "content": "Ensure core voltage is applied before I/O voltage for FPGAs and processors. "
                "Use sequencing ICs or RC delays for controlled power-up order. Add supervisor "
                "ICs for brownout detection and controlled reset.",
     "category": "design_rule"},

    {"topic": "signal_integrity", "title": "Signal Integrity Basics",
     "content": "Match trace impedance to source/load impedance for high-speed signals. "
                "Use series termination (source) or parallel termination (load) to prevent "
                "reflections. Keep high-speed traces short and avoid vias.",
     "category": "design_rule"},
]


def build_design_rules(db: Database, rules: list[dict] | None = None) -> dict:
    """Insert design rules into the knowledge database.

    Returns stats dict.
    """
    if rules is None:
        rules = DESIGN_RULES

    stats = {"created": 0, "skipped": 0}

    for rule in rules:
        entry_id = str(uuid.uuid4())
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM knowledge WHERE topic = ?",
                (rule["topic"],),
            ).fetchone()
            if existing:
                stats["skipped"] += 1
                continue

            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'design_rules')",
                (entry_id, rule["category"], rule["topic"], rule["title"],
                 rule["content"], json.dumps([]), json.dumps([]),
                 "intermediate"),
            )
            stats["created"] += 1

    return stats
