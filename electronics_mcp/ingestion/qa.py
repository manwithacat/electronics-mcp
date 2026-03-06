"""Quality-assurance checks for ingested data."""

import json
import math
from electronics_mcp.core.database import Database


def check_knowledge(db: Database) -> list[dict]:
    """Validate knowledge entries: title, content length, difficulty tag."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, topic, title, content, difficulty, related_topics "
            "FROM knowledge"
        ).fetchall()

    for row in rows:
        entry_issues: list[str] = []
        if not row["title"] or len(row["title"].strip()) == 0:
            entry_issues.append("missing title")
        if not row["content"] or len(row["content"].split()) < 5:
            entry_issues.append("content too short (< 5 words)")
        if not row["difficulty"]:
            entry_issues.append("missing difficulty tag")
        if entry_issues:
            issues.append(
                {
                    "table": "knowledge",
                    "id": row["id"],
                    "topic": row["topic"],
                    "issues": entry_issues,
                }
            )
    return issues


def check_components(db: Database) -> list[dict]:
    """Validate component_models: type, description, parameters."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, type, part_number, description, parameters, spice_model "
            "FROM component_models"
        ).fetchall()

    for row in rows:
        entry_issues: list[str] = []
        if not row["type"]:
            entry_issues.append("missing type")
        if not row["description"]:
            entry_issues.append("missing description")
        params = row["parameters"]
        has_params = params and params != "{}" and params != "null"
        has_spice = row["spice_model"] and row["spice_model"].strip()
        if not has_params and not has_spice:
            entry_issues.append("no parameters or SPICE model")
        if entry_issues:
            issues.append(
                {
                    "table": "component_models",
                    "id": row["id"],
                    "part_number": row["part_number"],
                    "issues": entry_issues,
                }
            )
    return issues


def check_subcircuits(db: Database) -> list[dict]:
    """Validate subcircuits: schema parseable, has ports, has description."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, schema_json, ports FROM subcircuits"
        ).fetchall()

    for row in rows:
        entry_issues: list[str] = []
        if not row["description"]:
            entry_issues.append("missing description")
        try:
            schema = json.loads(row["schema_json"])
            if not schema.get("components"):
                entry_issues.append("schema has no components")
        except (json.JSONDecodeError, TypeError):
            entry_issues.append("invalid schema_json")
        try:
            ports = json.loads(row["ports"])
            if not ports:
                entry_issues.append("no ports defined")
        except (json.JSONDecodeError, TypeError):
            entry_issues.append("invalid ports JSON")
        if entry_issues:
            issues.append(
                {
                    "table": "subcircuits",
                    "id": row["id"],
                    "name": row["name"],
                    "issues": entry_issues,
                }
            )
    return issues


def check_formulas(db: Database) -> list[dict]:
    """Validate formula entries: expressions evaluate for sample inputs."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, topic, formulas FROM knowledge WHERE source = 'formula_builder'"
        ).fetchall()

    # Safe evaluation namespace with math functions and sample EE values
    sample_vars = {
        "V": 5.0,
        "I": 0.01,
        "R": 100.0,
        "P": 0.5,
        "f": 1000.0,
        "C": 1e-6,
        "L": 1e-3,
        "Rf": 10000.0,
        "Rin": 1000.0,
        "Rg": 1000.0,
        "Rc": 1000.0,
        "Re": 100.0,
        "Rb": 100000.0,
        "Vin": 5.0,
        "Vout": 3.3,
        "R1": 1000.0,
        "R2": 1000.0,
        "R3": 1000.0,
        "Ta": 25.0,
        "Tj_max": 150.0,
        "Rth_ja": 50.0,
        "Vf": 5.0,
        "t": 0.001,
        "pi": math.pi,
        "sqrt": math.sqrt,
        "exp": math.exp,
        "log10": math.log10,
        "log": math.log,
        "Xl": 6.28,
        "Xc": 159.0,
        "f0": 1000.0,
        "Q": 10.0,
        # Semiconductor variables
        "Is": 1e-12,
        "n": 1.0,
        "Vt": 0.026,
        "k": 1.38e-23,
        "T": 300.0,
        "q": 1.6e-19,
        "Id": 0.001,
        "Ic": 0.01,
        "hFE": 100.0,
        "Ib": 1e-5,
        "Vcc": 12.0,
        "Vce": 6.0,
        "Kp": 0.01,
        "Vgs": 5.0,
        "Vth": 2.0,
        "Vds": 5.0,
        "Rds_on": 0.05,
        # Opamp/amplifier variables
        "Av": 10.0,
        "BW": 1e5,
        "GBW": 1e6,
        "SR": 1e6,
        "en": 10e-9,
        "in_noise": 1e-12,
        # Power converter variables
        "D": 0.5,
        "Cout": 100e-6,
        "dI_L": 0.1,
        "Iout": 1.0,
        "Pout": 5.0,
        "P_cond": 0.1,
        "P_sw": 0.1,
        "tr": 20e-9,
        "tf": 20e-9,
        "Idc": 1.0,
        "I_peak": 1.1,
        "I_ripple": 0.05,
        "ESR": 0.01,
        # PCB variables
        "Er": 4.5,
        "h": 0.2,
        "w": 0.2,
        "b": 0.4,
        # Skin effect
        "mu": 1.26e-6,
        "sigma": 5.8e7,
        "delta_skin": 0.001,
        "Rdc": 0.01,
        # Digital timing
        "tpd": 5e-9,
        "tsu": 2e-9,
        "Tclk": 10e-9,
        # ADC/DAC
        "N": 12.0,
        "Vref": 3.3,
        "SNR_meas": 72.0,
        # PLL
        "f_ref": 1e6,
        # Battery/motor
        "Capacity": 2.0,
        "V_nom": 3.7,
        "torque": 0.1,
        "omega": 100.0,
        "P_mech": 10.0,
        "P_elec": 12.0,
        "rpm": 1000.0,
        # Decibel
        "V1": 1.0,
        "V2": 10.0,
        "P1": 0.001,
        "P2": 0.01,
        # Wheatstone/transformer
        "Rx": 1000.0,
        "Np": 100.0,
        "Ns": 10.0,
        "Vp": 120.0,
        "Zl": 50.0,
    }

    for row in rows:
        try:
            formulas = json.loads(row["formulas"]) if row["formulas"] else []
        except json.JSONDecodeError:
            issues.append(
                {
                    "table": "knowledge",
                    "id": row["id"],
                    "topic": row["topic"],
                    "issues": ["invalid formulas JSON"],
                }
            )
            continue

        entry_issues: list[str] = []
        for f in formulas:
            expr = f.get("expression", "")
            try:
                # Restricted eval: no builtins, only sample EE variables
                eval(expr, {"__builtins__": {}}, sample_vars)  # noqa: S307
            except Exception as e:
                entry_issues.append(f"formula '{f.get('name', '?')}' eval error: {e}")

        if entry_issues:
            issues.append(
                {
                    "table": "knowledge",
                    "id": row["id"],
                    "topic": row["topic"],
                    "issues": entry_issues,
                }
            )
    return issues


def run_qa(db: Database) -> dict:
    """Run all QA checks and return summary."""
    results = {
        "knowledge": check_knowledge(db),
        "components": check_components(db),
        "subcircuits": check_subcircuits(db),
        "formulas": check_formulas(db),
    }
    total_issues = sum(len(v) for v in results.values())
    return {"checks": results, "total_issues": total_issues}
