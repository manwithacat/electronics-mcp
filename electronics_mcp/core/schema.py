"""Pydantic models for the circuit description schema.

Implements Master Spec Section 4: Circuit Description Schema.
"""
from pydantic import BaseModel, field_validator
from typing import Any

# Valid component types from the type hierarchy
VALID_COMPONENT_TYPES = {
    # Passive
    "resistor", "capacitor", "inductor", "potentiometer", "fuse", "crystal",
    # Source
    "voltage_source", "current_source", "dependent_source",
    # Semiconductor
    "diode", "zener", "led", "bjt", "mosfet", "jfet", "igbt",
    # Integrated circuit
    "opamp", "comparator", "voltage_regulator", "timer_555", "custom_ic",
    # Subcircuit
    "subcircuit",
    # Transformer
    "transformer",
    # Electromechanical
    "relay", "switch", "connector",
}


class Probe(BaseModel):
    node: str
    label: str


class DesignIntent(BaseModel):
    topology: str | None = None
    target_specs: dict[str, float | str] = {}


class ComponentBase(BaseModel):
    id: str
    type: str
    subtype: str | None = None
    parameters: dict[str, str] = {}
    nodes: list[str] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_COMPONENT_TYPES:
            raise ValueError(
                f"Invalid component type: {v!r}. "
                f"Valid types: {sorted(VALID_COMPONENT_TYPES)}"
            )
        return v

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("Component must connect to at least 2 nodes")
        return v


class Connection(BaseModel):
    from_node: str  # Using from_node instead of from (reserved keyword)
    to: str


class SubcircuitInstance(BaseModel):
    id: str
    reference: str
    parameters: dict[str, str] = {}
    port_connections: dict[str, str] = {}


class CircuitSchema(BaseModel):
    name: str
    description: str | None = None
    design_intent: DesignIntent | None = None
    ground_node: str = "gnd"
    components: list[ComponentBase] = []
    subcircuit_instances: list[SubcircuitInstance] = []
    probes: list[Probe] = []


class ComponentUpdate(BaseModel):
    id: str
    parameters: dict[str, str] = {}
    nodes: list[str] | None = None


class CircuitModification(BaseModel):
    add: list[ComponentBase] = []
    remove: list[str] = []
    update: list[ComponentUpdate] = []
    rename_node: dict[str, str] = {}
    connect: list[Connection] = []
