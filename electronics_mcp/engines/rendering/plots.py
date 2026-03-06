"""Plot generation functions for simulation results."""

from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def draw_bode(
    frequency: np.ndarray,
    magnitude_db: np.ndarray,
    phase_deg: np.ndarray,
    title: str = "Bode Plot",
    output_path: Path | str = "bode.png",
) -> Path:
    """Generate a Bode plot (magnitude + phase vs frequency)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    ax1.semilogx(frequency, magnitude_db, "b-", linewidth=1.5)
    ax1.set_ylabel("Magnitude (dB)")
    ax1.set_title(title)
    ax1.grid(True, which="both", ls="-", alpha=0.3)
    ax1.axhline(y=-3, color="r", linestyle="--", alpha=0.5, label="-3dB")
    ax1.legend()

    ax2.semilogx(frequency, phase_deg, "r-", linewidth=1.5)
    ax2.set_ylabel("Phase (degrees)")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.grid(True, which="both", ls="-", alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path


def draw_waveform(
    time: np.ndarray,
    voltage: np.ndarray,
    title: str = "Waveform",
    output_path: Path | str = "waveform.png",
    xlabel: str = "Time (s)",
    ylabel: str = "Voltage (V)",
) -> Path:
    """Generate a time-domain waveform plot."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time, voltage, "b-", linewidth=1.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path


def draw_phasor(
    phasors: list[dict],
    title: str = "Phasor Diagram",
    output_path: Path | str = "phasor.png",
) -> Path:
    """Generate a phasor diagram.

    Each phasor dict: {'label': str, 'magnitude': float, 'angle_deg': float}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": "polar"})

    colors = plt.cm.tab10(np.linspace(0, 1, max(len(phasors), 1)))
    for i, p in enumerate(phasors):
        angle_rad = np.radians(p["angle_deg"])
        ax.annotate(
            "",
            xy=(angle_rad, p["magnitude"]),
            xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color=colors[i], lw=2),
        )
        ax.text(
            angle_rad,
            p["magnitude"] * 1.1,
            p["label"],
            ha="center",
            fontsize=9,
            color=colors[i],
        )

    ax.set_title(title, pad=20)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path


def draw_pole_zero(
    poles: list[dict],
    zeros: list[dict],
    title: str = "Pole-Zero Plot",
    output_path: Path | str = "pole_zero.png",
) -> Path:
    """Generate a pole-zero plot.

    Each pole/zero dict: {'real': float, 'imag': float}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6))

    for p in poles:
        ax.plot(p["real"], p["imag"], "rx", markersize=12, markeredgewidth=2)

    for z in zeros:
        ax.plot(
            z["real"],
            z["imag"],
            "bo",
            markersize=10,
            markeredgewidth=2,
            fillstyle="none",
        )

    ax.axhline(y=0, color="k", linewidth=0.5)
    ax.axvline(x=0, color="k", linewidth=0.5)
    ax.set_xlabel("Real")
    ax.set_ylabel("Imaginary")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # Add legend
    ax.plot([], [], "rx", markersize=10, markeredgewidth=2, label="Poles")
    ax.plot(
        [], [], "bo", markersize=8, markeredgewidth=2, fillstyle="none", label="Zeros"
    )
    ax.legend()

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path
