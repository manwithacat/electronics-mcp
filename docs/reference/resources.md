# MCP Resources Reference

Resources provide retrievable context that the LLM can pull into its working context on demand, without a tool call that returns computed results.

## Resource URI Schemes

| URI | Description |
|-----|-------------|
| `electronics://topologies/{name}` | Reference material for standard topologies |
| `electronics://components/{type}` | Component reference (characteristics, selection criteria) |
| `electronics://design-rules/{domain}` | Design heuristics (e.g., `power` -> thermal management) |
| `electronics://formulas/{topic}` | Key formulas with derivations |
| `electronics://safety/{topic}` | Safety guidance (mains isolation, ESD, battery handling) |
| `electronics://standards/{name}` | Relevant standards references |

## Examples

### Topology Reference

```
electronics://topologies/buck_converter
```

Returns a structured article covering:

- Circuit description and operating principle
- Key design equations
- Component selection guidance
- Typical performance characteristics
- Common pitfalls and design rules
- Links to related subcircuit definitions

### Component Reference

```
electronics://components/mosfet
```

Returns:

- What MOSFETs are and how they work
- Key parameters (Vgs(th), Rds(on), gate charge)
- Selection criteria for common applications
- Available models in the component library

### Design Rules

```
electronics://design-rules/decoupling
```

Returns the design rule article on decoupling strategy:

- 100nF ceramic per IC power pin
- Bulk capacitors on power rails
- Placement guidelines
- Frequency considerations

## How Resources Work

Resources are backed by queries against the knowledge base tables in the SQLite database. They provide a structured alternative to the `search_knowledge` tool for when the LLM knows what category of information it needs.

The LLM client (e.g., Claude Code) can pull these into context automatically when it determines they're relevant to the conversation.
