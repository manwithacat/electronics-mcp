"""Circuit CRUD operations with versioning and validation."""
import json
import uuid
from collections import Counter

from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import (
    CircuitSchema, CircuitModification, ComponentBase,
)


class CircuitManager:
    """Manages circuit lifecycle: create, read, modify, clone, delete, validate."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, schema: CircuitSchema) -> str:
        """Create a new circuit and store version 1."""
        circuit_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        schema_json = schema.model_dump_json()

        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO circuits (id, name, description, schema_json, status) "
                "VALUES (?, ?, ?, ?, 'draft')",
                (circuit_id, schema.name, schema.description, schema_json),
            )
            conn.execute(
                "INSERT INTO circuit_versions (id, circuit_id, version, schema_json) "
                "VALUES (?, ?, 1, ?)",
                (version_id, circuit_id, schema_json),
            )
        return circuit_id

    def get(self, circuit_id: str) -> dict | None:
        """Retrieve circuit metadata."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT id, name, description, status, created_at, updated_at "
                "FROM circuits WHERE id = ?",
                (circuit_id,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def get_schema(self, circuit_id: str) -> CircuitSchema:
        """Get the current circuit schema as a Pydantic model."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT schema_json FROM circuits WHERE id = ?",
                (circuit_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Circuit {circuit_id} not found")
            return CircuitSchema.model_validate_json(row["schema_json"])

    def modify(self, circuit_id: str, mod: CircuitModification) -> int:
        """Apply a modification and create a new version. Returns new version number."""
        schema = self.get_schema(circuit_id)

        # Apply removals
        if mod.remove:
            schema.components = [c for c in schema.components if c.id not in mod.remove]

        # Apply updates
        for update in mod.update:
            for comp in schema.components:
                if comp.id == update.id:
                    comp.parameters.update(update.parameters)
                    if update.nodes is not None:
                        comp.nodes = update.nodes
                    break

        # Apply additions
        schema.components.extend(mod.add)

        # Apply node renames
        if mod.rename_node:
            for comp in schema.components:
                comp.nodes = [mod.rename_node.get(n, n) for n in comp.nodes]

        # Store updated schema and new version
        schema_json = schema.model_dump_json()
        with self.db.connect() as conn:
            # Get current max version
            row = conn.execute(
                "SELECT MAX(version) as max_v FROM circuit_versions WHERE circuit_id = ?",
                (circuit_id,),
            ).fetchone()
            new_version = (row["max_v"] or 0) + 1

            version_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO circuit_versions (id, circuit_id, version, schema_json) "
                "VALUES (?, ?, ?, ?)",
                (version_id, circuit_id, new_version, schema_json),
            )
            conn.execute(
                "UPDATE circuits SET schema_json = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (schema_json, circuit_id),
            )
        return new_version

    def clone(self, circuit_id: str, new_name: str) -> str:
        """Deep copy a circuit with a new name."""
        schema = self.get_schema(circuit_id)
        schema.name = new_name
        return self.create(schema)

    def delete(self, circuit_id: str):
        """Remove a circuit and all related data."""
        with self.db.connect() as conn:
            conn.execute("DELETE FROM simulation_results WHERE circuit_id = ?", (circuit_id,))
            conn.execute("DELETE FROM circuit_versions WHERE circuit_id = ?", (circuit_id,))
            conn.execute("DELETE FROM project_notes WHERE circuit_id = ?", (circuit_id,))
            conn.execute("DELETE FROM design_decisions WHERE circuit_id = ?", (circuit_id,))
            conn.execute("DELETE FROM circuits WHERE id = ?", (circuit_id,))

    def validate(self, circuit_id: str) -> list[str]:
        """Check circuit for errors. Returns list of warning strings."""
        schema = self.get_schema(circuit_id)
        warnings = []

        # Count node connections
        node_counts: Counter[str] = Counter()
        for comp in schema.components:
            for node in comp.nodes:
                node_counts[node] += 1

        # Check for floating nodes (connected to only one component)
        for node, count in node_counts.items():
            if count < 2 and node != schema.ground_node:
                warnings.append(f"Floating/unconnected node: '{node}' (only 1 connection)")

        # Check for ground node
        if schema.ground_node not in node_counts and schema.components:
            warnings.append(f"No ground node '{schema.ground_node}' found in circuit")

        # Check for parallel voltage sources (same two nodes)
        vsources = [c for c in schema.components if c.type == "voltage_source"]
        node_pairs = [tuple(sorted(v.nodes[:2])) for v in vsources if len(v.nodes) >= 2]
        seen_pairs: set[tuple[str, ...]] = set()
        for pair in node_pairs:
            if pair in seen_pairs:
                warnings.append(f"Parallel voltage sources on nodes {pair}")
            seen_pairs.add(pair)

        return warnings

    def list_all(self) -> list[dict]:
        """List all circuits."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT c.id, c.name, c.description, c.status, c.created_at, "
                "c.schema_json FROM circuits c ORDER BY c.created_at DESC"
            ).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                schema = json.loads(d.pop("schema_json"))
                d["component_count"] = len(schema.get("components", []))
                results.append(d)
            return results

    def get_versions(self, circuit_id: str) -> list[dict]:
        """Get version history for a circuit."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, version, change_summary, created_at "
                "FROM circuit_versions WHERE circuit_id = ? ORDER BY version",
                (circuit_id,),
            ).fetchall()
            return [dict(r) for r in rows]
