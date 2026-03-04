"""Component suggestion engine -- finds real parts matching ideal values."""
from electronics_mcp.core.database import Database
from electronics_mcp.core.units import parse_value
import json


class ComponentSuggester:
    """Suggests real components from the database that match ideal values."""

    def __init__(self, db: Database):
        self.db = db

    def suggest(
        self,
        component_type: str,
        target_value: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Find components matching a type and optional target value.

        Returns list of component dicts sorted by relevance.
        """
        with self.db.connect() as conn:
            if target_value:
                rows = conn.execute(
                    "SELECT id, type, manufacturer, part_number, description, "
                    "parameters, spice_model, footprint, datasheet_url "
                    "FROM component_models WHERE type = ? LIMIT ?",
                    (component_type, limit * 3),
                ).fetchall()

                # Rank by closeness to target value
                try:
                    target = parse_value(target_value)
                except ValueError:
                    target = None

                results = []
                for row in rows:
                    d = dict(row)
                    d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
                    if target is not None:
                        d["match_score"] = self._score_match(d, target)
                    results.append(d)

                results.sort(key=lambda x: x.get("match_score", float("inf")))
                return results[:limit]
            else:
                rows = conn.execute(
                    "SELECT id, type, manufacturer, part_number, description, "
                    "parameters, spice_model, footprint, datasheet_url "
                    "FROM component_models WHERE type = ? LIMIT ?",
                    (component_type, limit),
                ).fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
                    results.append(d)
                return results

    def get_selection_guide(self, component_type: str) -> list[dict]:
        """Get selection guide for a component type."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT type, subtype, selection_guide, typical_values "
                "FROM component_categories WHERE type = ?",
                (component_type,),
            ).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d["typical_values"]:
                    d["typical_values"] = json.loads(d["typical_values"])
                results.append(d)
            return results

    def _score_match(self, component: dict, target: float) -> float:
        """Score how close a component matches a target value (lower is better)."""
        # Try to extract a comparable value from component parameters
        params = component.get("parameters", {})
        for key in ("resistance", "capacitance", "inductance", "value"):
            if key in params:
                try:
                    val = parse_value(str(params[key]))
                    if val > 0 and target > 0:
                        return abs(val / target - 1.0)
                except (ValueError, ZeroDivisionError):
                    pass
        return float("inf")
