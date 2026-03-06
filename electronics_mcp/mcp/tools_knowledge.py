"""MCP tools for knowledge base access and learning."""

import json
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.core.circuit_manager import CircuitManager
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
            lines.append(
                f"  - {cat.get('subtype', 'general')}: {cat.get('selection_guide', 'N/A')}"
            )
    if info.get("models"):
        lines.append("")
        lines.append("## Available Models")
        for m in info["models"]:
            lines.append(
                f"  - {m.get('manufacturer', '?')} {m.get('part_number', '?')}"
            )
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


@mcp.tool()
def what_if(circuit_id: str, change_description: str) -> str:
    """Qualitative what-if analysis: predict effects of a circuit change.

    Loads the circuit, searches knowledge base for relevant principles,
    and composes a qualitative analysis of expected effects.

    Args:
        circuit_id: Circuit to analyze
        change_description: Description of proposed change (e.g. "double R1 resistance")
    """
    db = get_db()
    cm = CircuitManager(db)
    schema = cm.get_schema(circuit_id)
    km = KnowledgeManager(db)

    # Search knowledge base for relevant principles
    search_terms = change_description.split()
    # Also include component types from the circuit
    comp_types = {c.type for c in schema.components}
    query = " ".join(search_terms[:5] + list(comp_types)[:3])
    articles = km.search(query)

    lines = [f"What-If Analysis: {change_description}", ""]
    lines.append(f"Circuit: {schema.name}")
    lines.append(
        f"Components: {', '.join(c.id + ' (' + c.type + ')' for c in schema.components)}"
    )
    lines.append("")

    # Compose qualitative analysis
    lines.append("## Analysis")
    if schema.design_intent and schema.design_intent.topology:
        lines.append(f"Topology: {schema.design_intent.topology}")

    # Provide relevant knowledge context
    if articles:
        lines.append("")
        lines.append("## Relevant Knowledge")
        for a in articles[:3]:
            lines.append(f"  - [{a['category']}] {a['title']}: {a['content'][:120]}...")
    else:
        lines.append("  No directly relevant knowledge articles found.")

    lines.append("")
    lines.append("## Expected Effects")
    lines.append(f"  Change: {change_description}")
    lines.append(
        f"  Affects circuit '{schema.name}' with {len(schema.components)} components."
    )
    lines.append(
        "  Use simulation tools (dc_operating_point, ac_analysis) to quantify the impact."
    )

    return "\n".join(lines)


@mcp.tool()
def check_design(circuit_id: str) -> str:
    """Check circuit simulation results against design intent targets.

    Loads latest simulation results and compares against target_specs
    defined in the circuit's design_intent.

    Args:
        circuit_id: Circuit to check
    """
    db = get_db()
    cm = CircuitManager(db)
    schema = cm.get_schema(circuit_id)

    # Load latest simulation results
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT analysis_type, results_json FROM simulation_results "
            "WHERE circuit_id = ? ORDER BY rowid DESC LIMIT 5",
            (circuit_id,),
        ).fetchall()

    if not rows:
        return f"No simulation results found for circuit '{circuit_id}'. Run a simulation first."

    lines = [f"Design Check: {schema.name}", ""]

    # Get target specs
    targets = {}
    if schema.design_intent and schema.design_intent.target_specs:
        targets = schema.design_intent.target_specs
        lines.append("## Target Specifications")
        for spec, val in targets.items():
            lines.append(f"  {spec}: {val}")
        lines.append("")

    # Build results summary
    lines.append("## Latest Simulation Results")
    all_results = {}
    for row in rows:
        analysis_type = row[0]
        results = json.loads(row[1])
        lines.append(f"  [{analysis_type}]")
        for key, val in results.items():
            if isinstance(val, (int, float)):
                lines.append(f"    {key}: {val:.4g}")
                all_results[key] = val
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, (int, float)):
                        lines.append(f"    {key}.{k}: {v:.4g}")
                        all_results[f"{key}.{k}"] = v

    # Compare against targets
    if targets:
        lines.append("")
        lines.append("## Pass/Fail Table")
        lines.append(f"  {'Spec':<25} {'Target':>12} {'Measured':>12} {'Status':>8}")
        lines.append(f"  {'-' * 25} {'-' * 12} {'-' * 12} {'-' * 8}")
        for spec, target in targets.items():
            measured = all_results.get(spec)
            if measured is not None:
                try:
                    target_val = (
                        float(target) if isinstance(target, str) else float(target)
                    )
                    # Pass if within 20% of target
                    ratio = measured / target_val if target_val != 0 else float("inf")
                    status = "PASS" if 0.8 <= ratio <= 1.2 else "FAIL"
                except (ValueError, TypeError):
                    status = "N/A"
                lines.append(
                    f"  {spec:<25} {str(target):>12} {measured:>12.4g} {status:>8}"
                )
            else:
                lines.append(
                    f"  {spec:<25} {str(target):>12} {'---':>12} {'MISSING':>8}"
                )
    else:
        lines.append("")
        lines.append("No target specifications defined in design_intent.")

    return "\n".join(lines)
