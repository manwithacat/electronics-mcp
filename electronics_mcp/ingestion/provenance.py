"""Record provenance (data lineage) for ingested records."""

from datetime import datetime, timezone

from electronics_mcp.core.database import Database


def record_provenance(
    db: Database,
    record_table: str,
    record_id: str,
    source_name: str,
    *,
    source_url: str | None = None,
    licence: str = "unknown",
    original_path: str | None = None,
    notes: str | None = None,
) -> None:
    """Record provenance for a single ingested record."""
    with db.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO provenance "
            "(record_table, record_id, source_name, source_url, licence, "
            "original_path, extraction_date, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record_table,
                record_id,
                source_name,
                source_url,
                licence,
                original_path,
                datetime.now(timezone.utc).isoformat(),
                notes,
            ),
        )


def record_bulk_provenance(
    db: Database,
    record_table: str,
    record_ids: list[str],
    source_name: str,
    *,
    source_url: str | None = None,
    licence: str = "unknown",
    original_path: str | None = None,
    notes: str | None = None,
) -> int:
    """Record provenance for multiple records at once.

    Returns count of rows inserted.
    """
    if not record_ids:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO provenance "
            "(record_table, record_id, source_name, source_url, licence, "
            "original_path, extraction_date, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    record_table,
                    rid,
                    source_name,
                    source_url,
                    licence,
                    original_path,
                    now,
                    notes,
                )
                for rid in record_ids
            ],
        )
    return len(record_ids)
