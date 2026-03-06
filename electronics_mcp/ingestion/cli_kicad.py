"""CLI wrapper: ingest KiCad symbol library files."""
import argparse
import sys
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_kicad_symbols import ingest_kicad_symbols


def main():
    parser = argparse.ArgumentParser(
        description="Ingest KiCad .kicad_sym symbol library files.",
    )
    parser.add_argument(
        "--file", type=Path, action="append", dest="files",
        help="KiCad symbol library file(s) to ingest (can be repeated)",
    )
    parser.add_argument(
        "--dir", type=Path, default=None,
        help="Directory to scan for .kicad_sym files",
    )
    parser.add_argument(
        "--db", type=Path, default=Path("electronics.db"),
        help="Database file path (default: electronics.db)",
    )
    args = parser.parse_args()

    files_to_process: list[Path] = []
    if args.files:
        files_to_process.extend(args.files)
    if args.dir:
        if not args.dir.exists():
            print(f"Error: directory not found: {args.dir}")
            sys.exit(1)
        files_to_process.extend(sorted(args.dir.glob("**/*.kicad_sym")))

    if not files_to_process:
        print("Error: provide --file or --dir")
        sys.exit(1)

    db = Database(args.db)
    db.initialize()

    total_symbols = 0
    total_skipped = 0
    for f in files_to_process:
        if not f.exists():
            print(f"Warning: file not found: {f}")
            continue
        print(f"Ingesting {f.name}...")
        stats = ingest_kicad_symbols(f, db)
        total_symbols += stats["symbols"]
        total_skipped += stats["skipped"]

    print(f"\nTotal symbols ingested: {total_symbols}")
    print(f"Total skipped (duplicates): {total_skipped}")


if __name__ == "__main__":
    main()
