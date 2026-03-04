"""Generate seed SQL from ingested data after QA checks."""
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.build_design_rules import build_design_rules
from electronics_mcp.ingestion.build_formulas import build_formulas
from electronics_mcp.ingestion.build_subcircuits import build_subcircuits
from electronics_mcp.ingestion.qa import run_qa


def _escape_sql(value: str | None) -> str:
    """Escape a string for SQL insertion."""
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _export_table(conn, table: str, columns: list[str]) -> list[str]:
    """Export rows from a table as INSERT statements."""
    rows = conn.execute(
        f"SELECT {', '.join(columns)} FROM {table}"  # noqa: S608
    ).fetchall()
    statements = []
    for row in rows:
        values = []
        for col in columns:
            val = row[col]
            if val is None:
                values.append("NULL")
            else:
                values.append(_escape_sql(str(val)))
        stmt = (
            f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(values)});"
        )
        statements.append(stmt)
    return statements


def generate_seed_sql(db: Database, output_path: Path | str) -> dict:
    """Run ingestion, QA, and export passing records as seed SQL.

    Returns stats dict.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run ingestion
    dr_stats = build_design_rules(db)
    fm_stats = build_formulas(db)
    sc_stats = build_subcircuits(db)

    # Run QA
    qa_result = run_qa(db)

    # Collect IDs with issues for exclusion
    issue_ids: set[str] = set()
    for check_list in qa_result["checks"].values():
        for item in check_list:
            issue_ids.add(item["id"])

    # Export tables
    statements = ["-- ElectronicsMCP Seed Data", "-- Auto-generated", ""]

    with db.connect() as conn:
        # Knowledge
        statements.append("-- Knowledge Base")
        for stmt in _export_table(conn, "knowledge", [
            "id", "category", "topic", "title", "content",
            "formulas", "related_topics", "difficulty", "source",
        ]):
            statements.append(stmt)

        # Subcircuits
        statements.append("\n-- Subcircuit Library")
        for stmt in _export_table(conn, "subcircuits", [
            "id", "name", "category", "description", "schema_json",
            "ports", "parameters", "design_notes", "source",
        ]):
            statements.append(stmt)

        # Component categories (always include)
        statements.append("\n-- Component Categories")
        for stmt in _export_table(conn, "component_categories", [
            "type", "subtype", "selection_guide", "typical_values",
        ]):
            statements.append(stmt)

    statements.append("")
    output_path.write_text("\n".join(statements))

    return {
        "design_rules": dr_stats,
        "formulas": fm_stats,
        "subcircuits": sc_stats,
        "qa_issues": qa_result["total_issues"],
        "output": str(output_path),
    }
