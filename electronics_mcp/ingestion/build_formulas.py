"""Build formula knowledge entries from structured definitions."""
import json
import uuid

from electronics_mcp.core.database import Database


FORMULAS = [
    # Ohm's law family
    {"topic": "ohms_law", "title": "Ohm's Law", "category": "fundamentals",
     "formulas": [
         {"name": "V", "expression": "I * R", "latex": "V = IR", "description": "Voltage from current and resistance"},
         {"name": "I", "expression": "V / R", "latex": "I = \\frac{V}{R}", "description": "Current from voltage and resistance"},
         {"name": "R", "expression": "V / I", "latex": "R = \\frac{V}{I}", "description": "Resistance from voltage and current"},
     ]},

    # Power
    {"topic": "power_formulas", "title": "Electrical Power", "category": "fundamentals",
     "formulas": [
         {"name": "P_vi", "expression": "V * I", "latex": "P = VI", "description": "Power from voltage and current"},
         {"name": "P_i2r", "expression": "I**2 * R", "latex": "P = I^2R", "description": "Power from current and resistance"},
         {"name": "P_v2r", "expression": "V**2 / R", "latex": "P = \\frac{V^2}{R}", "description": "Power from voltage and resistance"},
     ]},

    # Impedance
    {"topic": "impedance_formulas", "title": "Impedance", "category": "ac_theory",
     "formulas": [
         {"name": "Xc", "expression": "1 / (2 * pi * f * C)", "latex": "X_C = \\frac{1}{2\\pi fC}", "description": "Capacitive reactance"},
         {"name": "Xl", "expression": "2 * pi * f * L", "latex": "X_L = 2\\pi fL", "description": "Inductive reactance"},
         {"name": "Z_series", "expression": "sqrt(R**2 + (Xl - Xc)**2)", "latex": "Z = \\sqrt{R^2 + (X_L - X_C)^2}", "description": "Series impedance magnitude"},
     ]},

    # Filter cutoffs
    {"topic": "filter_cutoff_formulas", "title": "Filter Cutoff Frequencies", "category": "filter",
     "formulas": [
         {"name": "fc_rc", "expression": "1 / (2 * pi * R * C)", "latex": "f_c = \\frac{1}{2\\pi RC}", "description": "RC filter cutoff frequency"},
         {"name": "fc_rl", "expression": "R / (2 * pi * L)", "latex": "f_c = \\frac{R}{2\\pi L}", "description": "RL filter cutoff frequency"},
         {"name": "f0_rlc", "expression": "1 / (2 * pi * sqrt(L * C))", "latex": "f_0 = \\frac{1}{2\\pi\\sqrt{LC}}", "description": "RLC resonant frequency"},
         {"name": "Q_rlc", "expression": "(1/R) * sqrt(L/C)", "latex": "Q = \\frac{1}{R}\\sqrt{\\frac{L}{C}}", "description": "RLC quality factor"},
     ]},

    # Gain equations
    {"topic": "amplifier_gain_formulas", "title": "Amplifier Gain", "category": "amplifier",
     "formulas": [
         {"name": "Av_inv", "expression": "-Rf / Rin", "latex": "A_v = -\\frac{R_f}{R_{in}}", "description": "Inverting opamp gain"},
         {"name": "Av_noninv", "expression": "1 + Rf / Rg", "latex": "A_v = 1 + \\frac{R_f}{R_g}", "description": "Non-inverting opamp gain"},
         {"name": "Av_ce", "expression": "-Rc / Re", "latex": "A_v \\approx -\\frac{R_C}{R_E}", "description": "Common emitter gain (with degeneration)"},
     ]},

    # Voltage divider
    {"topic": "voltage_divider_formula", "title": "Voltage Divider", "category": "fundamentals",
     "formulas": [
         {"name": "Vout", "expression": "Vin * R2 / (R1 + R2)", "latex": "V_{out} = V_{in} \\frac{R_2}{R_1 + R_2}", "description": "Output voltage of resistive divider"},
     ]},

    # Thermal
    {"topic": "thermal_formulas", "title": "Thermal Calculations", "category": "thermal",
     "formulas": [
         {"name": "Tj", "expression": "Ta + P * Rth_ja", "latex": "T_j = T_a + P \\cdot R_{\\theta_{ja}}", "description": "Junction temperature"},
         {"name": "P_diss", "expression": "(Tj_max - Ta) / Rth_ja", "latex": "P_{max} = \\frac{T_{j,max} - T_a}{R_{\\theta_{ja}}}", "description": "Maximum power dissipation"},
     ]},

    # Timing
    {"topic": "rc_timing_formulas", "title": "RC Timing", "category": "fundamentals",
     "formulas": [
         {"name": "tau", "expression": "R * C", "latex": "\\tau = RC", "description": "RC time constant"},
         {"name": "V_charge", "expression": "Vf * (1 - exp(-t / (R * C)))", "latex": "V(t) = V_f(1 - e^{-t/RC})", "description": "Capacitor charging voltage"},
     ]},

    # Resonance
    {"topic": "resonance_formulas", "title": "Resonance", "category": "ac_theory",
     "formulas": [
         {"name": "f_res", "expression": "1 / (2 * pi * sqrt(L * C))", "latex": "f_r = \\frac{1}{2\\pi\\sqrt{LC}}", "description": "Resonant frequency"},
         {"name": "BW", "expression": "f0 / Q", "latex": "BW = \\frac{f_0}{Q}", "description": "Bandwidth from center frequency and Q"},
     ]},
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
                (entry_id, fset["category"], fset["topic"], fset["title"],
                 content, json.dumps(fset["formulas"]), json.dumps([]),
                 "intermediate"),
            )
            stats["created"] += 1
            stats["formulas"] += len(fset["formulas"])

    return stats
