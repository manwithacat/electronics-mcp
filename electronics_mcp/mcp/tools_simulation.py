"""MCP tools for circuit simulation (numerical and symbolic)."""
import json
import uuid
from electronics_mcp.mcp.server import mcp, get_db, get_config
from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.engines.simulation.numerical import NumericalSimulator
from electronics_mcp.engines.simulation.symbolic import SymbolicAnalyzer


def _save_result(circuit_id: str, analysis_type: str, parameters: dict, results: dict, plots: list[str] | None = None) -> None:
    """Save simulation results to the database."""
    db = get_db()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO simulation_results (id, circuit_id, analysis_type, parameters, results_json, plots) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), circuit_id, analysis_type,
             json.dumps(parameters), json.dumps(results),
             json.dumps(plots) if plots else None),
        )


def _get_schema(circuit_id: str):
    cm = CircuitManager(get_db())
    return cm.get_schema(circuit_id)


@mcp.tool()
def dc_operating_point(circuit_id: str) -> str:
    """Run DC operating point analysis on a circuit.

    Returns node voltages and branch currents at the DC bias point.
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()
    result = sim.dc_operating_point(schema)
    _save_result(circuit_id, "dc_op", {}, result)

    lines = ["DC Operating Point Analysis:", ""]
    lines.append("Node Voltages:")
    for node, voltage in result.get("node_voltages", {}).items():
        lines.append(f"  {node}: {voltage:.4g} V")
    lines.append("")
    lines.append("Branch Currents:")
    for branch, current in result.get("branch_currents", {}).items():
        lines.append(f"  {branch}: {current:.4g} A")
    return "\n".join(lines)


@mcp.tool()
def dc_sweep(
    circuit_id: str,
    source_id: str,
    start: float,
    stop: float,
    step: float,
    output_node: str,
) -> str:
    """Sweep a DC source and plot output voltage vs input.

    Args:
        circuit_id: Circuit to simulate
        source_id: ID of the voltage/current source to sweep
        start: Start value in volts or amps
        stop: Stop value
        step: Step size
        output_node: Node to measure
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()
    config = get_config()
    plot_path = config.plots_dir / f"dc_sweep_{circuit_id[:8]}.png"

    result = sim.dc_sweep(schema, source_id, start, stop, step, output_node, plot_path)
    _save_result(circuit_id, "dc_sweep",
                 {"source": source_id, "start": start, "stop": stop, "step": step},
                 result, [str(plot_path)] if plot_path.exists() else None)

    lines = [f"DC Sweep: {source_id} from {start} to {stop}"]
    lines.append(f"Output node: {output_node}")
    if plot_path.exists():
        lines.append(f"Plot saved: {plot_path}")
    return "\n".join(lines)


@mcp.tool()
def ac_analysis(
    circuit_id: str,
    output_node: str,
    start_freq: float = 1.0,
    stop_freq: float = 1e6,
    points_per_decade: int = 100,
) -> str:
    """Run AC frequency response analysis (Bode plot).

    Returns gain/phase data and bandwidth if applicable.
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()
    config = get_config()
    plot_path = config.plots_dir / f"bode_{circuit_id[:8]}.png"

    result = sim.ac_analysis(schema, start_freq=start_freq, stop_freq=stop_freq,
                             points_per_decade=points_per_decade,
                             output_node=output_node, plot_dir=plot_path.parent)
    _save_result(circuit_id, "ac", {"output_node": output_node,
                 "start_freq": start_freq, "stop_freq": stop_freq},
                 result)

    lines = ["AC Analysis Results:", ""]
    if "bandwidth_hz" in result:
        lines.append(f"  -3dB Bandwidth: {result['bandwidth_hz']:.2f} Hz")
    if "dc_gain_db" in result:
        lines.append(f"  DC Gain: {result['dc_gain_db']:.2f} dB")
    if "bode_plot" in result:
        lines.append(f"  Bode plot: {result['bode_plot']}")
    return "\n".join(lines)


@mcp.tool()
def transient_analysis(
    circuit_id: str,
    stop_time: float,
    output_node: str,
    step_time: float | None = None,
) -> str:
    """Run time-domain transient simulation.

    Args:
        circuit_id: Circuit to simulate
        stop_time: Simulation duration in seconds
        output_node: Node to measure
        step_time: Maximum time step (auto if omitted)
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()
    config = get_config()
    plot_path = config.plots_dir / f"transient_{circuit_id[:8]}.png"

    if step_time is None:
        step_time = stop_time / 1000

    result = sim.transient_analysis(schema, duration=stop_time, step_size=step_time,
                                     output_node=output_node, plot_dir=plot_path.parent)
    _save_result(circuit_id, "transient",
                 {"stop_time": stop_time, "output_node": output_node},
                 result)

    lines = ["Transient Analysis Results:", ""]
    if "rise_time" in result:
        lines.append(f"  Rise time: {result['rise_time']:.4g} s")
    if "overshoot_pct" in result:
        lines.append(f"  Overshoot: {result['overshoot_pct']:.1f}%")
    if "waveform_plot" in result:
        lines.append(f"  Waveform: {result['waveform_plot']}")
    return "\n".join(lines)


