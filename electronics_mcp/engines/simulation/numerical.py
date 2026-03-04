"""Numerical circuit simulation using PySpice/Ngspice."""
import random
import warnings
from pathlib import Path

import numpy as np

from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.core.units import parse_value


class NumericalSimulator:
    """SPICE-based numerical circuit simulator."""

    def _build_circuit(self, schema: CircuitSchema):
        """Convert a CircuitSchema to a PySpice Circuit object."""
        from PySpice.Spice.Netlist import Circuit

        circuit = Circuit(schema.name)

        for comp in schema.components:
            nodes = [str(circuit.gnd) if n == schema.ground_node else n
                     for n in comp.nodes]
            self._add_component(circuit, comp, nodes)

        return circuit

    def _add_component(self, circuit, comp: ComponentBase, nodes: list[str]):
        """Add a single component to the PySpice circuit."""
        # Strip common prefixes from ID to get suffix for PySpice naming
        suffix = comp.id.lstrip("RCLVIQMD")
        if not suffix:
            suffix = comp.id

        if comp.type == "resistor":
            val = parse_value(comp.parameters.get("resistance", "1k"))
            circuit.R(suffix, nodes[0], nodes[1], val)

        elif comp.type == "capacitor":
            val = parse_value(comp.parameters.get("capacitance", "1n"))
            circuit.C(suffix, nodes[0], nodes[1], val)

        elif comp.type == "inductor":
            val = parse_value(comp.parameters.get("inductance", "1u"))
            circuit.L(suffix, nodes[0], nodes[1], val)

        elif comp.type == "voltage_source":
            if comp.subtype == "dc":
                voltage = parse_value(comp.parameters.get("voltage", "0"))
                circuit.V(suffix, nodes[0], nodes[1], voltage)
            elif comp.subtype == "ac":
                amp = parse_value(comp.parameters.get("amplitude", "1"))
                offset = parse_value(comp.parameters.get("offset", "0"))
                circuit.V(suffix, nodes[0], nodes[1], f"DC {offset} AC {amp}")
            elif comp.subtype == "pulse":
                v1 = parse_value(comp.parameters.get("v1", "0"))
                v2 = parse_value(comp.parameters.get("v2", "5"))
                rise = parse_value(comp.parameters.get("rise_time", "1e-9"))
                pw = parse_value(comp.parameters.get("pulse_width", "0.01"))
                period = pw * 2
                circuit.PulseVoltageSource(
                    suffix, nodes[0], nodes[1],
                    initial_value=v1, pulsed_value=v2,
                    delay_time=0, rise_time=rise, fall_time=rise,
                    pulse_width=pw, period=period,
                )
            else:
                voltage = parse_value(comp.parameters.get("voltage", "0"))
                circuit.V(suffix, nodes[0], nodes[1], voltage)

        elif comp.type == "current_source":
            val = parse_value(comp.parameters.get("current", "1e-3"))
            circuit.I(suffix, nodes[0], nodes[1], val)

        elif comp.type == "diode":
            circuit.D(suffix, nodes[0], nodes[1], model="DDefault")

    def dc_operating_point(self, schema: CircuitSchema) -> dict:
        """Run DC operating point analysis.

        Returns dict with 'node_voltages' mapping node names to DC voltages.
        """
        circuit = self._build_circuit(schema)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            simulator = circuit.simulator()
            analysis = simulator.operating_point()

        node_voltages = {}
        for name in analysis.nodes:
            if name != str(circuit.gnd):
                node_voltages[str(name)] = float(analysis.nodes[name])

        return {"node_voltages": node_voltages}

    def ac_analysis(
        self,
        schema: CircuitSchema,
        start_freq: float = 1,
        stop_freq: float = 1e6,
        points_per_decade: int = 100,
        output_node: str = "output",
        plot_dir: Path | None = None,
    ) -> dict:
        """Run AC frequency sweep analysis.

        Returns dict with frequency/magnitude/phase arrays and derived metrics.
        """
        circuit = self._build_circuit(schema)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            simulator = circuit.simulator()
            analysis = simulator.ac(
                start_frequency=start_freq,
                stop_frequency=stop_freq,
                number_of_points=points_per_decade,
                variation="dec",
            )

        frequency = np.array(analysis.frequency, dtype=float)
        output = np.array(analysis.nodes[output_node], dtype=complex)
        magnitude_db = 20 * np.log10(np.abs(output) + 1e-30)
        phase_deg = np.degrees(np.angle(output))

        # Find -3dB bandwidth
        max_db = np.max(magnitude_db)
        cutoff_mask = magnitude_db <= (max_db - 3.0)
        bandwidth_hz = None
        if np.any(cutoff_mask):
            # First frequency where gain drops below -3dB
            idx = np.argmax(cutoff_mask)
            if idx > 0:
                bandwidth_hz = float(frequency[idx])

        result = {
            "frequency": frequency.tolist(),
            "magnitude_db": magnitude_db.tolist(),
            "phase_deg": phase_deg.tolist(),
            "max_gain_db": float(max_db),
        }

        if bandwidth_hz is not None:
            result["bandwidth_hz"] = bandwidth_hz

        # Generate plot if directory provided
        if plot_dir is not None:
            self._plot_bode(frequency, magnitude_db, phase_deg,
                            schema.name, plot_dir / "bode.png")
            result["plot_path"] = str(plot_dir / "bode.png")

        return result

    def transient_analysis(
        self,
        schema: CircuitSchema,
        duration: float = 1e-3,
        step_size: float = 1e-6,
        output_node: str = "output",
        plot_dir: Path | None = None,
    ) -> dict:
        """Run transient time-domain analysis.

        Returns dict with time/voltage arrays and derived metrics.
        """
        circuit = self._build_circuit(schema)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            simulator = circuit.simulator()
            analysis = simulator.transient(
                step_time=step_size,
                end_time=duration,
            )

        time = np.array(analysis.time, dtype=float)
        output = np.array(analysis.nodes[output_node], dtype=float)

        # Compute metrics
        final_value = float(output[-1]) if len(output) > 0 else 0.0
        max_value = float(np.max(output))
        min_value = float(np.min(output))

        result = {
            "time": time.tolist(),
            "voltage": output.tolist(),
            "final_value": final_value,
            "max_value": max_value,
            "min_value": min_value,
        }

        # Rise time (10% to 90% of final value)
        if final_value > 0:
            low_thresh = 0.1 * final_value
            high_thresh = 0.9 * final_value
            low_times = time[output >= low_thresh]
            high_times = time[output >= high_thresh]
            if len(low_times) > 0 and len(high_times) > 0:
                result["rise_time"] = float(high_times[0] - low_times[0])

        # Overshoot
        if final_value > 0 and max_value > final_value:
            result["overshoot_pct"] = float((max_value - final_value) / final_value * 100)

        # Generate plot
        if plot_dir is not None:
            self._plot_transient(time, output, schema.name, plot_dir / "transient.png")
            result["plot_path"] = str(plot_dir / "transient.png")

        return result

    def _plot_bode(self, freq, mag_db, phase_deg, title, output_path):
        """Generate a Bode plot."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

        ax1.semilogx(freq, mag_db)
        ax1.set_ylabel("Magnitude (dB)")
        ax1.set_title(f"Bode Plot: {title}")
        ax1.grid(True, which="both", ls="-", alpha=0.3)
        ax1.axhline(y=-3, color="r", linestyle="--", alpha=0.5, label="-3dB")
        ax1.legend()

        ax2.semilogx(freq, phase_deg)
        ax2.set_ylabel("Phase (degrees)")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.grid(True, which="both", ls="-", alpha=0.3)

        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150)
        plt.close(fig)

    def _plot_transient(self, time, voltage, title, output_path):
        """Generate a transient response plot."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(time * 1e3, voltage)
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"Transient Response: {title}")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150)
        plt.close(fig)

    def dc_sweep(
        self,
        schema: CircuitSchema,
        source_id: str,
        start: float,
        stop: float,
        step: float,
        output_node: str = "output",
        plot_dir: Path | None = None,
    ) -> dict:
        """Sweep a DC source across a range and measure output.

        Returns dict with sweep_values and output_values arrays.
        """
        circuit = self._build_circuit(schema)

        # Find the source name in PySpice format
        suffix = source_id.lstrip("V")
        if not suffix:
            suffix = source_id

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            simulator = circuit.simulator()
            analysis = simulator.dc(**{f"V{suffix}": slice(start, stop, step)})

        sweep_values = np.array(analysis.nodes[f"v-sweep"], dtype=float) if hasattr(analysis, 'sweep') else np.arange(start, stop + step, step)
        output_values = np.array(analysis.nodes[output_node], dtype=float)

        # Handle the sweep values from the analysis
        try:
            sweep_values = np.array(analysis.sweep, dtype=float)
        except Exception:
            sweep_values = np.arange(start, stop + step / 2, step)

        result = {
            "sweep_values": sweep_values.tolist(),
            "output_values": output_values.tolist(),
        }

        if plot_dir is not None:
            self._plot_dc_sweep(sweep_values, output_values,
                                source_id, schema.name, plot_dir / "dc_sweep.png")
            result["plot_path"] = str(plot_dir / "dc_sweep.png")

        return result

    def parametric_sweep(
        self,
        schema: CircuitSchema,
        component_id: str,
        parameter: str,
        values: list[str],
        analysis_type: str = "ac",
        analysis_params: dict | None = None,
        plot_dir: Path | None = None,
    ) -> dict:
        """Run multiple analyses while sweeping a component parameter.

        Returns dict with 'sweeps' list, one entry per parameter value.
        """
        analysis_params = analysis_params or {}
        sweeps = []

        for val in values:
            # Create modified schema with new parameter value
            modified = schema.model_copy(deep=True)
            for comp in modified.components:
                if comp.id == component_id:
                    comp.parameters[parameter] = val
                    break

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                if analysis_type == "ac":
                    result = self.ac_analysis(
                        modified,
                        start_freq=analysis_params.get("start_freq", 1),
                        stop_freq=analysis_params.get("stop_freq", 1e6),
                        points_per_decade=analysis_params.get("points_per_decade", 100),
                        output_node=analysis_params.get("output_node", "output"),
                    )
                elif analysis_type == "dc":
                    result = self.dc_operating_point(modified)
                else:
                    result = self.dc_operating_point(modified)

            result["parameter_value"] = val
            sweeps.append(result)

        return {"sweeps": sweeps}

    def monte_carlo(
        self,
        schema: CircuitSchema,
        num_runs: int = 10,
        tolerance_pct: float = 5.0,
        analysis_type: str = "ac",
        analysis_params: dict | None = None,
        plot_dir: Path | None = None,
        seed: int | None = None,
    ) -> dict:
        """Run Monte Carlo analysis with random component tolerances.

        Varies passive component values by +-tolerance_pct% using Gaussian distribution.
        """
        analysis_params = analysis_params or {}
        if seed is not None:
            random.seed(seed)

        passive_types = {"resistor", "capacitor", "inductor"}
        param_keys = {"resistor": "resistance", "capacitor": "capacitance",
                       "inductor": "inductance"}

        runs = []
        bandwidth_values = []

        for i in range(num_runs):
            modified = schema.model_copy(deep=True)

            # Apply random tolerance to passive components
            for comp in modified.components:
                if comp.type in passive_types:
                    key = param_keys.get(comp.type)
                    if key and key in comp.parameters:
                        nominal = parse_value(comp.parameters[key])
                        # Gaussian with 1-sigma = tolerance/3 (99.7% within tolerance)
                        factor = 1 + random.gauss(0, tolerance_pct / 300)
                        varied = nominal * factor
                        comp.parameters[key] = f"{varied:g}"

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                if analysis_type == "ac":
                    result = self.ac_analysis(
                        modified,
                        start_freq=analysis_params.get("start_freq", 1),
                        stop_freq=analysis_params.get("stop_freq", 1e6),
                        points_per_decade=analysis_params.get("points_per_decade", 100),
                        output_node=analysis_params.get("output_node", "output"),
                    )
                    if "bandwidth_hz" in result:
                        bandwidth_values.append(result["bandwidth_hz"])
                else:
                    result = self.dc_operating_point(modified)

            result["run"] = i + 1
            # Remove bulky arrays for summary
            result.pop("frequency", None)
            result.pop("magnitude_db", None)
            result.pop("phase_deg", None)
            runs.append(result)

        # Compute statistics
        statistics = {}
        if bandwidth_values:
            statistics["bandwidth_hz"] = {
                "mean": float(np.mean(bandwidth_values)),
                "std": float(np.std(bandwidth_values)),
                "min": float(np.min(bandwidth_values)),
                "max": float(np.max(bandwidth_values)),
            }

        return {"runs": runs, "statistics": statistics}

    def _plot_dc_sweep(self, sweep, output, source_id, title, output_path):
        """Generate a DC sweep plot."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sweep, output)
        ax.set_xlabel(f"{source_id} (V)")
        ax.set_ylabel("Output (V)")
        ax.set_title(f"DC Sweep: {title}")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150)
        plt.close(fig)
