"""Design guide generator -- creates step-by-step design procedures."""
from electronics_mcp.core.database import Database
from electronics_mcp.engines.knowledge.manager import KnowledgeManager


class DesignGuide:
    """Generates step-by-step design guides using knowledge base content."""

    def __init__(self, db: Database):
        self.db = db
        self.km = KnowledgeManager(db)

    def generate(self, topic: str, requirements: dict | None = None) -> dict:
        """Generate a design guide for a given topic.

        Args:
            topic: The design topic (e.g., "low_pass_filter", "voltage_divider")
            requirements: Optional design requirements/constraints

        Returns:
            Dict with steps, formulas, component suggestions, and notes.
        """
        guide: dict = {
            "topic": topic,
            "steps": [],
            "formulas": [],
            "component_suggestions": [],
            "notes": [],
        }

        # Get knowledge base content
        article = self.km.get_topic(topic)
        if article:
            guide["formulas"] = article.get("formulas", [])
            # Extract steps from content if available
            guide["steps"] = self._extract_steps(article["content"])
            guide["notes"].append(f"Source: {article.get('source', 'knowledge base')}")

        # Search for additional relevant knowledge
        search_results = self.km.search(topic, limit=5)
        for result in search_results:
            if result["topic"] != topic:
                additional_formulas = result.get("formulas", [])
                for f in additional_formulas:
                    if f not in guide["formulas"]:
                        guide["formulas"].append(f)

        # Get component suggestions from categories
        component_info = self._get_relevant_components(topic)
        guide["component_suggestions"] = component_info

        # Add requirement-based notes
        if requirements:
            guide["notes"].extend(self._requirements_notes(requirements))

        return guide

    def _extract_steps(self, content: str) -> list[str]:
        """Extract numbered steps from content text."""
        steps = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (
                line[0].isdigit() and "." in line[:3]
                or line.startswith("- ")
                or line.startswith("* ")
            ):
                # Strip bullet/number prefix
                clean = line.lstrip("0123456789.-* ").strip()
                if clean:
                    steps.append(clean)
        return steps if steps else [content[:200]]

    def _get_relevant_components(self, topic: str) -> list[dict]:
        """Find component categories relevant to a design topic."""
        # Map common topics to component types
        topic_components = {
            "filter": ["resistor", "capacitor", "inductor"],
            "amplifier": ["resistor", "opamp", "bjt", "mosfet"],
            "voltage_divider": ["resistor"],
            "power_supply": ["capacitor", "diode", "voltage_regulator"],
            "oscillator": ["resistor", "capacitor", "inductor"],
        }

        component_types = set()
        for key, types in topic_components.items():
            if key in topic.lower():
                component_types.update(types)

        if not component_types:
            return []

        suggestions = []
        with self.db.connect() as conn:
            for ctype in component_types:
                rows = conn.execute(
                    "SELECT type, subtype, selection_guide, typical_values "
                    "FROM component_categories WHERE type = ?",
                    (ctype,),
                ).fetchall()
                for row in rows:
                    suggestions.append(dict(row))

        return suggestions

    def _requirements_notes(self, requirements: dict) -> list[str]:
        """Generate notes based on design requirements."""
        notes = []
        if "frequency" in requirements:
            notes.append(f"Target frequency: {requirements['frequency']}")
        if "voltage" in requirements:
            notes.append(f"Operating voltage: {requirements['voltage']}")
        if "tolerance" in requirements:
            notes.append(f"Required tolerance: {requirements['tolerance']}")
        if "power" in requirements:
            notes.append(f"Power budget: {requirements['power']}")
        return notes