@mcp.tool()
def parametric_sweep(
    circuit_id: str,
    component_id: str,
    parameter: str,
    values_json: str,
    analysis_type: str = "ac",
    output_node: str = "output",
) -> str:
    """Sweep a component parameter across multiple values and compare results.

    Args:
        circuit_id: Circuit to simulate
        component_id: Component to vary (e.g. "R1")
        parameter: Parameter name (e.g. "resistance")
        values_json: JSON array of values to sweep (e.g. '["1k", "10k", "100k"]')
        analysis_type: Type of analysis ("ac" or "dc_op")
        output_node: Node to measure
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()
    values = json.loads(values_json)

    result = sim.parametric_sweep(schema, component_id, parameter,
                                  values, analysis_type, output_node)
    _save_result(circuit_id, "parametric",
                 {"component": component_id, "parameter": parameter, "values": values},
                 result)

    lines = [f"Parametric Sweep: {component_id}.{parameter}", ""]
    for sweep in result.get("sweeps", []):
        lines.append(f"  {parameter}={sweep['value']}:")
        if "bandwidth_hz" in sweep.get("result", {}):
            lines.append(f"    Bandwidth: {sweep['result']['bandwidth_hz']:.2f} Hz")
    return "\n".join(lines)


@mcp.tool()
def monte_carlo(
    circuit_id: str,
    num_runs: int = 100,
    tolerance: float = 0.05,
    analysis_type: str = "ac",
    output_node: str = "output",
) -> str:
    """Run Monte Carlo analysis with component tolerance variations.

    Args:
        circuit_id: Circuit to simulate
        num_runs: Number of random trials
        tolerance: Component tolerance (0.05 = 5%)
        analysis_type: Type of analysis ("ac" or "dc_op")
        output_node: Node to measure
    """
    schema = _get_schema(circuit_id)
    sim = NumericalSimulator()

    result = sim.monte_carlo(schema, num_runs, tolerance, analysis_type, output_node)
    _save_result(circuit_id, "monte_carlo",
                 {"num_runs": num_runs, "tolerance": tolerance},
                 result)

    lines = [f"Monte Carlo Analysis ({num_runs} runs, {tolerance*100:.0f}% tolerance):", ""]
    stats = result.get("statistics", {})
    for metric, values in stats.items():
        lines.append(f"  {metric}:")
        lines.append(f"    Mean: {values.get('mean', 'N/A')}")
        lines.append(f"    Std:  {values.get('std', 'N/A')}")
        lines.append(f"    Min:  {values.get('min', 'N/A')}")
        lines.append(f"    Max:  {values.get('max', 'N/A')}")
    return "\n".join(lines)


@mcp.tool()
def transfer_function(
    circuit_id: str,
    input_node: str,
    output_node: str,
) -> str:
    """Compute symbolic transfer function H(s) = Vout/Vin.

    Returns LaTeX expression and Python-evaluable form.
    """
    schema = _get_schema(circuit_id)
    analyzer = SymbolicAnalyzer()
    result = analyzer.transfer_function(schema, input_node, output_node)

    lines = ["Transfer Function H(s):", ""]
    lines.append(f"  Expression: {result.get('expression', 'N/A')}")
    lines.append(f"  LaTeX: {result.get('latex', 'N/A')}")
    if "python_expr" in result:
        lines.append(f"  Python: {result['python_expr']}")
    return "\n".join(lines)


@mcp.tool()
def impedance(
    circuit_id: str,
    node1: str,
    node2: str,
) -> str:
    """Compute symbolic impedance between two nodes.

    Returns impedance as a function of frequency (s or omega).
    """
    schema = _get_schema(circuit_id)
    analyzer = SymbolicAnalyzer()
    result = analyzer.impedance(schema, node1, node2)

    lines = ["Impedance:", ""]
    lines.append(f"  Expression: {result.get('expression', 'N/A')}")
    lines.append(f"  LaTeX: {result.get('latex', 'N/A')}")
    return "\n".join(lines)


@mcp.tool()
def poles_and_zeros(
    circuit_id: str,
    input_node: str,
    output_node: str,
) -> str:
    """Find poles and zeros of a circuit's transfer function.

    Returns pole/zero locations with multiplicities and a pole-zero plot.
    """
    schema = _get_schema(circuit_id)
    analyzer = SymbolicAnalyzer()
    config = get_config()
    plot_path = config.plots_dir / f"pz_{circuit_id[:8]}.png"

    result = analyzer.poles_and_zeros(schema, input_node, output_node, plot_dir=plot_path.parent)
    _save_result(circuit_id, "poles_zeros",
                 {"input_node": input_node, "output_node": output_node},
                 result)

    lines = ["Poles and Zeros:", ""]
    lines.append("Poles:")
    for p in result.get("poles", []):
        lines.append(f"  {p['value']} (multiplicity {p['multiplicity']})")
    lines.append("Zeros:")
    for z in result.get("zeros", []):
        lines.append(f"  {z['value']} (multiplicity {z['multiplicity']})")
    if "pz_plot" in result:
        lines.append(f"Plot: {result['pz_plot']}")
    return "\n".join(lines)
