import numpy as np
from electronics_mcp.engines.rendering.plots import (
    draw_bode,
    draw_waveform,
    draw_phasor,
    draw_pole_zero,
)


class TestBodePlot:
    def test_generates_png(self, tmp_path):
        freq = np.logspace(0, 6, 500)
        # Simple RC low-pass: H = 1/(1 + j*f/fc), fc=1591 Hz
        fc = 1591
        magnitude_db = -10 * np.log10(1 + (freq / fc) ** 2)
        phase_deg = -np.degrees(np.arctan(freq / fc))

        path = draw_bode(
            freq,
            magnitude_db,
            phase_deg,
            title="RC Filter",
            output_path=tmp_path / "bode.png",
        )
        assert path.exists()
        assert path.stat().st_size > 1000  # Not empty


class TestWaveformPlot:
    def test_generates_png(self, tmp_path):
        time = np.linspace(0, 1e-3, 1000)
        voltage = 5 * (1 - np.exp(-time / (10e3 * 10e-9)))

        path = draw_waveform(
            time,
            voltage,
            title="Step Response",
            output_path=tmp_path / "wave.png",
            xlabel="Time (s)",
            ylabel="Voltage (V)",
        )
        assert path.exists()
        assert path.stat().st_size > 1000


class TestPhasorPlot:
    def test_generates_png(self, tmp_path):
        phasors = [
            {"label": "V1", "magnitude": 5.0, "angle_deg": 0},
            {"label": "V2", "magnitude": 3.0, "angle_deg": -45},
            {"label": "V3", "magnitude": 2.0, "angle_deg": 90},
        ]
        path = draw_phasor(
            phasors, title="Phasor Diagram", output_path=tmp_path / "phasor.png"
        )
        assert path.exists()
        assert path.stat().st_size > 1000


class TestPoleZeroPlot:
    def test_generates_png(self, tmp_path):
        poles = [{"real": -1000, "imag": 0}]
        zeros = []
        path = draw_pole_zero(
            poles, zeros, title="P-Z Plot", output_path=tmp_path / "pz.png"
        )
        assert path.exists()
        assert path.stat().st_size > 1000
