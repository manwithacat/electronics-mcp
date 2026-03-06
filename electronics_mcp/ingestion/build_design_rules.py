"""Build design rules knowledge entries from structured definitions."""

import json
import uuid

from electronics_mcp.core.database import Database
from electronics_mcp.ingestion.provenance import record_provenance


DESIGN_RULES = [
    {
        "topic": "decoupling_capacitors",
        "title": "Decoupling Capacitor Placement",
        "content": "Place 100nF ceramic capacitors as close as possible to every IC power pin. "
        "Add bulk capacitors (10-100uF) on each power rail. Use low-ESR ceramics for "
        "high-frequency decoupling. Multiple smaller caps are better than one large cap.",
        "category": "design_rule",
    },
    {
        "topic": "ground_planes",
        "title": "Ground Plane Design",
        "content": "Use unbroken ground planes on multilayer PCBs. Avoid splitting ground planes "
        "under high-speed signal traces. Connect analog and digital grounds at a single "
        "point (star ground) to prevent noise coupling.",
        "category": "design_rule",
    },
    {
        "topic": "voltage_derating",
        "title": "Component Voltage Derating",
        "content": "Derate capacitors to 50% of rated voltage for reliability. Derate semiconductors "
        "to 80% of absolute maximum ratings. Resistors should not exceed 75% of rated power "
        "in continuous operation.",
        "category": "design_rule",
    },
    {
        "topic": "thermal_management",
        "title": "Thermal Management Guidelines",
        "content": "Calculate power dissipation for all active components. Use thermal resistance "
        "values (Rth_ja, Rth_jc) to estimate junction temperature. Add heatsinks when "
        "Tj exceeds 80% of Tj_max. Ensure adequate airflow for convection cooling.",
        "category": "design_rule",
    },
    {
        "topic": "trace_width_current",
        "title": "PCB Trace Width vs Current",
        "content": "Use IPC-2221 standard for trace width calculations. For 1oz copper external "
        "layers: 10mil for 0.5A, 20mil for 1A, 50mil for 2A, 100mil for 4A. "
        "Internal layers require wider traces due to reduced cooling.",
        "category": "design_rule",
    },
    {
        "topic": "bypass_cap_placement",
        "title": "Bypass Capacitor Strategy",
        "content": "Place bypass caps on the same layer as the IC when possible. Route power through "
        "the capacitor to the IC pin, not the other way around. Use 100nF + 10nF in parallel "
        "for wide frequency coverage.",
        "category": "design_rule",
    },
    {
        "topic": "emi_reduction",
        "title": "EMI Reduction Techniques",
        "content": "Minimize loop areas in high-current paths. Use ground planes to reduce radiation. "
        "Add ferrite beads on power lines entering/exiting the board. Shield sensitive analog "
        "circuits from digital noise sources.",
        "category": "design_rule",
    },
    {
        "topic": "input_protection",
        "title": "Input Protection",
        "content": "Add TVS diodes on external-facing signal lines. Use series resistors to limit "
        "current into ESD protection structures. Clamp voltages to supply rails with "
        "Schottky diodes for overvoltage protection.",
        "category": "design_rule",
    },
    {
        "topic": "power_supply_sequencing",
        "title": "Power Supply Sequencing",
        "content": "Ensure core voltage is applied before I/O voltage for FPGAs and processors. "
        "Use sequencing ICs or RC delays for controlled power-up order. Add supervisor "
        "ICs for brownout detection and controlled reset.",
        "category": "design_rule",
    },
    {
        "topic": "signal_integrity",
        "title": "Signal Integrity Basics",
        "content": "Match trace impedance to source/load impedance for high-speed signals. "
        "Use series termination (source) or parallel termination (load) to prevent "
        "reflections. Keep high-speed traces short and avoid vias.",
        "category": "design_rule",
    },
    # Batch 8: +20 design rules
    {
        "topic": "analog_layout_guidelines",
        "title": "Analog Layout Guidelines",
        "content": "Keep analog signal paths short and away from digital signals. Use guard rings "
        "around sensitive analog nodes. Route analog signals over unbroken ground planes. "
        "Separate analog and digital power planes with ferrite beads at the bridge point.",
        "category": "design_rule",
    },
    {
        "topic": "component_selection_criteria",
        "title": "Component Selection Criteria",
        "content": "Select components with adequate margin: voltage rating 2x operating, current "
        "rating 1.5x expected. Prefer automotive-grade (AEC-Q) for harsh environments. "
        "Check long-term availability and second-source options. Consider temperature "
        "coefficient, aging drift, and end-of-life derating.",
        "category": "design_rule",
    },
    {
        "topic": "opamp_stability",
        "title": "Op-Amp Stability",
        "content": "Ensure adequate phase margin (>45 degrees, ideally >60 degrees). Add compensation "
        "capacitor in feedback path for capacitive loads. Use unity-gain-stable opamps for "
        "gain < 5. Check datasheet Bode plots at your actual gain setting. Avoid long traces "
        "on inverting input that add parasitic capacitance.",
        "category": "design_rule",
    },
    {
        "topic": "feedback_compensation",
        "title": "Feedback Loop Compensation",
        "content": "Type I compensation (integrator): adds a pole at origin for zero steady-state error. "
        "Type II adds a zero for phase boost. Type III adds two zeros for aggressive phase boost. "
        "Place the crossover frequency at 1/5 to 1/10 of switching frequency for power supplies.",
        "category": "design_rule",
    },
    {
        "topic": "current_sensing_techniques",
        "title": "Current Sensing Techniques",
        "content": "Low-side sensing is simpler but loses ground reference. High-side sensing preserves "
        "ground but needs differential or current-sense amplifier. Shunt resistor value trades "
        "accuracy (larger) vs power loss (smaller). Consider Hall-effect sensors for high "
        "current (>20A) to avoid shunt losses.",
        "category": "design_rule",
    },
    {
        "topic": "battery_management",
        "title": "Battery Management Design",
        "content": "Implement undervoltage lockout to prevent deep discharge. Monitor cell voltages "
        "individually in series packs. Include cell balancing for multi-cell Li-ion. Set "
        "charge termination at 4.2V per cell for Li-ion. Add thermal protection with NTC "
        "on the pack. Use dedicated BMS IC for safety certification.",
        "category": "design_rule",
    },
    {
        "topic": "motor_driving_basics",
        "title": "Motor Driving Design",
        "content": "Size MOSFETs for worst-case stall current (5-10x running current). Add bootstrap "
        "capacitors for high-side gate drive. Use dead-time to prevent shoot-through in H-bridge. "
        "Place snubber networks across switches for inductive loads. Decouple motor supply "
        "close to the driver IC.",
        "category": "design_rule",
    },
    {
        "topic": "rf_layout_guidelines",
        "title": "RF Layout Guidelines",
        "content": "Maintain 50-ohm impedance on RF traces (use microstrip calculator). Keep RF traces "
        "as short as possible. Use coplanar waveguide with ground for better shielding. "
        "Place matching components at the antenna feed. Shield RF sections with ground plane "
        "stitching vias every lambda/20.",
        "category": "design_rule",
    },
    {
        "topic": "crystal_oscillator_layout",
        "title": "Crystal Oscillator Layout",
        "content": "Place crystal as close as possible to the MCU/IC oscillator pins. Keep load capacitor "
        "traces short and symmetric. Guard-ring the crystal with ground to reduce coupling. "
        "Do not route signals under the crystal. Use ground plane beneath the oscillator circuit.",
        "category": "design_rule",
    },
    {
        "topic": "connector_selection",
        "title": "Connector Selection Guidelines",
        "content": "Derate connector current ratings by 50% for reliability. Ensure adequate pin count "
        "for power (multiple pins paralleled). Choose gold-plated contacts for low-level signals. "
        "Consider mating cycles (USB-C: 10,000, board-to-board: 30-100). Include keying to "
        "prevent reverse insertion. Add TVS protection on external connectors.",
        "category": "design_rule",
    },
    {
        "topic": "thermal_vias",
        "title": "Thermal Via Design",
        "content": "Use thermal vias under exposed pads to conduct heat to inner copper planes. "
        "Recommended: 0.3mm drill, 0.6mm pad, array with 1.2mm pitch. Fill or cap vias to "
        "prevent solder wicking during reflow. 9-16 vias under a typical QFN pad provides "
        "adequate thermal path. Connect to large copper area on opposite side.",
        "category": "design_rule",
    },
    {
        "topic": "differential_pair_routing",
        "title": "Differential Pair Routing",
        "content": "Maintain constant spacing between differential pair traces. Match trace lengths to "
        "within 5 mils for high-speed signals. Keep pairs tightly coupled — spacing equal to "
        "trace width. Route pairs on the same layer. Avoid splitting pairs across vias. "
        "Use differential impedance calculator (typically 90-100 ohm).",
        "category": "design_rule",
    },
    {
        "topic": "impedance_controlled_routing",
        "title": "Impedance-Controlled Routing",
        "content": "Standard single-ended impedance is 50 ohm. Calculate trace width using stackup "
        "parameters (Er, height, copper weight). Control impedance to +/-10% tolerance. "
        "Specify impedance requirements in PCB fabrication notes. Request TDR testing "
        "on impedance-controlled nets for validation.",
        "category": "design_rule",
    },
    {
        "topic": "digital_ic_decoupling",
        "title": "Digital IC Decoupling Strategy",
        "content": "Use 100nF MLCC per power pin, placed within 2mm of pin. Add 1-10uF bulk cap per "
        "IC or group of ICs. For FPGAs and processors: use the vendor's recommended decoupling "
        "network (often 10+ caps). Consider embedded capacitance in PCB stackup for GHz designs. "
        "Route power through cap to pin, not as a tap.",
        "category": "design_rule",
    },
    {
        "topic": "power_plane_partitioning",
        "title": "Power Plane Partitioning",
        "content": "Assign dedicated power planes in multilayer PCBs. Keep power and ground planes adjacent "
        "for maximum decoupling capacitance. Split power planes for different voltage domains. "
        "Ensure return current paths are not interrupted by splits. Bridge plane splits with "
        "0-ohm resistors or ferrite beads where signals cross.",
        "category": "design_rule",
    },
    {
        "topic": "ferrite_bead_selection",
        "title": "Ferrite Bead Selection",
        "content": "Select ferrite beads based on impedance at the noise frequency, not just DC resistance. "
        "Check impedance curves — beads are resistive above their rated frequency. Ensure DC "
        "current rating exceeds expected load. Low-DCR beads for power lines, high-impedance "
        "for signal filtering. Avoid saturating ferrite with DC bias current.",
        "category": "design_rule",
    },
    {
        "topic": "esd_protection_strategy",
        "title": "ESD Protection Strategy",
        "content": "Add TVS diodes on all external-facing connectors and IOs. Use low-capacitance TVS "
        "for high-speed data lines (USB, HDMI). Place TVS as close to connector as possible. "
        "Size series resistors to limit peak current into IC protection diodes. Consider "
        "IEC 61000-4-2 levels: contact ±4kV, air ±8kV minimum.",
        "category": "design_rule",
    },
    {
        "topic": "test_point_placement",
        "title": "Test Point Placement",
        "content": "Add test points on all power rails and key signals. Place test points on a grid "
        "for automated test fixtures. Use 50-mil round pads for manual probing, 35-mil for "
        "automated. Include ground test points near signal test points for differential probing. "
        "Label test points in silkscreen. Include JTAG/SWD access.",
        "category": "design_rule",
    },
    {
        "topic": "led_thermal_design",
        "title": "LED Thermal Design",
        "content": "Calculate LED thermal resistance from junction to ambient. Ensure junction temperature "
        "stays below maximum (typically 125C). Provide thermal pad connected to copper area for "
        "high-power LEDs. Derate LED current at elevated ambient temperatures. Account for "
        "thermal resistance of solder joint, PCB, and enclosure.",
        "category": "design_rule",
    },
    {
        "topic": "pcb_stackup_design",
        "title": "PCB Stackup Design",
        "content": "4-layer minimum for mixed-signal designs: Signal-Ground-Power-Signal. 6-layer for "
        "high-speed: Sig-Gnd-Sig-Sig-Pwr-Sig. Keep signal layers adjacent to reference planes. "
        "Maintain symmetric stackup for manufacturing. Use core/prepreg thicknesses that give "
        "target impedance. Specify stackup in fab notes with impedance targets.",
        "category": "design_rule",
    },
]


def build_design_rules(db: Database, rules: list[dict] | None = None) -> dict:
    """Insert design rules into the knowledge database.

    Returns stats dict.
    """
    if rules is None:
        rules = DESIGN_RULES

    stats = {"created": 0, "skipped": 0}

    for rule in rules:
        entry_id = str(uuid.uuid4())
        created = False
        with db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM knowledge WHERE topic = ?",
                (rule["topic"],),
            ).fetchone()
            if existing:
                stats["skipped"] += 1
                continue

            conn.execute(
                "INSERT INTO knowledge (id, category, topic, title, content, "
                "formulas, related_topics, difficulty, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'design_rules')",
                (
                    entry_id,
                    rule["category"],
                    rule["topic"],
                    rule["title"],
                    rule["content"],
                    json.dumps([]),
                    json.dumps([]),
                    "intermediate",
                ),
            )
            created = True

        if created:
            record_provenance(
                db,
                "knowledge",
                entry_id,
                "design_rules",
                licence="original",
                notes=f"Design rule: {rule['topic']}",
            )
            stats["created"] += 1

    return stats
