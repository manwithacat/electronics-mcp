"""MCP tools for circuit comparison and ranking."""

import json
import uuid
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.engines.fabrication.bom import generate_bom_summary


@mcp.tool()
def create_comparison(
    name: str, circuit_ids_json: str, criteria_json: str | None = None
) -> str:
    """Create a named comparison between multiple circuits.

    Args:
        name: Comparison name
        circuit_ids_json: JSON array of circuit IDs to compare
        criteria_json: Optional JSON object with comparison criteria
    """
    circuit_ids = json.loads(circuit_ids_json)
    criteria = json.loads(criteria_json) if criteria_json else {}
    comp_id = str(uuid.uuid4())

    db = get_db()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO comparisons (id, name, circuit_ids, comparison_axes, results) "
            "VALUES (?, ?, ?, ?, ?)",
            (comp_id, name, json.dumps(circuit_ids), json.dumps(criteria), "{}"),
        )
    return (
        f"Comparison '{name}' created with ID: {comp_id}\nCircuits: {len(circuit_ids)}"
    )


@mcp.tool()
def compare_simulations(circuit_ids_json: str, analysis_type: str = "ac") -> str:
    """Compare simulation results across multiple circuits.

    Args:
        circuit_ids_json: JSON array of circuit IDs
        analysis_type: Type of analysis to compare (ac, dc_op, transient)
    """
    circuit_ids = json.loads(circuit_ids_json)
    db = get_db()
    cm = CircuitManager(db)

    lines = [f"Simulation Comparison ({analysis_type}):", ""]
    for cid in circuit_ids:
        schema = cm.get_schema(cid)
        lines.append(f"## {schema.name} ({cid[:8]})")

        with db.connect() as conn:
            row = conn.execute(
                "SELECT results_json FROM simulation_results "
                "WHERE circuit_id = ? AND analysis_type = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (cid, analysis_type),
            ).fetchone()

        if row:
            results = json.loads(row["results_json"])
            for key, value in results.items():
                if isinstance(value, (int, float)):
                    lines.append(f"  {key}: {value}")
        else:
            lines.append("  No simulation results found.")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def compare_boms(circuit_ids_json: str) -> str:
    """Compare bill of materials across multiple circuits.

    Args:
        circuit_ids_json: JSON array of circuit IDs
    """
    circuit_ids = json.loads(circuit_ids_json)
    cm = CircuitManager(get_db())

    lines = ["BOM Comparison:", ""]
    lines.append("| Circuit | Components | Unique Types |")
    lines.append("|---------|-----------|-------------|")

    for cid in circuit_ids:
        schema = cm.get_schema(cid)
        summary = generate_bom_summary(schema)
        lines.append(
            f"| {schema.name} ({cid[:8]}) | "
            f"{summary['total_components']} | "
            f"{summary['unique_types']} |"
        )
    return "\n".join(lines)


@mcp.tool()
def rank_designs(circuit_ids_json: str, metric: str = "component_count") -> str:
    """Rank circuits by a specified metric.

    Args:
        circuit_ids_json: JSON array of circuit IDs
        metric: Ranking metric (component_count, bandwidth, cost)
    """
    circuit_ids = json.loads(circuit_ids_json)
    cm = CircuitManager(get_db())
    db = get_db()

    rankings = []
    for cid in circuit_ids:
        schema = cm.get_schema(cid)
        score = len(schema.components)

        if metric == "bandwidth":
            with db.connect() as conn:
                row = conn.execute(
                    "SELECT results_json FROM simulation_results "
                    "WHERE circuit_id = ? AND analysis_type = 'ac' "
                    "ORDER BY created_at DESC LIMIT 1",
                    (cid,),
                ).fetchone()
                if row:
                    results = json.loads(row["results_json"])
                    score = results.get("bandwidth_hz", 0)

        rankings.append({"id": cid, "name": schema.name, "score": score})

    rankings.sort(key=lambda x: x["score"])
    lines = [f"Rankings by {metric}:", ""]
    for i, r in enumerate(rankings, 1):
        lines.append(f"  {i}. {r['name']} ({r['id'][:8]}): {r['score']}")
    return "\n".join(lines)
