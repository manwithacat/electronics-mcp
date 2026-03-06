"""Build standard subcircuit library from JSON definitions."""
import json
import uuid
from pathlib import Path

from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import CircuitSchema


# Standard subcircuit definitions
STANDARD_SUBCIRCUITS = [
    # Passive circuits
    {"name": "voltage_divider", "category": "passive",
     "description": "Resistive voltage divider",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R1": "10k", "R2": "10k"},
     "schema": {"name": "voltage_divider", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vout = Vin * R2/(R1+R2). Output impedance = R1||R2."},

    {"name": "rc_lowpass", "category": "passive",
     "description": "First-order RC low-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "rc_lowpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = 1/(2*pi*R*C). -20dB/decade rolloff."},

    {"name": "rc_highpass", "category": "passive",
     "description": "First-order RC high-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "rc_highpass", "components": [
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["input", "output"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = 1/(2*pi*R*C). Blocks DC, passes AC."},

    {"name": "rl_lowpass", "category": "passive",
     "description": "First-order RL low-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "10m"},
     "schema": {"name": "rl_lowpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "output"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10m"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = R/(2*pi*L)."},

    {"name": "rlc_bandpass", "category": "passive",
     "description": "Series RLC bandpass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "1m", "C": "100n"},
     "schema": {"name": "rlc_bandpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "mid"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "1m"}, "nodes": ["mid", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "f0 = 1/(2*pi*sqrt(L*C)). Q = (1/R)*sqrt(L/C)."},

    # Amplifiers
    {"name": "inverting_opamp", "category": "amplifier",
     "description": "Inverting operational amplifier",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"Rf": "100k", "Rin": "10k"},
     "schema": {"name": "inverting_opamp", "components": [
         {"id": "R_in", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "inv_in"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["inv_in", "output"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "gnd", "output"]},
     ]},
     "design_notes": "Gain = -Rf/Rin. Input impedance = Rin."},

    {"name": "non_inverting_opamp", "category": "amplifier",
     "description": "Non-inverting operational amplifier",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"Rf": "90k", "Rg": "10k"},
     "schema": {"name": "non_inverting_opamp", "components": [
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "gnd"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "90k"}, "nodes": ["inv_in", "output"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "input", "output"]},
     ]},
     "design_notes": "Gain = 1 + Rf/Rg. Very high input impedance."},

    {"name": "common_emitter", "category": "amplifier",
     "description": "Common emitter BJT amplifier",
     "ports": ["input", "output", "vcc", "gnd"],
     "parameters": {"Rc": "4.7k", "Rb": "100k", "Re": "1k"},
     "schema": {"name": "common_emitter", "components": [
         {"id": "R_b", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["input", "base"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base", "output", "emitter"]},
         {"id": "R_c", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "output"]},
         {"id": "R_e", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["emitter", "gnd"]},
     ]},
     "design_notes": "Av ≈ -Rc/Re (with emitter degeneration)."},

    # Power
    {"name": "led_driver", "category": "digital_interface",
     "description": "LED driver with current limiting resistor",
     "ports": ["input", "gnd"],
     "parameters": {"R": "330", "Vf": "2V"},
     "schema": {"name": "led_driver", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "330"}, "nodes": ["input", "anode"]},
         {"id": "D1", "type": "led", "parameters": {"forward_voltage": "2V"}, "nodes": ["anode", "gnd"]},
     ]},
     "design_notes": "R = (Vcc - Vf) / If. Typical If = 10-20mA."},

    {"name": "relay_driver", "category": "digital_interface",
     "description": "Relay driver with flyback diode",
     "ports": ["input", "vcc", "gnd"],
     "parameters": {"R_base": "1k"},
     "schema": {"name": "relay_driver", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["input", "base"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base", "coil_low", "gnd"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["coil_low", "vcc"]},
     ]},
     "design_notes": "Flyback diode D1 protects transistor from back-EMF."},

    # === Batch 5: Passive & Filters (12 new) ===

    # Passive (5)
    {"name": "rl_highpass", "category": "passive",
     "description": "First-order RL high-pass filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "10m"},
     "schema": {"name": "rl_highpass", "components": [
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10m"}, "nodes": ["input", "output"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "fc = R/(2*pi*L). Passes high frequencies, blocks DC."},

    {"name": "rlc_bandstop", "category": "passive",
     "description": "Series RLC bandstop (notch) filter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R": "100", "L": "1m", "C": "100n"},
     "schema": {"name": "rlc_bandstop", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "output"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "1m"}, "nodes": ["output", "trap"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["trap", "gnd"]},
     ]},
     "design_notes": "f0 = 1/(2*pi*sqrt(L*C)). Rejects a narrow frequency band."},

    {"name": "pi_filter", "category": "passive",
     "description": "Pi LC filter for power supply decoupling",
     "ports": ["input", "output", "gnd"],
     "parameters": {"C1": "100u", "L": "10u", "C2": "100u"},
     "schema": {"name": "pi_filter", "components": [
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100u"}, "nodes": ["input", "gnd"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10u"}, "nodes": ["input", "output"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "100u"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Good for power supply filtering. CLC topology provides high attenuation."},

    {"name": "t_filter", "category": "passive",
     "description": "T LC filter topology",
     "ports": ["input", "output", "gnd"],
     "parameters": {"L1": "10u", "C": "100u", "L2": "10u"},
     "schema": {"name": "t_filter", "components": [
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10u"}, "nodes": ["input", "mid"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100u"}, "nodes": ["mid", "gnd"]},
         {"id": "L2", "type": "inductor", "parameters": {"inductance": "10u"}, "nodes": ["mid", "output"]},
     ]},
     "design_notes": "LCL topology. Good impedance matching between source and load."},

    {"name": "impedance_matching_l", "category": "passive",
     "description": "L-network impedance matching",
     "ports": ["input", "output", "gnd"],
     "parameters": {"L": "100n", "C": "100p"},
     "schema": {"name": "impedance_matching_l", "components": [
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "100n"}, "nodes": ["input", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100p"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Matches source impedance to load at a specific frequency. Q = sqrt(Rh/Rl - 1)."},

    # Filters (5)
    {"name": "sallen_key_lowpass", "category": "filter",
     "description": "Sallen-Key second-order active low-pass filter",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"R1": "10k", "R2": "10k", "C1": "10n", "C2": "10n"},
     "schema": {"name": "sallen_key_lowpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "mid1"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["mid1", "inv_in"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["mid1", "output"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["inv_in", "gnd"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "output", "output"]},
     ]},
     "design_notes": "fc = 1/(2*pi*sqrt(R1*R2*C1*C2)). Unity-gain Butterworth when R1=R2, C1=C2."},

    {"name": "sallen_key_highpass", "category": "filter",
     "description": "Sallen-Key second-order active high-pass filter",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"R1": "10k", "R2": "10k", "C1": "10n", "C2": "10n"},
     "schema": {"name": "sallen_key_highpass", "components": [
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["input", "mid1"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["mid1", "inv_in"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["mid1", "output"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "gnd"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "output", "output"]},
     ]},
     "design_notes": "fc = 1/(2*pi*sqrt(R1*R2*C1*C2)). Dual of the low-pass Sallen-Key."},

    {"name": "multiple_feedback_bandpass", "category": "filter",
     "description": "Multiple feedback bandpass filter",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"R1": "10k", "R2": "10k", "R3": "10k", "C1": "10n", "C2": "10n"},
     "schema": {"name": "multiple_feedback_bandpass", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "inv_in"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["inv_in", "output"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "gnd"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["input", "output"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "output"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "gnd", "output"]},
     ]},
     "design_notes": "Provides bandpass response with adjustable Q and center frequency."},

    {"name": "state_variable_filter", "category": "filter",
     "description": "State variable filter (simultaneous LP/HP/BP outputs)",
     "ports": ["input", "lp_out", "hp_out", "bp_out", "gnd", "vcc", "vee"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "state_variable_filter", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "sum"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["bp_out", "sum"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["sum", "gnd", "hp_out"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["hp_out", "int1"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["int1", "bp_out"]},
         {"id": "R4", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["bp_out", "int2"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["int2", "lp_out"]},
     ]},
     "design_notes": "f0 = 1/(2*pi*R*C). Provides simultaneous LP, HP, BP outputs."},

    {"name": "active_notch_filter", "category": "filter",
     "description": "Active twin-T notch filter",
     "ports": ["input", "output", "gnd", "vcc", "vee"],
     "parameters": {"R": "10k", "C": "10n"},
     "schema": {"name": "active_notch_filter", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["input", "mid1"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["mid1", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["input", "mid2"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["mid2", "output"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "5k"}, "nodes": ["mid2", "gnd"]},
         {"id": "C3", "type": "capacitor", "parameters": {"capacitance": "20n"}, "nodes": ["mid1", "gnd"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["output", "output", "output"]},
     ]},
     "design_notes": "f_notch = 1/(2*pi*R*C). Twin-T network with opamp buffer for high Q."},

    # Protection (2)
    {"name": "tvs_clamp", "category": "protection",
     "description": "TVS diode voltage clamp for ESD/surge protection",
     "ports": ["input", "output", "gnd"],
     "parameters": {"R_series": "10"},
     "schema": {"name": "tvs_clamp", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10"}, "nodes": ["input", "output"]},
         {"id": "D1", "type": "zener", "parameters": {"breakdown_voltage": "5.1V"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "TVS clamps voltage transients. Place close to connector."},

    {"name": "reverse_polarity_pmos", "category": "protection",
     "description": "Reverse polarity protection using P-channel MOSFET",
     "ports": ["input", "output", "gnd"],
     "parameters": {},
     "schema": {"name": "reverse_polarity_pmos", "components": [
         {"id": "M1", "type": "mosfet", "subtype": "p-channel", "parameters": {}, "nodes": ["input", "output", "input"]},
     ]},
     "design_notes": "P-FET conducts when correct polarity applied. Lower Vdrop than diode."},

    # === Batch 6: Amplifiers & Power (14 new) ===

    # Amplifiers (7)
    {"name": "common_collector", "category": "amplifier",
     "description": "Common collector (emitter follower) BJT amplifier",
     "ports": ["input", "output", "vcc", "gnd"],
     "parameters": {"Rb": "100k", "Re": "1k"},
     "schema": {"name": "common_collector", "components": [
         {"id": "R_b", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["input", "base"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base", "vcc", "output"]},
         {"id": "R_e", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Voltage gain ≈ 1. High input impedance, low output impedance. Buffer."},

    {"name": "common_base", "category": "amplifier",
     "description": "Common base BJT amplifier",
     "ports": ["input", "output", "vcc", "gnd"],
     "parameters": {"Re": "1k", "Rc": "4.7k"},
     "schema": {"name": "common_base", "components": [
         {"id": "R_e", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["input", "emitter"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["gnd", "output", "emitter"]},
         {"id": "R_c", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "output"]},
     ]},
     "design_notes": "Av ≈ Rc/Re. Low input impedance. Good for high-frequency applications."},

    {"name": "common_source", "category": "amplifier",
     "description": "Common source MOSFET amplifier",
     "ports": ["input", "output", "vdd", "gnd"],
     "parameters": {"Rd": "4.7k", "Rs": "1k", "Rg": "1M"},
     "schema": {"name": "common_source", "components": [
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "1M"}, "nodes": ["input", "gate"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["gate", "output", "src"]},
         {"id": "R_d", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vdd", "output"]},
         {"id": "R_s", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["src", "gnd"]},
     ]},
     "design_notes": "Av = -gm*Rd (with source bypassed). Very high input impedance."},

    {"name": "common_drain", "category": "amplifier",
     "description": "Common drain (source follower) MOSFET amplifier",
     "ports": ["input", "output", "vdd", "gnd"],
     "parameters": {"Rs": "1k", "Rg": "1M"},
     "schema": {"name": "common_drain", "components": [
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "1M"}, "nodes": ["input", "gate"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["gate", "vdd", "output"]},
         {"id": "R_s", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Av ≈ 1. Buffer with very high input impedance, moderate output impedance."},

    {"name": "differential_amplifier", "category": "amplifier",
     "description": "BJT differential pair amplifier",
     "ports": ["inp", "inn", "output", "vcc", "gnd"],
     "parameters": {"Rc": "4.7k", "Re": "10k"},
     "schema": {"name": "differential_amplifier", "components": [
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["inp", "output", "tail"]},
         {"id": "Q2", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["inn", "vcc", "tail"]},
         {"id": "R_c", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "output"]},
         {"id": "R_e", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["tail", "gnd"]},
     ]},
     "design_notes": "Ad = gm*Rc. Good CMRR. Basis for opamp input stages."},

    {"name": "instrumentation_amplifier", "category": "amplifier",
     "description": "Three-opamp instrumentation amplifier",
     "ports": ["inp", "inn", "output", "gnd", "vcc", "vee"],
     "parameters": {"R1": "10k", "Rg": "1k", "R2": "10k", "R3": "10k"},
     "schema": {"name": "instrumentation_amplifier", "components": [
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inp", "fb1", "out1"]},
         {"id": "U2", "type": "opamp", "parameters": {}, "nodes": ["inn", "fb2", "out2"]},
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "1k"}, "nodes": ["fb1", "fb2"]},
         {"id": "R1a", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["out1", "fb1"]},
         {"id": "R1b", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["out2", "fb2"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["out1", "diff_in"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["diff_in", "output"]},
         {"id": "R4", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["out2", "ref"]},
         {"id": "R5", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["ref", "gnd"]},
         {"id": "U3", "type": "opamp", "parameters": {}, "nodes": ["diff_in", "ref", "output"]},
     ]},
     "design_notes": "Gain = (1 + 2*R1/Rg) * (R3/R2). High CMRR, high Zin."},

    {"name": "push_pull_output", "category": "amplifier",
     "description": "Push-pull (complementary) output stage",
     "ports": ["input", "output", "vcc", "vee"],
     "parameters": {"R_bias": "100"},
     "schema": {"name": "push_pull_output", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100"}, "nodes": ["input", "base_n"]},
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["base_n", "vcc", "output"]},
         {"id": "Q2", "type": "bjt", "subtype": "pnp", "parameters": {"model": "2N2907"}, "nodes": ["base_n", "vee", "output"]},
     ]},
     "design_notes": "Class B output. Add bias diodes for class AB to reduce crossover distortion."},

    # Power (7)
    {"name": "linear_regulator_78xx", "category": "power",
     "description": "Fixed linear voltage regulator (78xx series)",
     "ports": ["input", "output", "gnd"],
     "parameters": {"Cin": "330n", "Cout": "100n"},
     "schema": {"name": "linear_regulator_78xx", "components": [
         {"id": "C_in", "type": "capacitor", "parameters": {"capacitance": "330n"}, "nodes": ["input", "gnd"]},
         {"id": "U1", "type": "voltage_regulator", "parameters": {"output_voltage": "5V"}, "nodes": ["input", "output"]},
         {"id": "C_out", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vin must be > Vout + 2V (dropout). Cin required if far from filter cap."},

    {"name": "ldo_regulator", "category": "power",
     "description": "Low-dropout voltage regulator with decoupling",
     "ports": ["input", "output", "gnd"],
     "parameters": {"Cin": "1u", "Cout": "10u"},
     "schema": {"name": "ldo_regulator", "components": [
         {"id": "C_in", "type": "capacitor", "parameters": {"capacitance": "1u"}, "nodes": ["input", "gnd"]},
         {"id": "U1", "type": "voltage_regulator", "parameters": {"output_voltage": "3.3V", "dropout": "0.2V"}, "nodes": ["input", "output"]},
         {"id": "C_out", "type": "capacitor", "parameters": {"capacitance": "10u"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Low dropout (~200mV). Cout ESR critical for stability — check datasheet."},

    {"name": "boost_converter", "category": "power",
     "description": "Boost (step-up) switching converter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"L": "10u", "C": "22u"},
     "schema": {"name": "boost_converter", "components": [
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "10u"}, "nodes": ["input", "sw_node"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["sw_node", "sw_node", "gnd"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["sw_node", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "22u"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vout = Vin/(1-D). D = duty cycle. L = Vin*D/(f*deltaI)."},

    {"name": "buck_boost_converter", "category": "power",
     "description": "Buck-boost (inverting) switching converter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"L": "22u", "C": "47u"},
     "schema": {"name": "buck_boost_converter", "components": [
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["input", "input", "sw_node"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "22u"}, "nodes": ["sw_node", "gnd"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["output", "sw_node"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "47u"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vout = -Vin*D/(1-D). Output is inverted. Can step up or down."},

    {"name": "flyback_converter", "category": "power",
     "description": "Flyback converter for isolated DC-DC",
     "ports": ["input", "output", "gnd_pri", "gnd_sec"],
     "parameters": {"Lp": "100u", "C": "47u"},
     "schema": {"name": "flyback_converter", "components": [
         {"id": "T1", "type": "transformer", "parameters": {"turns_ratio": "1:1"}, "nodes": ["input", "sw_node"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["sw_node", "sw_node", "gnd_pri"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["sec_out", "output"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "47u"}, "nodes": ["output", "gnd_sec"]},
     ]},
     "design_notes": "Provides galvanic isolation. Energy stored in transformer gap."},

    {"name": "charge_pump", "category": "power",
     "description": "Voltage doubler charge pump",
     "ports": ["input", "output", "gnd"],
     "parameters": {"C_fly": "1u", "C_out": "10u"},
     "schema": {"name": "charge_pump", "components": [
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "1u"}, "nodes": ["input", "mid"]},
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["gnd", "mid"]},
         {"id": "D2", "type": "diode", "parameters": {}, "nodes": ["mid", "output"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10u"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "Vout ≈ 2*Vin - 2*Vf. Low current capability. Good for bias supplies."},

    {"name": "gate_driver_bootstrap", "category": "power",
     "description": "High-side gate driver bootstrap circuit",
     "ports": ["pwm_in", "gate_out", "vcc", "gnd"],
     "parameters": {"C_boot": "100n", "R_gate": "10"},
     "schema": {"name": "gate_driver_bootstrap", "components": [
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["vcc", "boot"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["boot", "sw_node"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10"}, "nodes": ["boot", "gate_out"]},
     ]},
     "design_notes": "Bootstrap cap charges when low-side on. Provides Vgs > Vth for high-side FET."},

    # === Batch 7: Oscillators, Digital, Interface (14 new) ===

    # Oscillators (5)
    {"name": "astable_555", "category": "oscillator",
     "description": "555 timer in astable mode",
     "ports": ["output", "vcc", "gnd"],
     "parameters": {"Ra": "10k", "Rb": "10k", "C": "10n"},
     "schema": {"name": "astable_555", "components": [
         {"id": "U1", "type": "timer_555", "parameters": {}, "nodes": ["output", "vcc"]},
         {"id": "R_a", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "dis"]},
         {"id": "R_b", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["dis", "thresh"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["thresh", "gnd"]},
     ]},
     "design_notes": "f = 1.44/((Ra+2*Rb)*C). Duty > 50% inherently."},

    {"name": "monostable_555", "category": "oscillator",
     "description": "555 timer in monostable (one-shot) mode",
     "ports": ["trigger", "output", "vcc", "gnd"],
     "parameters": {"R": "100k", "C": "10u"},
     "schema": {"name": "monostable_555", "components": [
         {"id": "U1", "type": "timer_555", "parameters": {}, "nodes": ["output", "vcc"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["vcc", "dis"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10u"}, "nodes": ["dis", "gnd"]},
     ]},
     "design_notes": "t_pulse = 1.1 * R * C. Triggered on negative edge of trigger input."},

    {"name": "colpitts_oscillator", "category": "oscillator",
     "description": "Colpitts LC oscillator",
     "ports": ["output", "vcc", "gnd"],
     "parameters": {"L": "1u", "C1": "100p", "C2": "100p"},
     "schema": {"name": "colpitts_oscillator", "components": [
         {"id": "Q1", "type": "bjt", "parameters": {"model": "2N2222"}, "nodes": ["gnd", "output", "emitter"]},
         {"id": "L1", "type": "inductor", "parameters": {"inductance": "1u"}, "nodes": ["output", "emitter"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100p"}, "nodes": ["output", "gnd"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "100p"}, "nodes": ["emitter", "gnd"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "output"]},
     ]},
     "design_notes": "f = 1/(2*pi*sqrt(L*Cs)), Cs = C1*C2/(C1+C2). Feedback ratio = C1/C2."},

    {"name": "wien_bridge_oscillator", "category": "oscillator",
     "description": "Wien bridge sine wave oscillator",
     "ports": ["output", "vcc", "vee", "gnd"],
     "parameters": {"R": "10k", "C": "10n", "Rf": "20k", "Rg": "10k"},
     "schema": {"name": "wien_bridge_oscillator", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["output", "pos_in"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["pos_in", "gnd"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["pos_in", "mid"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "10n"}, "nodes": ["mid", "gnd"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "20k"}, "nodes": ["inv_in", "output"]},
         {"id": "R_g", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inv_in", "gnd"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["inv_in", "pos_in", "output"]},
     ]},
     "design_notes": "f = 1/(2*pi*R*C). Requires Rf/Rg = 2 for sustained oscillation."},

    {"name": "crystal_oscillator_pierce", "category": "oscillator",
     "description": "Pierce crystal oscillator",
     "ports": ["output", "vcc", "gnd"],
     "parameters": {"C1": "22p", "C2": "22p", "Rf": "1M"},
     "schema": {"name": "crystal_oscillator_pierce", "components": [
         {"id": "Y1", "type": "crystal", "parameters": {"frequency": "16M"}, "nodes": ["xin", "xout"]},
         {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "22p"}, "nodes": ["xin", "gnd"]},
         {"id": "C2", "type": "capacitor", "parameters": {"capacitance": "22p"}, "nodes": ["xout", "gnd"]},
         {"id": "R_f", "type": "resistor", "parameters": {"resistance": "1M"}, "nodes": ["xin", "xout"]},
     ]},
     "design_notes": "Load capacitance = C1*C2/(C1+C2) + Cstray. Most common MCU oscillator."},

    # Digital Interface (4)
    {"name": "rs_latch", "category": "digital_interface",
     "description": "RS latch from cross-coupled NAND (resistor pull-ups)",
     "ports": ["set", "reset", "q", "vcc", "gnd"],
     "parameters": {"R1": "10k", "R2": "10k"},
     "schema": {"name": "rs_latch", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "set"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "reset"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["q", "gnd"]},
     ]},
     "design_notes": "Active-low set/reset. Pull-up resistors for open-collector/drain outputs."},

    {"name": "comparator_with_hysteresis", "category": "digital_interface",
     "description": "Schmitt trigger comparator with positive feedback",
     "ports": ["input", "output", "vref", "vcc", "vee"],
     "parameters": {"R1": "10k", "R2": "100k"},
     "schema": {"name": "comparator_with_hysteresis", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vref", "pos_in"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "100k"}, "nodes": ["output", "pos_in"]},
         {"id": "U1", "type": "comparator", "parameters": {}, "nodes": ["input", "pos_in", "output"]},
     ]},
     "design_notes": "Hysteresis = Vout_swing * R1/(R1+R2). Prevents output chatter."},

    {"name": "current_limiter", "category": "digital_interface",
     "description": "Simple FET current limiter",
     "ports": ["input", "output", "gnd"],
     "parameters": {"Rs": "1"},
     "schema": {"name": "current_limiter", "components": [
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["input", "input", "output"]},
         {"id": "R_s", "type": "resistor", "parameters": {"resistance": "1"}, "nodes": ["output", "gnd"]},
     ]},
     "design_notes": "I_limit ≈ Vgs_th / Rs. Self-regulating current source."},

    {"name": "voltage_level_shifter", "category": "digital_interface",
     "description": "Bidirectional logic level shifter (3.3V to 5V)",
     "ports": ["low_side", "high_side", "vcc_low", "vcc_high", "gnd"],
     "parameters": {"R1": "10k", "R2": "10k"},
     "schema": {"name": "voltage_level_shifter", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc_low", "low_side"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["low_side", "high_side", "gnd"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc_high", "high_side"]},
     ]},
     "design_notes": "BSS138-based level shifter. Works bidirectionally for I2C/SPI."},

    # Power extras (3)
    {"name": "full_bridge", "category": "power",
     "description": "Full-bridge (H-bridge) rectifier",
     "ports": ["ac1", "ac2", "dc_pos", "dc_neg"],
     "parameters": {},
     "schema": {"name": "full_bridge", "components": [
         {"id": "D1", "type": "diode", "parameters": {}, "nodes": ["ac1", "dc_pos"]},
         {"id": "D2", "type": "diode", "parameters": {}, "nodes": ["dc_neg", "ac1"]},
         {"id": "D3", "type": "diode", "parameters": {}, "nodes": ["ac2", "dc_pos"]},
         {"id": "D4", "type": "diode", "parameters": {}, "nodes": ["dc_neg", "ac2"]},
     ]},
     "design_notes": "Full-wave rectification. Vdc ≈ Vpeak - 2*Vf. Add filter cap for DC."},

    {"name": "half_bridge_driver", "category": "power",
     "description": "Half-bridge MOSFET driver",
     "ports": ["hi_in", "lo_in", "output", "vbus", "gnd"],
     "parameters": {"R_hi": "10", "R_lo": "10"},
     "schema": {"name": "half_bridge_driver", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10"}, "nodes": ["hi_in", "gate_hi"]},
         {"id": "M1", "type": "mosfet", "parameters": {}, "nodes": ["gate_hi", "vbus", "output"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10"}, "nodes": ["lo_in", "gate_lo"]},
         {"id": "M2", "type": "mosfet", "parameters": {}, "nodes": ["gate_lo", "output", "gnd"]},
     ]},
     "design_notes": "Dead-time needed to prevent shoot-through. Gate resistors control dV/dt."},

    {"name": "i2c_pullup", "category": "digital_interface",
     "description": "I2C bus pull-up resistors",
     "ports": ["sda", "scl", "vcc"],
     "parameters": {"R_sda": "4.7k", "R_scl": "4.7k"},
     "schema": {"name": "i2c_pullup", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "sda"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "4.7k"}, "nodes": ["vcc", "scl"]},
     ]},
     "design_notes": "4.7k for 100kHz, 2.2k for 400kHz. Check bus capacitance."},

    # Misc (2)
    {"name": "wheatstone_bridge", "category": "passive",
     "description": "Wheatstone bridge for precision measurement",
     "ports": ["vcc", "gnd", "sense_pos", "sense_neg"],
     "parameters": {"R1": "10k", "R2": "10k", "R3": "10k", "Rx": "10k"},
     "schema": {"name": "wheatstone_bridge", "components": [
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "sense_pos"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["sense_pos", "gnd"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["vcc", "sense_neg"]},
         {"id": "Rx", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["sense_neg", "gnd"]},
     ]},
     "design_notes": "Balanced when R1/R2 = R3/Rx. Vbridge = Vcc*(Rx/(R3+Rx) - R2/(R1+R2))."},

    {"name": "current_sense_amplifier", "category": "amplifier",
     "description": "High-side current sense amplifier",
     "ports": ["inp", "inn", "output", "gnd", "vcc"],
     "parameters": {"Rshunt": "0.1", "Rgain": "10k"},
     "schema": {"name": "current_sense_amplifier", "components": [
         {"id": "R_shunt", "type": "resistor", "parameters": {"resistance": "0.1"}, "nodes": ["inp", "inn"]},
         {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inp", "pos_in"]},
         {"id": "R2", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["inn", "neg_in"]},
         {"id": "R3", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["neg_in", "output"]},
         {"id": "R4", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["pos_in", "gnd"]},
         {"id": "U1", "type": "opamp", "parameters": {}, "nodes": ["neg_in", "pos_in", "output"]},
     ]},
     "design_notes": "Vout = I_load * Rshunt * (R3/R2). Kelvin-connected for accuracy."},
]


def build_subcircuits(db: Database, definitions: list[dict] | None = None) -> dict:
    """Build subcircuit library from definitions.

    Args:
        db: Database to populate
        definitions: List of subcircuit definitions. Uses STANDARD_SUBCIRCUITS if None.

    Returns:
        Stats dict with counts.
    """
    if definitions is None:
        definitions = STANDARD_SUBCIRCUITS

    stats = {"created": 0, "skipped": 0, "errors": 0}

    for defn in definitions:
        try:
            # Validate schema
            CircuitSchema.model_validate(defn["schema"])

            sc_id = str(uuid.uuid4())
            with db.connect() as conn:
                existing = conn.execute(
                    "SELECT id FROM subcircuits WHERE name = ?",
                    (defn["name"],),
                ).fetchone()
                if existing:
                    stats["skipped"] += 1
                    continue

                conn.execute(
                    "INSERT INTO subcircuits (id, name, category, description, "
                    "schema_json, ports, parameters, design_notes, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'builder')",
                    (sc_id, defn["name"], defn.get("category", ""),
                     defn.get("description", ""),
                     json.dumps(defn["schema"]),
                     json.dumps(defn["ports"]),
                     json.dumps(defn.get("parameters", {})),
                     defn.get("design_notes", "")),
                )
                stats["created"] += 1

        except Exception as e:
            stats["errors"] += 1

    return stats


def build_from_directory(source_dir: Path | str, db: Database) -> dict:
    """Build subcircuits from JSON files in a directory."""
    source_dir = Path(source_dir)
    definitions = []
    for f in sorted(source_dir.glob("*.json")):
        defn = json.loads(f.read_text())
        if isinstance(defn, list):
            definitions.extend(defn)
        else:
            definitions.append(defn)
    return build_subcircuits(db, definitions)
