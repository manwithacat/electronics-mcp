"""Ingest knowledge from 'Lessons in Electric Circuits' (Kuphaldt) HTML volumes."""
import re
import json
import uuid
from pathlib import Path
from html.parser import HTMLParser

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import record_provenance


# Volume categories
VOLUME_CATEGORIES = {
    "DC": "fundamentals",
    "AC": "ac_theory",
    "Semi": "semiconductor",
    "Digital": "digital",
    "Ref": "reference",
    "Exper": "experiments",
}


class _SectionExtractor(HTMLParser):
    """Extract sections from Kuphaldt HTML by heading structure."""

    def __init__(self):
        super().__init__()
        self.sections: list[dict] = []
        self._current_tag = ""
        self._current_heading = ""
        self._current_content: list[str] = []
        self._in_heading = False
        self._heading_level = 0
        self._capture_content = False

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag in ("h1", "h2", "h3", "h4"):
            self._flush_section()
            self._in_heading = True
            self._heading_level = int(tag[1])
            self._current_heading = ""
        elif tag in ("p", "li", "td", "pre"):
            self._capture_content = True

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4"):
            self._in_heading = False
            self._capture_content = True
        elif tag in ("p", "li", "td", "pre"):
            self._capture_content = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_heading:
            self._current_heading += text
        elif self._capture_content:
            self._current_content.append(text)

    def _flush_section(self):
        if self._current_heading and self._current_content:
            self.sections.append({
                "title": self._current_heading.strip(),
                "content": "\n".join(self._current_content),
                "level": self._heading_level,
            })
        self._current_content = []

    def close(self):
        self._flush_section()
        super().close()


def _extract_formulas(text: str) -> list[dict]:
    """Extract formula-like patterns from text."""
    formulas = []
    # Match patterns like "V = IR", "f = 1/(2*pi*R*C)", etc.
    formula_re = re.compile(
        r'([A-Z][a-z_]*)\s*=\s*([^.;,\n]{3,50}(?:[\*/\+\-\(\)][^.;,\n]{1,30})*)'
    )
    for match in formula_re.finditer(text):
        name = match.group(1).strip()
        expr = match.group(2).strip()
        if len(expr) > 3 and any(c in expr for c in "*/+-()"):
            formulas.append({"name": name, "expression": expr})
    return formulas


def _difficulty_from_depth(volume: str, level: int) -> str:
    """Estimate difficulty from volume + heading depth."""
    base = {"DC": 0, "AC": 1, "Semi": 2, "Digital": 2, "Ref": 1, "Exper": 1}
    score = base.get(volume, 1) + max(0, level - 2)
    if score <= 1:
        return "beginner"
    elif score <= 3:
        return "intermediate"
    return "advanced"


def _topic_slug(title: str) -> str:
    """Convert a heading to a topic slug."""
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
    return slug[:60]


def ingest_kuphaldt(
    source_dir: Path | str,
    db: Database,
    min_content_length: int = 50,
) -> dict:
    """Ingest Kuphaldt HTML volumes into the knowledge database.

    Args:
        source_dir: Directory containing volume HTML files
        db: Database to populate
        min_content_length: Minimum content length to keep

    Returns:
        Dict with counts of articles and formulas ingested.
    """
    source_dir = Path(source_dir)
    stats = {"articles": 0, "formulas": 0, "skipped": 0}

    for html_file in sorted(source_dir.glob("*.html")):
        volume = _guess_volume(html_file.stem)
        category = VOLUME_CATEGORIES.get(volume, "general")

        content = html_file.read_text(errors="replace")
        parser = _SectionExtractor()
        parser.feed(content)
        parser.close()

        for section in parser.sections:
            if len(section["content"]) < min_content_length:
                stats["skipped"] += 1
                continue

            topic = _topic_slug(section["title"])
            formulas = _extract_formulas(section["content"])
            difficulty = _difficulty_from_depth(volume, section["level"])

            entry_id = str(uuid.uuid4())
            created = False
            with db.connect() as conn:
                # Skip duplicates
                existing = conn.execute(
                    "SELECT id FROM knowledge WHERE topic = ?", (topic,)
                ).fetchone()
                if existing:
                    stats["skipped"] += 1
                    continue

                conn.execute(
                    "INSERT INTO knowledge (id, category, topic, title, content, "
                    "formulas, related_topics, difficulty, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'kuphaldt')",
                    (entry_id, category, topic, section["title"],
                     section["content"], json.dumps(formulas),
                     json.dumps([]), difficulty),
                )
                created = True

            if created:
                record_provenance(
                    db, "knowledge", entry_id, "kuphaldt",
                    source_url="https://www.allaboutcircuits.com/textbook/",
                    licence="Design Science License",
                    original_path=str(html_file),
                    notes=f"Volume: {volume}, Topic: {topic}",
                )
                stats["articles"] += 1
                stats["formulas"] += len(formulas)

    return stats


def _guess_volume(filename: str) -> str:
    """Guess the volume from filename."""
    for prefix in VOLUME_CATEGORIES:
        if prefix.lower() in filename.lower():
            return prefix
    return "Ref"
