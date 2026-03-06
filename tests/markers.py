"""Shared test markers for conditional skipping."""

import pytest


def _ngspice_works() -> bool:
    """Check if PySpice can actually run simulations (not just load the library).

    On Ubuntu Noble, ngspice 42 loads fine but fails at simulation time
    with 'Unsupported Ngspice version 42'. We must attempt a real simulation.
    """
    try:
        import warnings

        from PySpice.Spice.Netlist import Circuit

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            ckt = Circuit("marker_probe")
            ckt.V(1, "probe_node", ckt.gnd, "DC 1V")
            ckt.R(1, "probe_node", ckt.gnd, "1k")
            sim = ckt.simulator()
            sim.operating_point()
        return True
    except Exception:
        return False


requires_ngspice = pytest.mark.skipif(
    not _ngspice_works(), reason="ngspice shared library not available or incompatible"
)
