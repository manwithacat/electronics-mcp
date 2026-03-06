"""Build formula knowledge entries from structured definitions."""

import json
import uuid

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import record_provenance


FORMULAS = [
    # Ohm's law family
    {
        "topic": "ohms_law",
        "title": "Ohm's Law",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "V",
                "expression": "I * R",
                "latex": "V = IR",
                "description": "Voltage from current and resistance",
            },
            {
                "name": "I",
                "expression": "V / R",
                "latex": "I = \\frac{V}{R}",
                "description": "Current from voltage and resistance",
            },
            {
                "name": "R",
                "expression": "V / I",
                "latex": "R = \\frac{V}{I}",
                "description": "Resistance from voltage and current",
            },
        ],
    },
    # Power
    {
        "topic": "power_formulas",
        "title": "Electrical Power",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "P_vi",
                "expression": "V * I",
                "latex": "P = VI",
                "description": "Power from voltage and current",
            },
            {
                "name": "P_i2r",
                "expression": "I**2 * R",
                "latex": "P = I^2R",
                "description": "Power from current and resistance",
            },
            {
                "name": "P_v2r",
                "expression": "V**2 / R",
                "latex": "P = \\frac{V^2}{R}",
                "description": "Power from voltage and resistance",
            },
        ],
    },
    # Impedance
    {
        "topic": "impedance_formulas",
        "title": "Impedance",
        "category": "ac_theory",
        "formulas": [
            {
                "name": "Xc",
                "expression": "1 / (2 * pi * f * C)",
                "latex": "X_C = \\frac{1}{2\\pi fC}",
                "description": "Capacitive reactance",
            },
            {
                "name": "Xl",
                "expression": "2 * pi * f * L",
                "latex": "X_L = 2\\pi fL",
                "description": "Inductive reactance",
            },
            {
                "name": "Z_series",
                "expression": "sqrt(R**2 + (Xl - Xc)**2)",
                "latex": "Z = \\sqrt{R^2 + (X_L - X_C)^2}",
                "description": "Series impedance magnitude",
            },
        ],
    },
    # Filter cutoffs
    {
        "topic": "filter_cutoff_formulas",
        "title": "Filter Cutoff Frequencies",
        "category": "filter",
        "formulas": [
            {
                "name": "fc_rc",
                "expression": "1 / (2 * pi * R * C)",
                "latex": "f_c = \\frac{1}{2\\pi RC}",
                "description": "RC filter cutoff frequency",
            },
            {
                "name": "fc_rl",
                "expression": "R / (2 * pi * L)",
                "latex": "f_c = \\frac{R}{2\\pi L}",
                "description": "RL filter cutoff frequency",
            },
            {
                "name": "f0_rlc",
                "expression": "1 / (2 * pi * sqrt(L * C))",
                "latex": "f_0 = \\frac{1}{2\\pi\\sqrt{LC}}",
                "description": "RLC resonant frequency",
            },
            {
                "name": "Q_rlc",
                "expression": "(1/R) * sqrt(L/C)",
                "latex": "Q = \\frac{1}{R}\\sqrt{\\frac{L}{C}}",
                "description": "RLC quality factor",
            },
        ],
    },
    # Gain equations
    {
        "topic": "amplifier_gain_formulas",
        "title": "Amplifier Gain",
        "category": "amplifier",
        "formulas": [
            {
                "name": "Av_inv",
                "expression": "-Rf / Rin",
                "latex": "A_v = -\\frac{R_f}{R_{in}}",
                "description": "Inverting opamp gain",
            },
            {
                "name": "Av_noninv",
                "expression": "1 + Rf / Rg",
                "latex": "A_v = 1 + \\frac{R_f}{R_g}",
                "description": "Non-inverting opamp gain",
            },
            {
                "name": "Av_ce",
                "expression": "-Rc / Re",
                "latex": "A_v \\approx -\\frac{R_C}{R_E}",
                "description": "Common emitter gain (with degeneration)",
            },
        ],
    },
    # Voltage divider
    {
        "topic": "voltage_divider_formula",
        "title": "Voltage Divider",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "Vout",
                "expression": "Vin * R2 / (R1 + R2)",
                "latex": "V_{out} = V_{in} \\frac{R_2}{R_1 + R_2}",
                "description": "Output voltage of resistive divider",
            },
        ],
    },
    # Thermal
    {
        "topic": "thermal_formulas",
        "title": "Thermal Calculations",
        "category": "thermal",
        "formulas": [
            {
                "name": "Tj",
                "expression": "Ta + P * Rth_ja",
                "latex": "T_j = T_a + P \\cdot R_{\\theta_{ja}}",
                "description": "Junction temperature",
            },
            {
                "name": "P_diss",
                "expression": "(Tj_max - Ta) / Rth_ja",
                "latex": "P_{max} = \\frac{T_{j,max} - T_a}{R_{\\theta_{ja}}}",
                "description": "Maximum power dissipation",
            },
        ],
    },
    # Timing
    {
        "topic": "rc_timing_formulas",
        "title": "RC Timing",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "tau",
                "expression": "R * C",
                "latex": "\\tau = RC",
                "description": "RC time constant",
            },
            {
                "name": "V_charge",
                "expression": "Vf * (1 - exp(-t / (R * C)))",
                "latex": "V(t) = V_f(1 - e^{-t/RC})",
                "description": "Capacitor charging voltage",
            },
        ],
    },
    # Resonance
    {
        "topic": "resonance_formulas",
        "title": "Resonance",
        "category": "ac_theory",
        "formulas": [
            {
                "name": "f_res",
                "expression": "1 / (2 * pi * sqrt(L * C))",
                "latex": "f_r = \\frac{1}{2\\pi\\sqrt{LC}}",
                "description": "Resonant frequency",
            },
            {
                "name": "BW",
                "expression": "f0 / Q",
                "latex": "BW = \\frac{f_0}{Q}",
                "description": "Bandwidth from center frequency and Q",
            },
        ],
    },
    # === Batch 9: +10 formula sets ===
    {
        "topic": "semiconductor_diode",
        "title": "Semiconductor Diode Equations",
        "category": "semiconductor",
        "formulas": [
            {
                "name": "I_shockley",
                "expression": "Is * (exp(V / (n * Vt)) - 1)",
                "latex": "I = I_S(e^{V/nV_T} - 1)",
                "description": "Shockley diode equation",
            },
            {
                "name": "Vt",
                "expression": "k * T / q",
                "latex": "V_T = \\frac{kT}{q}",
                "description": "Thermal voltage (≈26mV at 300K)",
            },
            {
                "name": "rd",
                "expression": "Vt / Id",
                "latex": "r_d = \\frac{V_T}{I_D}",
                "description": "Dynamic resistance of forward-biased diode",
            },
        ],
    },
    {
        "topic": "bjt_biasing",
        "title": "BJT Biasing Equations",
        "category": "semiconductor",
        "formulas": [
            {
                "name": "Ic",
                "expression": "hFE * Ib",
                "latex": "I_C = \\beta I_B",
                "description": "Collector current from base current",
            },
            {
                "name": "Vce",
                "expression": "Vcc - Ic * (Rc + Re)",
                "latex": "V_{CE} = V_{CC} - I_C(R_C + R_E)",
                "description": "Collector-emitter voltage",
            },
            {
                "name": "S_factor",
                "expression": "(1 + hFE) / (1 + hFE * Re / (Re + Rb))",
                "latex": "S = \\frac{1+\\beta}{1+\\beta R_E/(R_E+R_B)}",
                "description": "Stability factor",
            },
        ],
    },
    {
        "topic": "mosfet_equations",
        "title": "MOSFET Equations",
        "category": "semiconductor",
        "formulas": [
            {
                "name": "Id_sat",
                "expression": "0.5 * Kp * (Vgs - Vth)**2",
                "latex": "I_D = \\frac{K_p}{2}(V_{GS}-V_{th})^2",
                "description": "Drain current in saturation",
            },
            {
                "name": "gm_mos",
                "expression": "2 * Id / (Vgs - Vth)",
                "latex": "g_m = \\frac{2I_D}{V_{GS}-V_{th}}",
                "description": "MOSFET transconductance",
            },
            {
                "name": "Rds_on",
                "expression": "1 / (Kp * (Vgs - Vth))",
                "latex": "R_{DS,on} = \\frac{1}{K_p(V_{GS}-V_{th})}",
                "description": "On-resistance in linear region",
            },
        ],
    },
    {
        "topic": "opamp_bandwidth",
        "title": "Op-Amp Bandwidth",
        "category": "amplifier",
        "formulas": [
            {
                "name": "GBW",
                "expression": "Av * BW",
                "latex": "GBW = A_v \\times BW",
                "description": "Gain-bandwidth product",
            },
            {
                "name": "BW_cl",
                "expression": "GBW / Av",
                "latex": "BW_{CL} = \\frac{GBW}{A_v}",
                "description": "Closed-loop bandwidth",
            },
            {
                "name": "f_slew",
                "expression": "SR / (2 * pi * Vp)",
                "latex": "f_{max} = \\frac{SR}{2\\pi V_p}",
                "description": "Slew rate limited frequency",
            },
        ],
    },
    {
        "topic": "opamp_noise",
        "title": "Op-Amp Noise",
        "category": "amplifier",
        "formulas": [
            {
                "name": "en_total",
                "expression": "en * sqrt(BW)",
                "latex": "e_{n,total} = e_n\\sqrt{BW}",
                "description": "Total input-referred voltage noise",
            },
            {
                "name": "in_total",
                "expression": "in_noise * sqrt(BW)",
                "latex": "i_{n,total} = i_n\\sqrt{BW}",
                "description": "Total input-referred current noise",
            },
        ],
    },
    {
        "topic": "buck_converter",
        "title": "Buck Converter Equations",
        "category": "power",
        "formulas": [
            {
                "name": "D_buck",
                "expression": "Vout / Vin",
                "latex": "D = \\frac{V_{out}}{V_{in}}",
                "description": "Buck converter duty cycle",
            },
            {
                "name": "dI_L",
                "expression": "(Vin - Vout) * D / (f * L)",
                "latex": "\\Delta I_L = \\frac{(V_{in}-V_{out})D}{fL}",
                "description": "Inductor ripple current",
            },
            {
                "name": "dV_out",
                "expression": "dI_L / (8 * f * Cout)",
                "latex": "\\Delta V_{out} = \\frac{\\Delta I_L}{8fC_{out}}",
                "description": "Output voltage ripple",
            },
        ],
    },
    {
        "topic": "boost_converter_formulas",
        "title": "Boost Converter Equations",
        "category": "power",
        "formulas": [
            {
                "name": "D_boost",
                "expression": "1 - Vin / Vout",
                "latex": "D = 1 - \\frac{V_{in}}{V_{out}}",
                "description": "Boost converter duty cycle",
            },
            {
                "name": "L_min",
                "expression": "Vin * D / (f * dI_L)",
                "latex": "L_{min} = \\frac{V_{in} D}{f \\Delta I_L}",
                "description": "Minimum inductance for CCM",
            },
            {
                "name": "dV_boost",
                "expression": "Iout * D / (f * Cout)",
                "latex": "\\Delta V = \\frac{I_{out} D}{fC_{out}}",
                "description": "Output voltage ripple",
            },
        ],
    },
    {
        "topic": "decibel_conversions",
        "title": "Decibel Conversions",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "dB_voltage",
                "expression": "20 * log10(V2 / V1)",
                "latex": "dB = 20\\log_{10}\\frac{V_2}{V_1}",
                "description": "Voltage gain in dB",
            },
            {
                "name": "dB_power",
                "expression": "10 * log10(P2 / P1)",
                "latex": "dB = 10\\log_{10}\\frac{P_2}{P_1}",
                "description": "Power gain in dB",
            },
            {
                "name": "dBm",
                "expression": "10 * log10(P / 0.001)",
                "latex": "dBm = 10\\log_{10}\\frac{P}{1mW}",
                "description": "Power referenced to 1mW",
            },
        ],
    },
    {
        "topic": "wheatstone_bridge_formulas",
        "title": "Wheatstone Bridge",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "V_bridge",
                "expression": "Vcc * (Rx / (R3 + Rx) - R2 / (R1 + R2))",
                "latex": "V_{bridge} = V_{CC}\\left(\\frac{R_x}{R_3+R_x} - \\frac{R_2}{R_1+R_2}\\right)",
                "description": "Bridge voltage",
            },
            {
                "name": "Rx_balance",
                "expression": "R3 * R2 / R1",
                "latex": "R_x = \\frac{R_3 R_2}{R_1}",
                "description": "Unknown resistance at balance",
            },
        ],
    },
    {
        "topic": "transformer_equations",
        "title": "Transformer Equations",
        "category": "fundamentals",
        "formulas": [
            {
                "name": "turns_ratio",
                "expression": "Np / Ns",
                "latex": "n = \\frac{N_p}{N_s}",
                "description": "Turns ratio",
            },
            {
                "name": "V_secondary",
                "expression": "Vp * Ns / Np",
                "latex": "V_s = V_p \\frac{N_s}{N_p}",
                "description": "Secondary voltage",
            },
            {
                "name": "Z_reflected",
                "expression": "Zl * (Np / Ns)**2",
                "latex": "Z_{ref} = Z_L \\left(\\frac{N_p}{N_s}\\right)^2",
                "description": "Reflected impedance",
            },
        ],
    },
    # === Batch 10: +10 formula sets ===
    {
        "topic": "switching_regulator_efficiency",
        "title": "Switching Regulator Efficiency",
        "category": "power",
        "formulas": [
            {
                "name": "P_cond",
                "expression": "I**2 * Rds_on * D",
                "latex": "P_{cond} = I^2 R_{DS,on} D",
                "description": "Conduction loss",
            },
            {
                "name": "P_sw",
                "expression": "0.5 * Vin * I * (tr + tf) * f",
                "latex": "P_{sw} = \\frac{1}{2}V_{in}I(t_r+t_f)f",
                "description": "Switching loss",
            },
            {
                "name": "eta",
                "expression": "Pout / (Pout + P_cond + P_sw)",
                "latex": "\\eta = \\frac{P_{out}}{P_{out}+P_{cond}+P_{sw}}",
                "description": "Efficiency",
            },
        ],
    },
    {
        "topic": "inductor_ripple",
        "title": "Inductor Ripple",
        "category": "power",
        "formulas": [
            {
                "name": "I_peak",
                "expression": "Idc + dI_L / 2",
                "latex": "I_{peak} = I_{DC} + \\frac{\\Delta I_L}{2}",
                "description": "Peak inductor current",
            },
            {
                "name": "E_stored",
                "expression": "0.5 * L * I_peak**2",
                "latex": "E = \\frac{1}{2}LI_{peak}^2",
                "description": "Energy stored in inductor",
            },
        ],
    },
    {
        "topic": "capacitor_selection",
        "title": "Capacitor Selection",
        "category": "power",
        "formulas": [
            {
                "name": "I_ripple",
                "expression": "dI_L / sqrt(3)",
                "latex": "I_{rms} = \\frac{\\Delta I_L}{\\sqrt{3}}",
                "description": "RMS ripple current (triangular)",
            },
            {
                "name": "P_esr",
                "expression": "I_ripple**2 * ESR",
                "latex": "P_{ESR} = I_{rms}^2 \\times ESR",
                "description": "ESR heating power",
            },
        ],
    },
    {
        "topic": "pcb_trace_impedance",
        "title": "PCB Trace Impedance",
        "category": "pcb",
        "formulas": [
            {
                "name": "Z_microstrip",
                "expression": "87 / sqrt(Er + 1.41) * log((5.98 * h) / (0.8 * w + t))",
                "latex": "Z_0 = \\frac{87}{\\sqrt{\\epsilon_r+1.41}}\\ln\\frac{5.98h}{0.8w+t}",
                "description": "Microstrip impedance (approximate)",
            },
            {
                "name": "Z_stripline",
                "expression": "60 / sqrt(Er) * log((1.9 * b) / (0.8 * w + t))",
                "latex": "Z_0 = \\frac{60}{\\sqrt{\\epsilon_r}}\\ln\\frac{1.9b}{0.8w+t}",
                "description": "Stripline impedance (approximate)",
            },
        ],
    },
    {
        "topic": "skin_effect",
        "title": "Skin Effect",
        "category": "ac_theory",
        "formulas": [
            {
                "name": "delta_skin",
                "expression": "1 / sqrt(pi * f * mu * sigma)",
                "latex": "\\delta = \\frac{1}{\\sqrt{\\pi f \\mu \\sigma}}",
                "description": "Skin depth",
            },
            {
                "name": "R_ac",
                "expression": "Rdc * t / (2 * delta_skin)",
                "latex": "R_{AC} \\approx R_{DC}\\frac{t}{2\\delta}",
                "description": "AC resistance increase due to skin effect",
            },
        ],
    },
    {
        "topic": "digital_timing",
        "title": "Digital Timing",
        "category": "digital",
        "formulas": [
            {
                "name": "f_max",
                "expression": "1 / (tpd + tsu)",
                "latex": "f_{max} = \\frac{1}{t_{pd}+t_{su}}",
                "description": "Maximum clock frequency",
            },
            {
                "name": "t_setup_margin",
                "expression": "Tclk - tpd - tsu",
                "latex": "t_{margin} = T_{clk}-t_{pd}-t_{su}",
                "description": "Setup time margin",
            },
        ],
    },
    {
        "topic": "adc_dac_formulas",
        "title": "ADC/DAC Formulas",
        "category": "digital",
        "formulas": [
            {
                "name": "resolution",
                "expression": "Vref / (2**N)",
                "latex": "LSB = \\frac{V_{ref}}{2^N}",
                "description": "LSB step size (resolution)",
            },
            {
                "name": "SNR_ideal",
                "expression": "6.02 * N + 1.76",
                "latex": "SNR = 6.02N + 1.76\\ dB",
                "description": "Ideal ADC SNR",
            },
            {
                "name": "ENOB",
                "expression": "(SNR_meas - 1.76) / 6.02",
                "latex": "ENOB = \\frac{SNR_{meas}-1.76}{6.02}",
                "description": "Effective number of bits",
            },
        ],
    },
    {
        "topic": "pll_basics",
        "title": "PLL Basics",
        "category": "digital",
        "formulas": [
            {
                "name": "f_out_pll",
                "expression": "N * f_ref",
                "latex": "f_{out} = N \\times f_{ref}",
                "description": "PLL output frequency",
            },
            {
                "name": "BW_pll",
                "expression": "f_ref / 10",
                "latex": "BW_{PLL} \\approx \\frac{f_{ref}}{10}",
                "description": "Rule-of-thumb loop bandwidth",
            },
        ],
    },
    {
        "topic": "battery_capacity",
        "title": "Battery Capacity",
        "category": "power",
        "formulas": [
            {
                "name": "C_rate",
                "expression": "I / Capacity",
                "latex": "C_{rate} = \\frac{I}{Capacity}",
                "description": "C-rate (charge/discharge rate)",
            },
            {
                "name": "E_battery",
                "expression": "Capacity * V_nom",
                "latex": "E = Capacity \\times V_{nom}",
                "description": "Battery energy (Wh)",
            },
            {
                "name": "runtime",
                "expression": "Capacity / I",
                "latex": "t = \\frac{Capacity}{I}",
                "description": "Runtime estimate at constant current",
            },
        ],
    },
    {
        "topic": "motor_power",
        "title": "Motor Power",
        "category": "power",
        "formulas": [
            {
                "name": "P_mech",
                "expression": "torque * omega",
                "latex": "P = \\tau \\omega",
                "description": "Mechanical power",
            },
            {
                "name": "eta_motor",
                "expression": "P_mech / P_elec",
                "latex": "\\eta = \\frac{P_{mech}}{P_{elec}}",
                "description": "Motor efficiency",
            },
            {
                "name": "omega_rpm",
                "expression": "rpm * 2 * pi / 60",
                "latex": "\\omega = \\frac{2\\pi \\times RPM}{60}",
                "description": "Angular velocity from RPM",
            },
        ],
    },
]


