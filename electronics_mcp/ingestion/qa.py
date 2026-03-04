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
            issues.append({
                "table": "knowledge", "id": row["id"],
                "topic": row["topic"], "issues": entry_issues,
            })
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
            issues.append({
                "table": "component_models", "id": row["id"],
                "part_number": row["part_number"], "issues": entry_issues,
            })
    return issues


def check_subcircuits(db: Database) -> list[dict]:
    """Validate subcircuits: schema parseable, has ports, has description."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, schema_json, ports "
            "FROM subcircuits"
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
            issues.append({
                "table": "subcircuits", "id": row["id"],
                "name": row["name"], "issues": entry_issues,
            })
    return issues


def check_formulas(db: Database) -> list[dict]:
    """Validate formula entries: expressions evaluate for sample inputs."""
    issues = []
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, topic, formulas FROM knowledge "
            "WHERE source = 'formula_builder'"
        ).fetchall()

    # Safe evaluation namespace with math functions and sample EE values
    sample_vars = {
        "V": 5.0, "I": 0.01, "R": 100.0, "P": 0.5,
        "f": 1000.0, "C": 1e-6, "L": 1e-3,
        "Rf": 10000.0, "Rin": 1000.0, "Rg": 1000.0,
        "Rc": 1000.0, "Re": 100.0,
        "Vin": 5.0, "R1": 1000.0, "R2": 1000.0,
        "Ta": 25.0, "Tj_max": 150.0, "Rth_ja": 50.0,
        "Vf": 5.0, "t": 0.001,
        "pi": math.pi, "sqrt": math.sqrt, "exp": math.exp,
        "Xl": 6.28, "Xc": 159.0,
        "f0": 1000.0, "Q": 10.0,
    }

    for row in rows:
        try:
            formulas = json.loads(row["formulas"]) if row["formulas"] else []
        except json.JSONDecodeError:
            issues.append({
                "table": "knowledge", "id": row["id"],
                "topic": row["topic"], "issues": ["invalid formulas JSON"],
            })
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
            issues.append({
                "table": "knowledge", "id": row["id"],
                "topic": row["topic"], "issues": entry_issues,
            })
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
