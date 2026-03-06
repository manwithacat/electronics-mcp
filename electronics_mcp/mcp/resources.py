"""MCP resource URIs for electronics knowledge."""

import json
from electronics_mcp.mcp.server import mcp, get_db
from electronics_mcp.engines.knowledge.manager import KnowledgeManager


@mcp.resource("electronics://topologies/{name}")
def get_topology_resource(name: str) -> str:
    """Reference material for standard circuit topologies."""
    km = KnowledgeManager(get_db())
    article = km.get_topic(name)
    if not article:
        return json.dumps({"error": f"Topology '{name}' not found"})
    return json.dumps(article, default=str)


@mcp.resource("electronics://components/{component_type}")
def get_component_resource(component_type: str) -> str:
    """Component selection guides and specifications."""
    km = KnowledgeManager(get_db())
    info = km.component_info(component_type)
    return json.dumps(info, default=str)


@mcp.resource("electronics://formulas/{topic}")
def get_formulas_resource(topic: str) -> str:
    """Formulas and equations for a topic."""
    km = KnowledgeManager(get_db())
    formulas = km.get_formulas(topic)
    return json.dumps({"topic": topic, "formulas": formulas}, default=str)


@mcp.resource("electronics://design-rules/{category}")
def get_design_rules_resource(category: str) -> str:
    """Design rules and guidelines by category."""
    km = KnowledgeManager(get_db())
    results = km.search(category, category="design_rule")
    return json.dumps({"category": category, "rules": results}, default=str)


@mcp.resource("electronics://knowledge/{topic}")
def get_knowledge_resource(topic: str) -> str:
    """General knowledge base article."""
    km = KnowledgeManager(get_db())
    article = km.get_topic(topic)
    if not article:
        return json.dumps({"error": f"Topic '{topic}' not found"})
    return json.dumps(article, default=str)


@mcp.resource("electronics://standards/{standard}")
def get_standards_resource(standard: str) -> str:
    """Reference to electronics standards and specifications."""
    km = KnowledgeManager(get_db())
    results = km.search(standard, category="standard")
    return json.dumps({"standard": standard, "results": results}, default=str)
