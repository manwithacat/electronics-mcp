"""Symbolic circuit analysis using lcapy."""
import warnings
from pathlib import Path

import sympy

from electronics_mcp.core.schema import CircuitSchema, ComponentBase
from electronics_mcp.core.units import parse_value


class SymbolicAnalyzer:
    """Symbolic circuit analyzer using lcapy for transfer functions, impedance, poles/zeros."""

    def _build_lcapy_circuit(self, schema: CircuitSchema):
        """Convert CircuitSchema to an lcapy Circuit.

        lcapy uses numeric node names; we map schema node names to integers.
        Node 0 is always ground.
        """
        from lcapy import Circuit

        circuit = Circuit()

        # Build node name -> integer mapping
        node_map = {schema.ground_node: 0}
        next_node = 1
        for comp in schema.components:
            for node in comp.nodes:
                if node not in node_map:
                    node_map[node] = next_node
                    next_node += 1

        # Add components
        for comp in schema.components:
            nodes = [str(node_map[n]) for n in comp.nodes]
            line = self._component_to_lcapy(comp, nodes)
            if line:
                circuit.add(line)

        return circuit, node_map

    def _lcapy_value(self, val: str) -> str:
        """Convert an EE value string to an lcapy-compatible value.

        If the value is numeric (with EE units), convert to a number.
        If symbolic (like 'R', 'C'), keep as-is.
        """
        try:
            numeric = parse_value(val)
            return f"{numeric:g}"
        except ValueError:
            # It's a symbolic name -- keep it
            return val

    def _component_to_lcapy(self, comp: ComponentBase, nodes: list[str]) -> str | None:
        """Convert a component to an lcapy netlist line."""
        n1, n2 = nodes[0], nodes[1]

        if comp.type == "resistor":
            val = self._lcapy_value(comp.parameters.get("resistance", "R"))
            return f"{comp.id} {n1} {n2} {{{val}}}"

        elif comp.type == "capacitor":
            val = self._lcapy_value(comp.parameters.get("capacitance", "C"))
            return f"{comp.id} {n1} {n2} {{{val}}}"

        elif comp.type == "inductor":
            val = self._lcapy_value(comp.parameters.get("inductance", "L"))
            return f"{comp.id} {n1} {n2} {{{val}}}"

        elif comp.type == "voltage_source":
            amp = self._lcapy_value(comp.parameters.get("amplitude",
                                    comp.parameters.get("voltage", "1")))
            return f"{comp.id} {n1} {n2} {{{amp}}}"

        elif comp.type == "current_source":
            val = self._lcapy_value(comp.parameters.get("current", "1"))
            return f"{comp.id} {n1} {n2} {{{val}}}"

        return None

    def transfer_function(
        self,
        schema: CircuitSchema,
        input_node: str,
        output_node: str,
    ) -> dict:
        """Compute symbolic transfer function H(s) = V(output)/V(input).

        Returns dict with 'latex', 'python_expr', and 'expression' keys.
        """
        circuit, node_map = self._build_lcapy_circuit(schema)

        in_node = node_map.get(input_node, 1)
        out_node = node_map.get(output_node, 2)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            H = circuit.transfer(in_node, 0, out_node, 0)

        expr = H.expr
        return {
            "latex": sympy.latex(expr),
            "python_expr": str(expr),
            "expression": str(H),
        }

    def impedance(
        self,
        schema: CircuitSchema,
        node1: str,
        node2: str,
    ) -> dict:
        """Compute symbolic impedance between two nodes.

        Returns dict with 'latex', 'expression' keys.
        """
        circuit, node_map = self._build_lcapy_circuit(schema)

        n1 = node_map.get(node1, 1)
        n2 = node_map.get(node2, 0)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            Z = circuit.impedance(n1, n2)

        expr = Z.expr
        return {
            "latex": sympy.latex(expr),
            "expression": str(Z),
        }

    def poles_and_zeros(
        self,
        schema: CircuitSchema,
        input_node: str,
        output_node: str,
        plot_dir: Path | None = None,
    ) -> dict:
        """Find poles and zeros of the transfer function.

        Returns dict with 'poles' and 'zeros' lists (symbolic expressions).
        """
        circuit, node_map = self._build_lcapy_circuit(schema)

        in_node = node_map.get(input_node, 1)
        out_node = node_map.get(output_node, 2)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            H = circuit.transfer(in_node, 0, out_node, 0)
            poles = H.poles()
            zeros = H.zeros()

        poles_list = [{"value": str(k), "multiplicity": int(float(str(v)))} for k, v in poles.items()]
        zeros_list = [{"value": str(k), "multiplicity": int(float(str(v)))} for k, v in zeros.items()]

        result = {
            "poles": poles_list,
            "zeros": zeros_list,
            "poles_latex": [sympy.latex(sympy.sympify(str(p["value"]))) for p in poles_list],
            "zeros_latex": [sympy.latex(sympy.sympify(str(z["value"]))) for z in zeros_list],
        }

        if plot_dir is not None:
            self._plot_pole_zero(poles_list, zeros_list, plot_dir / "pole_zero.png")
            result["plot_path"] = str(plot_dir / "pole_zero.png")

        return result

    def node_voltage(self, schema: CircuitSchema, node: str) -> dict:
        """Compute symbolic voltage at a node.

        Returns dict with 'latex', 'expression', 'python_expr' keys.
        """
        circuit, node_map = self._build_lcapy_circuit(schema)
        n = node_map.get(node, 1)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            V = circuit[n].V

        expr = V.expr
        return {
            "latex": sympy.latex(expr),
            "expression": str(V),
            "python_expr": str(expr),
        }

    def simplify(self, schema: CircuitSchema) -> dict:
        """Compute total load impedance seen by the source via series/parallel reduction.

        Builds passive-only circuit and computes equivalent impedance.
        Returns dict with 'simplified_expression', 'latex', 'description'.
        """
        from lcapy import Circuit

        # Build passive-only circuit (skip sources)
        node_map = {schema.ground_node: 0}
        next_node = 1
        for comp in schema.components:
            for node in comp.nodes:
                if node not in node_map:
                    node_map[node] = next_node
                    next_node += 1

        passive_cct = Circuit()
        source_node = None
        for comp in schema.components:
            if comp.type in ("voltage_source", "current_source"):
                # Track which node the source drives
                for n in comp.nodes:
                    if node_map[n] != 0:
                        source_node = node_map[n]
                continue
            nodes = [str(node_map[n]) for n in comp.nodes]
            line = self._component_to_lcapy(comp, nodes)
            if line:
                passive_cct.add(line)

        if source_node is None:
            source_node = 1

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            Z = passive_cct.impedance(source_node, 0)

        expr = Z.expr
        simplified = sympy.simplify(expr)
        return {
            "simplified_expression": str(simplified),
            "latex": sympy.latex(simplified),
            "description": f"Load impedance from node {source_node} to ground: {simplified}",
        }

    def step_response(
        self,
        schema: CircuitSchema,
        input_node: str,
        output_node: str,
        plot_dir: Path | None = None,
    ) -> dict:
        """Compute step response of the circuit.

        Gets H(s), computes inverse Laplace of H(s)/s for the step response.
        Returns dict with 'expression', 'latex', and optionally 'plot_path'.
        """
        circuit, node_map = self._build_lcapy_circuit(schema)

        in_node = node_map.get(input_node, 1)
        out_node = node_map.get(output_node, 2)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            H = circuit.transfer(in_node, 0, out_node, 0)
            # Step response: inverse Laplace of H(s)/s
            from lcapy import s as lcapy_s
            step = (H / lcapy_s).inverse_laplace(causal=True)

        expr = step.expr
        result = {
            "expression": str(step),
            "latex": sympy.latex(expr),
        }

        if plot_dir is not None:
            plot_dir = Path(plot_dir)
            plot_dir.mkdir(parents=True, exist_ok=True)
            plot_path = plot_dir / "step_response.png"
            self._plot_step_response(expr, plot_path)
            result["plot_path"] = str(plot_path)

        return result

    def _plot_step_response(self, expr, output_path):
        """Generate a step response plot."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(8, 5))

        # Try numeric evaluation
        t_sym = sympy.Symbol("t")
        free_syms = expr.free_symbols - {t_sym}

        if not free_syms:
            # Fully numeric -- plot directly
            f = sympy.lambdify(t_sym, expr, modules=["numpy"])
            t = np.linspace(0, 5, 500)
            try:
                y = np.real(f(t))
                ax.plot(t, y, "b-", linewidth=2)
            except Exception:
                ax.text(0.5, 0.5, str(expr), transform=ax.transAxes,
                        ha="center", fontsize=10)
        else:
            ax.text(0.5, 0.5, f"${sympy.latex(expr)}$", transform=ax.transAxes,
                    ha="center", fontsize=14)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Response")
        ax.set_title("Step Response")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150)
        plt.close(fig)

    def _plot_pole_zero(self, poles, zeros, output_path):
        """Generate a pole-zero plot."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 6))

        # Try to evaluate poles/zeros numerically for plotting
        for p in poles:
            try:
                val = complex(sympy.sympify(p["value"]))
                ax.plot(val.real, val.imag, "rx", markersize=12, markeredgewidth=2)
            except (TypeError, ValueError):
                pass

        for z in zeros:
            try:
                val = complex(sympy.sympify(z["value"]))
                ax.plot(val.real, val.imag, "bo", markersize=10, markeredgewidth=2,
                        fillstyle="none")
            except (TypeError, ValueError):
                pass

        ax.axhline(y=0, color="k", linewidth=0.5)
        ax.axvline(x=0, color="k", linewidth=0.5)
        ax.set_xlabel("Real")
        ax.set_ylabel("Imaginary")
        ax.set_title("Pole-Zero Plot")
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150)
        plt.close(fig)
