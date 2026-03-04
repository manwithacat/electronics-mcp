"""Circuit CRUD operations with versioning and validation."""
import json
import uuid
from collections import Counter

from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import (
    CircuitSchema, CircuitModification, ComponentBase,
)
from electronics_mcp.core.units import parse_value, format_value


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

    def generate_netlist(self, circuit_id: str) -> str:
        """Generate a SPICE netlist from the circuit schema.

        Expands subcircuit instances inline and maps component types
        to SPICE element lines.
        """
        schema = self.get_schema(circuit_id)
        lines = [f"* {schema.name}"]
        if schema.description:
            lines.append(f"* {schema.description}")
        lines.append("")

        # Map ground node to SPICE node 0
        def spice_node(node: str) -> str:
            return "0" if node == schema.ground_node else node

        # Expand subcircuit instances
        expanded_components = list(schema.components)
        for inst in schema.subcircuit_instances:
            sub_comps = self._expand_subcircuit(inst)
            expanded_components.extend(sub_comps)

        # Generate SPICE lines for each component
        for comp in expanded_components:
            line = self._component_to_spice(comp, spice_node)
            if line:
                lines.append(line)

        lines.append("")
        lines.append(".end")
        return "\n".join(lines)

    def _expand_subcircuit(self, inst) -> list[ComponentBase]:
        """Expand a subcircuit instance into inline components."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT schema_json, ports, parameters FROM subcircuits WHERE name = ?",
                (inst.reference,),
            ).fetchone()
            if row is None:
                return []

        sub_schema = json.loads(row["schema_json"])
        sub_params = json.loads(row["parameters"]) if row["parameters"] else []
        sub_ports = json.loads(row["ports"]) if row["ports"] else []

        # Build parameter map: param_name -> value (from instance or defaults)
        param_map = {}
        for p in sub_params:
            param_map[p["name"]] = inst.parameters.get(p["name"], p.get("default", ""))

        # Build port map: subcircuit port name -> circuit node name
        port_map = dict(inst.port_connections)

        components = []
        for comp_data in sub_schema.get("components", []):
            # Prefix component IDs to avoid collisions
            new_id = f"{inst.id}_{comp_data['id']}"

            # Substitute parameters
            new_params = {}
            for k, v in comp_data.get("parameters", {}).items():
                if v.startswith("PARAM_"):
                    param_name = v[6:]  # Strip PARAM_ prefix
                    new_params[k] = param_map.get(param_name, v)
                else:
                    new_params[k] = v

            # Map subcircuit nodes to circuit nodes
            new_nodes = [port_map.get(n, f"{inst.id}_{n}") for n in comp_data.get("nodes", [])]

            components.append(ComponentBase(
                id=new_id,
                type=comp_data["type"],
                parameters=new_params,
                nodes=new_nodes,
            ))

        return components

    def _component_to_spice(self, comp: ComponentBase, spice_node) -> str | None:
        """Convert a single component to a SPICE netlist line."""
        nodes_str = " ".join(spice_node(n) for n in comp.nodes)

        if comp.type == "resistor":
            val = comp.parameters.get("resistance", "1k")
            return f"R{comp.id.lstrip('R')} {nodes_str} {self._spice_value(val)}"

        elif comp.type == "capacitor":
            val = comp.parameters.get("capacitance", "1n")
            return f"C{comp.id.lstrip('C')} {nodes_str} {self._spice_value(val)}"

        elif comp.type == "inductor":
            val = comp.parameters.get("inductance", "1u")
            return f"L{comp.id.lstrip('L')} {nodes_str} {self._spice_value(val)}"

        elif comp.type == "voltage_source":
            if comp.subtype == "dc":
                voltage = comp.parameters.get("voltage", "0V")
                return f"V{comp.id.lstrip('V')} {nodes_str} DC {self._spice_value(voltage)}"
            elif comp.subtype == "ac":
                amp = comp.parameters.get("amplitude", "1V")
                return f"V{comp.id.lstrip('V')} {nodes_str} AC {self._spice_value(amp)}"
            elif comp.subtype == "pulse":
                v1 = comp.parameters.get("v1", "0")
                v2 = comp.parameters.get("v2", "5")
                rise = comp.parameters.get("rise_time", "1n")
                pw = comp.parameters.get("pulse_width", "10m")
                return (f"V{comp.id.lstrip('V')} {nodes_str} "
                        f"PULSE({self._spice_value(v1)} {self._spice_value(v2)} "
                        f"0 {self._spice_value(rise)} {self._spice_value(rise)} "
                        f"{self._spice_value(pw)} {self._spice_value(pw)})")
            else:
                voltage = comp.parameters.get("voltage", "0V")
                return f"V{comp.id.lstrip('V')} {nodes_str} {self._spice_value(voltage)}"

        elif comp.type == "current_source":
            val = comp.parameters.get("current", "1m")
            return f"I{comp.id.lstrip('I')} {nodes_str} {self._spice_value(val)}"

        elif comp.type == "diode":
            return f"D{comp.id.lstrip('D')} {nodes_str} D1N4148"

        elif comp.type in ("bjt",):
            model = "Q2N2222" if comp.subtype == "npn" else "Q2N2907"
            return f"Q{comp.id.lstrip('Q')} {nodes_str} {model}"

        elif comp.type in ("mosfet",):
            model = "NMOS" if comp.subtype == "nmos" else "PMOS"
            return f"M{comp.id.lstrip('M')} {nodes_str} {model}"

        elif comp.type == "opamp":
            return f"X{comp.id} {nodes_str} OPAMP"

        return f"* Unsupported: {comp.id} ({comp.type})"

    def _spice_value(self, val: str) -> str:
        """Convert an EE value string to a SPICE-compatible value."""
        try:
            numeric = parse_value(val)
            # SPICE uses its own suffixes: meg instead of M, etc.
            # For simplicity, return the numeric value
            if numeric == int(numeric) and abs(numeric) < 1e15:
                return str(int(numeric))
            return f"{numeric:g}"
        except ValueError:
            return val
