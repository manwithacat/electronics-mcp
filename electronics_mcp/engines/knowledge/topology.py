"""Topology explainer -- provides structured explanations of circuit topologies."""

from electronics_mcp.core.database import Database
from electronics_mcp.engines.knowledge.manager import KnowledgeManager


class TopologyExplainer:
    """Explains circuit topologies using the knowledge base."""

    def __init__(self, db: Database):
        self.db = db
        self.km = KnowledgeManager(db)

    def explain(self, topology_name: str) -> dict:
        """Get a structured explanation of a circuit topology.

        Returns dict with explanation, formulas, related subcircuits,
        and design considerations.
        """
        result: dict = {
            "topology": topology_name,
            "explanation": None,
            "formulas": [],
            "related_subcircuits": [],
            "related_topics": [],
        }

        # Look up in knowledge base
        article = self.km.get_topic(topology_name)
        if article:
            result["explanation"] = article["content"]
            result["formulas"] = article.get("formulas", [])
            result["related_topics"] = article.get("related_topics", [])

        # Search for related subcircuits
        with self.db.connect() as conn:
            subcircuit_rows = conn.execute(
                "SELECT id, name, description, ports "
                "FROM subcircuits WHERE name LIKE ? OR description LIKE ?",
                (f"%{topology_name}%", f"%{topology_name}%"),
            ).fetchall()
            for row in subcircuit_rows:
                result["related_subcircuits"].append(dict(row))

        # If no direct match, try FTS search
        if not result["explanation"]:
            search_results = self.km.search(topology_name, limit=3)
            if search_results:
                result["explanation"] = search_results[0]["content"]
                result["formulas"] = search_results[0].get("formulas", [])
                result["related_topics"] = [r["topic"] for r in search_results[1:]]

        return result

    def list_topologies(self, category: str | None = None) -> list[dict]:
        """List known circuit topologies."""
        with self.db.connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT topic, title, difficulty FROM knowledge "
                    "WHERE category = ? ORDER BY topic",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT topic, title, category, difficulty FROM knowledge "
                    "WHERE category IN ('topology', 'circuit', 'filter', 'amplifier', 'power') "
                    "ORDER BY category, topic",
                ).fetchall()
            return [dict(r) for r in rows]
