"""MCP tools for knowledge base access and learning."""
import json
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.engines.knowledge.manager import KnowledgeManager
from electronics_mcp.engines.knowledge.topology import TopologyExplainer
from electronics_mcp.engines.knowledge.design_guide import DesignGuide


@mcp.tool()
def search_knowledge(query: str, category: str | None = None) -> str:
    """Search the electronics knowledge base using full-text search.

    Args:
        query: Search terms (e.g. "low pass filter cutoff")
        category: Optional category filter (topology, filter, amplifier, etc.)
    """
    km = KnowledgeManager(get_db())
    results = km.search(query, category)
    if not results:
        return f"No results found for '{query}'."
    lines = [f"Found {len(results)} results:", ""]
    for r in results:
        lines.append(f"  [{r['category']}] {r['title']}")
        lines.append(f"    Topic: {r['topic']}")
        lines.append(f"    {r['content'][:150]}...")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_topic(topic: str) -> str:
    """Get a full knowledge article by topic name.

    Args:
        topic: Topic identifier (e.g. "voltage_divider", "low_pass_rc")
    """
    km = KnowledgeManager(get_db())
    article = km.get_topic(topic)
    if not article:
        return f"No article found for topic '{topic}'."
    lines = [f"# {article['title']}", ""]
    lines.append(f"Category: {article['category']}")
    lines.append(f"Difficulty: {article.get('difficulty', 'N/A')}")
    lines.append("")
    lines.append(article["content"])
    if article.get("formulas"):
        lines.append("")
        lines.append("## Formulas")
        for f in article["formulas"]:
            lines.append(f"  {f.get('name', '?')}: {f.get('expression', '?')}")
    if article.get("related_topics"):
        lines.append("")
        lines.append(f"Related: {', '.join(article['related_topics'])}")
    return "\n".join(lines)


@mcp.tool()
def explain_topology(topology_name: str) -> str:
    """Get a structured explanation of a circuit topology.

    Args:
        topology_name: Name of the topology (e.g. "common_emitter", "h_bridge")
    """
    explainer = TopologyExplainer(get_db())
    result = explainer.explain(topology_name)
    lines = [f"# Topology: {topology_name}", ""]
    if result.get("explanation"):
        lines.append(result["explanation"])
    else:
        lines.append("No detailed explanation available.")
    if result.get("formulas"):
        lines.append("")
        lines.append("## Key Formulas")
        for f in result["formulas"]:
            lines.append(f"  {f.get('name', '?')}: {f.get('expression', '?')}")
    if result.get("related_subcircuits"):
        lines.append("")
        lines.append("## Related Subcircuits")
        for sc in result["related_subcircuits"]:
            lines.append(f"  - {sc.get('name', '?')}: {sc.get('description', '')}")
    return "\n".join(lines)


@mcp.tool()
def design_guide(topic: str, requirements_json: str | None = None) -> str:
    """Get a step-by-step design guide for a circuit type.

    Args:
        topic: Design topic (e.g. "low_pass_filter", "voltage_divider")
        requirements_json: Optional JSON with design requirements
    """
    guide = DesignGuide(get_db())
    requirements = json.loads(requirements_json) if requirements_json else None
    result = guide.generate(topic, requirements)

    lines = [f"# Design Guide: {topic}", ""]
    if result.get("steps"):
        lines.append("## Steps")
        for i, step in enumerate(result["steps"], 1):
            lines.append(f"  {i}. {step}")
    if result.get("formulas"):
        lines.append("")
        lines.append("## Formulas")
        for f in result["formulas"]:
            lines.append(f"  {f.get('name', '?')}: {f.get('expression', '?')}")
    if result.get("component_suggestions"):
        lines.append("")
        lines.append("## Component Selection")
        for cs in result["component_suggestions"]:
            lines.append(f"  - {cs.get('type', '?')}/{cs.get('subtype', 'general')}")
    if result.get("notes"):
        lines.append("")
        lines.append("## Notes")
        for note in result["notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines)


@mcp.tool()
def component_info(component_type: str, model: str | None = None) -> str:
    """Look up component information from the database.

    Args:
        component_type: Type (resistor, capacitor, opamp, etc.)
        model: Optional model/part number filter
    """
    km = KnowledgeManager(get_db())
    info = km.component_info(component_type, model)

    lines = [f"# Component Info: {component_type}", ""]
    if info.get("categories"):
        lines.append("## Categories")
        for cat in info["categories"]:
            lines.append(f"  - {cat.get('subtype', 'general')}: {cat.get('selection_guide', 'N/A')}")
    if info.get("models"):
        lines.append("")
        lines.append("## Available Models")
        for m in info["models"]:
            lines.append(f"  - {m.get('manufacturer', '?')} {m.get('part_number', '?')}")
            if m.get("description"):
                lines.append(f"    {m['description']}")
    elif not info.get("categories"):
        lines.append("No information found.")
    return "\n".join(lines)


@mcp.tool()
def list_formulas(topic: str) -> str:
    """List formulas associated with a knowledge topic.

    Args:
        topic: Topic name to get formulas for
    """
    km = KnowledgeManager(get_db())
    formulas = km.get_formulas(topic)
    if not formulas:
        return f"No formulas found for topic '{topic}'."
    lines = [f"Formulas for {topic}:", ""]
    for f in formulas:
        lines.append(f"  {f.get('name', '?')}: {f.get('expression', '?')}")
        if f.get("description"):
            lines.append(f"    {f['description']}")
    return "\n".join(lines)


@mcp.tool()
def learn_pattern(
    category: str,
    topic: str,
    title: str,
    content: str,
    formulas_json: str | None = None,
) -> str:
    """Store new knowledge in the database for future reference.

    Args:
        category: Knowledge category (topology, filter, amplifier, etc.)
        topic: Unique topic identifier
        title: Human-readable title
        content: Full article content
        formulas_json: Optional JSON array of formula objects
    """
    km = KnowledgeManager(get_db())
    formulas = json.loads(formulas_json) if formulas_json else None
    entry_id = km.learn_pattern(category, topic, title, content, formulas)
    return f"Knowledge entry '{title}' stored with ID: {entry_id}"
