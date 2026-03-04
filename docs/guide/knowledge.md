# Knowledge Base

The knowledge engine provides searchable articles, formulas, design rules, and component data sourced from openly licensed corpora.

## Searching Knowledge

Full-text search across all knowledge articles:

```
search_knowledge(query="low pass filter design")
```

Returns ranked results with titles, summaries, and relevance scores.

## Knowledge Categories

| Category | Content | Source |
|----------|---------|--------|
| Articles | ~185 tutorial articles on EE fundamentals | Kuphaldt "Lessons in Electric Circuits" |
| Formulas | ~80 standard EE formulas with derivations | Kuphaldt + authored |
| Design Rules | ~30 practical design guidelines | Authored |
| Component Models | ~50 SPICE models with parameters | Ngspice bundled models |

## Topology Explanation

Get a detailed explanation of a circuit's topology and operating principles:

```
explain_topology(circuit_id=1)
```

Analyses the circuit structure, identifies the topology (e.g., "inverting amplifier", "common-emitter stage"), and explains how it works.

## Design Guides

Access structured design guides for common circuit types:

```
get_design_guide(topic="active_filter")
```

Design guides include component selection criteria, typical values, layout considerations, and common pitfalls.

## Formula Lookup

Search for specific formulas:

```
search_knowledge(query="voltage divider formula", category="formula")
```

Returns the formula with variable definitions, units, and usage context.

## Component Selection

Browse components by category with parametric filtering:

```
search_components(type="opamp", constraints={
    "gbw_min": 1e6,
    "supply_voltage": 5
})
```

Each component includes SPICE model parameters, typical application notes, and pin definitions.
