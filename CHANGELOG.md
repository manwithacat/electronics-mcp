# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-06

### Added
- Symbolic engine: `node_voltage`, `simplify`, `step_response` methods
- MCP tools: `node_voltage_expression`, `simplify_network`, `step_response`, `what_if`, `check_design`
- Web UI: parameter explorer wired to real simulation engine
- Web UI: waveform viewer data normalization (transient + AC)
- Web UI: circuit comparison overlay rendering with Plotly
- Web UI: component search page with parametric filtering
- 50 subcircuits (passive, filter, protection, amplifier, power, oscillator, digital, misc)
- 30 design rules covering PCB layout, thermal, EMI, signal integrity
- 29 formula sets (75 individual formulas) across all EE domains
- Provenance tracking module with `record_provenance` / `record_bulk_provenance`
- Provenance wired into all ingestion pipelines
- QA-based seed SQL filtering (exclude failed records)
- CLI wrappers: `cli_kuphaldt`, `cli_spice`, `cli_kicad`
- `/bump` and `/ship` slash commands for versioning and releases

## [0.1.0] - 2026-03-05

### Added
- Core: database, schema models, circuit manager, unit parser
- Engines: numerical simulation, symbolic analysis, rendering, fabrication, knowledge
- MCP server with 20+ tools for circuit design, simulation, and knowledge
- Ingestion pipelines: Kuphaldt parser, SPICE model importer, KiCad symbol importer
- Web UI with Dazzle-based views for circuits, knowledge, components
- QA pipeline with formula evaluation, schema validation, content checks
- Seed data generation with QA filtering
- 204 tests passing
