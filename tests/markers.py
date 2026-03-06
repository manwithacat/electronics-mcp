"""Shared test markers for conditional skipping."""

import pytest


def _ngspice_works() -> bool:
    """Check if PySpice can load and use the ngspice shared library."""
    try:
        from PySpice.Spice.NgSpice.Shared import NgSpiceShared

        ngspice = NgSpiceShared.new_instance()
        return ngspice is not None
    except Exception:
        return False


requires_ngspice = pytest.mark.skipif(
    not _ngspice_works(), reason="ngspice shared library not available or incompatible"
)