def build_formulas(db: Database, formula_sets: list[dict] | None = None) -> dict:
    """Insert formula knowledge entries into the database.

    Returns stats dict.
    """
    if formula_sets is None:
        formula_sets = FORMULAS

    stats = {"created": 0, "formulas": 0, "skipped": 0}

    for fset in formula_sets:
        entry_id = str(uuid.uuid4())
        content = f"{fset['title']}:\n"
        for f in fset["formulas"]:
            content += f"- {f['name']}: {f.get('description', f['expression'])}\n"

        created = False
        num_formulas = 0
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM knowledge WHERE topic = ?",
                (fset["topic"],),
            ).fetchone()
            if existing:
                stats["skipped"] += 1
                continue

            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'formula_builder')",
                (
                    entry_id,
                    fset["category"],
                    fset["topic"],
                    fset["title"],
                    content,
                    json.dumps(fset["formulas"]),
                    json.dumps([]),
                    "intermediate",
                ),
            )
            created = True
            num_formulas = len(fset["formulas"])

        if created:
            record_provenance(
                db,
                "knowledge",
                entry_id,
                "formula_builder",
                licence="original",
                notes=f"Formula set: {fset['topic']}",
            )
            stats["created"] += 1
            stats["formulas"] += num_formulas

    return stats
