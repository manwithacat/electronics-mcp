"""CLI wrapper: ingest SPICE model files from a directory."""

import argparse
import sys
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.ingest_spice_models import ingest_spice_directory


def main():
    parser = argparse.ArgumentParser(
        description="Ingest SPICE .model/.subckt files into the component database.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Directory containing SPICE model files (.lib, .mod, .model, .spice)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("electronics.db"),
        help="Database file path (default: electronics.db)",
    )
    args = parser.parse_args()

    if not args.dir.exists():
        print(f"Error: directory not found: {args.dir}")
        sys.exit(1)

    db = Database(args.db)
    db.initialize()

    print(f"Ingesting SPICE models from {args.dir}...")
    stats = ingest_spice_directory(args.dir, db)

    print(f"Files processed: {stats['files']}")
    print(f"Models ingested: {stats['models']}")
    print(f"Subcircuits ingested: {stats['subcircuits']}")
    print(f"Parse errors: {stats['errors']}")


if __name__ == "__main__":
    main()
