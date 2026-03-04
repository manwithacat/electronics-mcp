"""Report generation (Markdown + PDF)."""
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from electronics_mcp.core.schema import CircuitSchema

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_markdown(
    circuit: CircuitSchema,
    output_path: Path | str,
    title: str | None = None,
    simulation_results: list[dict] | None = None,
    validation_warnings: list[str] | None = None,
    notes: list[str] | None = None,
) -> Path:
    """Generate a Markdown report for a circuit.

    Returns the path to the generated Markdown file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.md.j2")

    content = template.render(
        title=title or f"Circuit Report: {circuit.name}",
        description=circuit.description,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        circuit=circuit,
        simulation_results=simulation_results or [],
        validation_warnings=validation_warnings or [],
        notes=notes or [],
    )

    output_path.write_text(content)
    return output_path


def generate_pdf(
    markdown_path: Path | str,
    output_path: Path | str | None = None,
) -> Path:
    """Convert a Markdown report to PDF using weasyprint.

    Returns the path to the generated PDF file.
    """
    markdown_path = Path(markdown_path)
    if output_path is None:
        output_path = markdown_path.with_suffix(".pdf")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = markdown_path.read_text()

    # Convert Markdown to basic HTML for weasyprint
    html = _markdown_to_html(content)

    from weasyprint import HTML
    HTML(string=html).write_pdf(str(output_path))

    return output_path


def _markdown_to_html(md: str) -> str:
    """Simple Markdown to HTML conversion for report rendering."""
    import re

    html_lines = []
    in_table = False
    in_list = False

    for line in md.split("\n"):
        stripped = line.strip()

        # Headers
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        # Horizontal rule
        elif stripped == "---":
            html_lines.append("<hr>")
        # Table rows
        elif stripped.startswith("|"):
            if not in_table:
                html_lines.append("<table>")
                in_table = True
            # Skip separator rows
            if re.match(r"^\|[\s\-|]+\|$", stripped):
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            row = "".join(f"<td>{c}</td>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
        # List items
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            # Handle bold in list items
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped[2:])
            html_lines.append(f"<li>{item}</li>")
        # Images
        elif stripped.startswith("!["):
            match = re.match(r"!\[(.+?)\]\((.+?)\)", stripped)
            if match:
                html_lines.append(f'<img src="{match.group(2)}" alt="{match.group(1)}">')
        # Empty line
        elif not stripped:
            if in_table:
                html_lines.append("</table>")
                in_table = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
        # Plain text with bold
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            html_lines.append(f"<p>{text}</p>")

    if in_table:
        html_lines.append("</table>")
    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html><head>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
tr:nth-child(even) {{ background-color: #f9f9f9; }}
img {{ max-width: 100%; }}
hr {{ border: 1px solid #ddd; margin: 2em 0; }}
</style>
</head><body>
{body}
</body></html>"""
