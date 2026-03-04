# Database Schema

ElectronicsMCP uses a project-scoped SQLite database at `data/ee.db`. The database is seeded on first initialization with component libraries, knowledge articles, and design rules.

## Tables

| Table | Purpose |
|-------|---------|
| `circuits` | Project circuit designs |
| `circuit_versions` | Immutable version snapshots |
| `subcircuits` | Reusable circuit blocks |
| `component_models` | SPICE models and parametric data |
| `component_categories` | Selection guides by type |
| `simulation_results` | Cached analysis results |
| `knowledge` | Articles, formulas, design rules |
| `knowledge_fts` | FTS5 full-text search index |
| `project_notes` | User and agent annotations |
| `design_decisions` | Recorded design rationale |
| `comparisons` | Circuit comparison setups |
| `provenance` | Source tracking for seed data |

See the implementation plan and source code for full CREATE TABLE statements.
