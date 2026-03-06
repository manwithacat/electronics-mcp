"""MCP tools for rendering schematics, plots, and reports."""

from electronics_mcp.mcp.server import mcp, get_db, get_config
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.engines.rendering.schematic import SchematicRenderer
from electronics_mcp.engines.rendering.plots import (
    draw_bode,
    draw_waveform,
    draw_phasor,
    draw_pole_zero,
)
from electronics_mcp.engines.rendering.reports import generate_markdown, generate_pdf


def _get_schema(circuit_id: str):
    cm = CircuitManager(get_db())
    return cm.get_schema(circuit_id)


@mcp.tool()
def draw_schematic(circuit_id: str) -> str:
    """Generate an SVG schematic diagram of a circuit.

    Returns the file path of the generated SVG.
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    output_path = config.schematics_dir / f"{circuit_id[:8]}_schematic.svg"

    renderer = SchematicRenderer()
    path = renderer.render(schema, output_path)
    return f"Schematic saved: {path}"


@mcp.tool()
def render_bode(
    circuit_id: str,
    frequencies_json: str,
    magnitude_db_json: str,
    phase_deg_json: str,
) -> str:
    """Draw a Bode plot from frequency response data.

    Args:
        circuit_id: Circuit ID for naming
        frequencies_json: JSON array of frequency values in Hz
        magnitude_db_json: JSON array of magnitude values in dB
        phase_deg_json: JSON array of phase values in degrees
    """
    import json

    config = get_config()
    output_path = config.plots_dir / f"bode_{circuit_id[:8]}.png"

    freqs = json.loads(frequencies_json)
    mag = json.loads(magnitude_db_json)
    phase = json.loads(phase_deg_json)

    path = draw_bode(freqs, mag, phase, output_path)
    return f"Bode plot saved: {path}"


@mcp.tool()
def render_waveform(
    circuit_id: str,
    time_json: str,
    signals_json: str,
    title: str = "Transient Response",
) -> str:
    """Draw a time-domain waveform plot.

    Args:
        circuit_id: Circuit ID for naming
        time_json: JSON array of time values in seconds
        signals_json: JSON object mapping signal names to value arrays
        title: Plot title
    """
    import json

    config = get_config()
    output_path = config.plots_dir / f"waveform_{circuit_id[:8]}.png"

    import numpy as np

    time_data = np.array(json.loads(time_json))
    signals = json.loads(signals_json)

    # draw_waveform takes a single voltage array; plot first signal
    first_signal = list(signals.values())[0]
    voltage = np.array(first_signal)

    path = draw_waveform(time_data, voltage, title, output_path)
    return f"Waveform plot saved: {path}"


@mcp.tool()
def render_phasor(
    circuit_id: str,
    phasors_json: str,
) -> str:
    """Draw a phasor diagram.

    Args:
        circuit_id: Circuit ID for naming
        phasors_json: JSON object mapping names to {magnitude, angle_deg}
    """
    import json

    config = get_config()
    output_path = config.plots_dir / f"phasor_{circuit_id[:8]}.png"

    phasors = json.loads(phasors_json)

    path = draw_phasor(phasors, output_path)
    return f"Phasor diagram saved: {path}"


@mcp.tool()
def render_pole_zero(
    circuit_id: str,
    poles_json: str,
    zeros_json: str,
) -> str:
    """Draw a pole-zero plot.

    Args:
        circuit_id: Circuit ID for naming
        poles_json: JSON array of [real, imag] pairs for poles
        zeros_json: JSON array of [real, imag] pairs for zeros
    """
    import json

    config = get_config()
    output_path = config.plots_dir / f"pz_{circuit_id[:8]}.png"

    poles = json.loads(poles_json)
    zeros = json.loads(zeros_json)

    path = draw_pole_zero(poles, zeros, output_path)
    return f"Pole-zero plot saved: {path}"


@mcp.tool()
def generate_circuit_report(circuit_id: str, notes: str = "") -> str:
    """Generate a Markdown report for a circuit including components and simulation results.

    Args:
        circuit_id: Circuit to report on
        notes: Additional notes to include
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    cm = CircuitManager(get_db())
    output_path = config.output_dir / f"report_{circuit_id[:8]}.md"

    # Gather simulation results
    sim_results = []
    with get_db().connect() as conn:
        rows = conn.execute(
            "SELECT analysis_type, parameters, results_json "
            "FROM simulation_results WHERE circuit_id = ? "
            "ORDER BY created_at DESC LIMIT 10",
            (circuit_id,),
        ).fetchall()
        for row in rows:
            import json

            sim_results.append(
                {
                    "analysis_type": row["analysis_type"],
                    "parameters": json.loads(row["parameters"]),
                    "results": json.loads(row["results_json"]),
                }
            )

    validation_warnings = cm.validate(circuit_id)

    path = generate_markdown(
        schema,
        output_path,
        title=schema.name,
        simulation_results=sim_results,
        validation_warnings=validation_warnings,
        notes=[notes] if notes else None,
    )
    return f"Report saved: {path}"


@mcp.tool()
def generate_circuit_pdf(circuit_id: str, notes: str = "") -> str:
    """Generate a PDF report for a circuit.

    Args:
        circuit_id: Circuit to report on
        notes: Additional notes to include
    """
    schema = _get_schema(circuit_id)
    config = get_config()
    cm = CircuitManager(get_db())
    output_path = config.output_dir / f"report_{circuit_id[:8]}.pdf"

    sim_results = []
    with get_db().connect() as conn:
        rows = conn.execute(
            "SELECT analysis_type, parameters, results_json "
            "FROM simulation_results WHERE circuit_id = ? "
            "ORDER BY created_at DESC LIMIT 10",
            (circuit_id,),
        ).fetchall()
        for row in rows:
            import json

            sim_results.append(
                {
                    "analysis_type": row["analysis_type"],
                    "parameters": json.loads(row["parameters"]),
                    "results": json.loads(row["results_json"]),
                }
            )

    validation_warnings = cm.validate(circuit_id)

    # Generate markdown first, then convert to PDF
    md_path = config.output_dir / f"report_{circuit_id[:8]}.md"
    generate_markdown(
        schema,
        md_path,
        title=schema.name,
        simulation_results=sim_results,
        validation_warnings=validation_warnings,
        notes=[notes] if notes else None,
    )
    path = generate_pdf(md_path, output_path)
    return f"PDF report saved: {path}"
