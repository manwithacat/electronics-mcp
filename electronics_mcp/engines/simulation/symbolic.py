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
