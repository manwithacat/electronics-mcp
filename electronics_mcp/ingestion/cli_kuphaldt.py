"""CLI wrapper: download and ingest Kuphaldt 'Lessons in Electric Circuits'."""

import argparse
import sys
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_kuphaldt import ingest_kuphaldt


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Kuphaldt 'Lessons in Electric Circuits' HTML volumes.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing Kuphaldt HTML volume files",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("electronics.db"),
        help="Database file path (default: electronics.db)",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=50,
        help="Minimum content length to keep (default: 50)",
    )
    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"Error: source directory not found: {args.source_dir}")
        sys.exit(1)

    db = Database(args.db)
    db.initialize()

    print(f"Ingesting Kuphaldt volumes from {args.source_dir}...")
    stats = ingest_kuphaldt(args.source_dir, db, min_content_length=args.min_length)

    print(f"Articles ingested: {stats['articles']}")
    print(f"Formulas extracted: {stats['formulas']}")
    print(f"Skipped (duplicates/short): {stats['skipped']}")


if __name__ == "__main__":
    main()
