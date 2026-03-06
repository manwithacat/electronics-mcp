"""Knowledge base manager with FTS5 search."""

import json
import uuid
from electronics_mcp.core.database import Database


class KnowledgeManager:
    """Manages the electronics knowledge base with full-text search."""

    def __init__(self, db: Database):
        self.db = db

    def search(
        self, query: str, category: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Full-text search across the knowledge base.

        Uses SQLite FTS5 for ranked search results.
        """
        # Sanitize query for FTS5: wrap each token in double quotes
        # to prevent operators like hyphens from being interpreted as column names
        fts_query = " ".join(f'"{token}"' for token in query.split())

        with self.db.connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT k.id, k.category, k.topic, k.title, k.content, "
                    "k.formulas, k.related_topics, k.difficulty "
                    "FROM knowledge k "
                    "JOIN knowledge_fts fts ON k.rowid = fts.rowid "
                    "WHERE knowledge_fts MATCH ? AND k.category = ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_query, category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT k.id, k.category, k.topic, k.title, k.content, "
                    "k.formulas, k.related_topics, k.difficulty "
                    "FROM knowledge k "
                    "JOIN knowledge_fts fts ON k.rowid = fts.rowid "
                    "WHERE knowledge_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_query, limit),
                ).fetchall()

            results = []
            for row in rows:
                d = dict(row)
                d["formulas"] = json.loads(d["formulas"]) if d["formulas"] else []
                d["related_topics"] = (
                    json.loads(d["related_topics"]) if d["related_topics"] else []
                )
                results.append(d)
            return results

    def get_topic(self, topic: str) -> dict | None:
        """Retrieve a full knowledge article by topic name."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT id, category, topic, title, content, formulas, "
                "related_topics, difficulty, source "
                "FROM knowledge WHERE topic = ?",
                (topic,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["formulas"] = json.loads(d["formulas"]) if d["formulas"] else []
            d["related_topics"] = (
                json.loads(d["related_topics"]) if d["related_topics"] else []
            )
            return d

    def get_formulas(self, topic: str) -> list[dict]:
        """Get formulas associated with a topic."""
        article = self.get_topic(topic)
        if not article:
            return []
        return article.get("formulas", [])

    def learn_pattern(
        self,
        category: str,
        topic: str,
        title: str,
        content: str,
        formulas: list[dict] | None = None,
        related_topics: list[str] | None = None,
        difficulty: str = "intermediate",
    ) -> str:
        """Store new knowledge in the database.

        Returns the ID of the created entry.
        """
        entry_id = str(uuid.uuid4())
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'learned')",
                (
                    entry_id,
                    category,
                    topic,
                    title,
                    content,
                    json.dumps(formulas or []),
                    json.dumps(related_topics or []),
                    difficulty,
                ),
            )
        return entry_id

    def component_info(self, component_type: str, model: str | None = None) -> dict:
        """Get component information from the database.

        Returns category info and optionally specific model data.
        """
        result: dict = {"type": component_type, "categories": [], "models": []}

        with self.db.connect() as conn:
            # Get category info
            cat_rows = conn.execute(
                "SELECT type, subtype, selection_guide, typical_values "
                "FROM component_categories WHERE type = ?",
                (component_type,),
            ).fetchall()
            for row in cat_rows:
                d = dict(row)
                d["typical_values"] = (
                    json.loads(d["typical_values"]) if d["typical_values"] else []
                )
                result["categories"].append(d)

            # Get models
            if model:
                model_rows = conn.execute(
                    "SELECT id, type, manufacturer, part_number, description, "
                    "parameters, spice_model, footprint, datasheet_url "
                    "FROM component_models WHERE type = ? AND "
                    "(part_number LIKE ? OR description LIKE ?)",
                    (component_type, f"%{model}%", f"%{model}%"),
                ).fetchall()
            else:
                model_rows = conn.execute(
                    "SELECT id, type, manufacturer, part_number, description, "
                    "parameters, spice_model, footprint, datasheet_url "
                    "FROM component_models WHERE type = ? LIMIT 10",
                    (component_type,),
                ).fetchall()

            for row in model_rows:
                d = dict(row)
                d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
                result["models"].append(d)

        return result
