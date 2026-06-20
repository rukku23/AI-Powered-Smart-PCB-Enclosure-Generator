"""
EnclosureAI — Constraint Schemas
Internal computed data models produced by the Constraint Engine.
These are NOT user-facing — they are the validated intermediate representation
passed directly into the LLM prompt builder.

All values in these schemas are pre-computed by the deterministic Constraint
Engine. The LLM uses these numbers verbatim — it never computes dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.schemas.input_schemas import PCBSpec


@dataclass
class EnclosureDimensions:
    """
    Computed outer and inner dimensions of the enclosure.
    Inner dimensions are derived: inner = outer - 2*wall.
    """
    outer_length: float
    outer_width: float
    outer_height: float
    wall: float
    clearance: float
    lid_thickness: float
    inner_length: float    # computed: outer_length - 2*wall
    inner_width: float     # computed: outer_width - 2*wall
    inner_height: float    # computed: outer_height - wall - lid_thickness


@dataclass
class StandoffSpec:
    """Single standoff position and dimensions in enclosure coordinate space."""
    x: float                # position in enclosure coordinate space
    y: float
    inner_diameter: float   # M2=2.2, M3=3.2, M4=4.2
    outer_diameter: float   # inner_diameter * 2
    height: float
    fastener_type: str      # "M2", "M3", "M4"


@dataclass
class CutoutSpec:
    """
    Connector cutout specification on an enclosure face.
    Positions are in the face's local coordinate system.
    """
    face: str               # "FRONT", "BACK", "LEFT", "RIGHT", "TOP"
    x_start: float          # position along face width axis
    x_end: float
    z_start: float          # position along face height axis
    z_end: float
    label: str
    component_type: str


@dataclass
class ThermalZone:
    """
    Thermal vent zone for a high-wattage component.
    Only components with wattage >= THERMAL_VENT_MIN_WATTAGE (1.0W) generate zones.
    """
    centre_x: float         # enclosure coordinate space
    centre_y: float
    radius: float
    face: str               # default "TOP" — hot air rises
    priority: float         # wattage — higher = more critical
    required_vent_area: float  # m²


@dataclass
class SnapFitSpec:
    """Snap-fit tab parameters distributed around the enclosure perimeter."""
    tab_count: int
    cantilever_length: float
    gap: float
    positions: list[dict] = field(default_factory=list)  # [{face, offset_from_start}]


@dataclass
class VentSpec:
    """Computed vent slot parameters for the enclosure."""
    slot_count: int
    slot_width: float       # mm
    slot_length: float      # mm
    slot_spacing: float     # mm
    total_area_m2: float    # total implemented vent area
    face: str = "TOP"


@dataclass
class ConstraintSchema:
    """
    Complete validated constraint set passed to the LLM prompt builder.
    ALL numeric values are pre-computed by the Constraint Engine.
    The LLM receives this as JSON and writes OpenSCAD code using these values directly.
    """
    pcb: PCBSpec
    enclosure: EnclosureDimensions
    standoffs: list[StandoffSpec]
    cutouts: list[CutoutSpec]
    thermal_zones: list[ThermalZone]
    snap_fit: Optional[SnapFitSpec]
    vent_spec: Optional[VentSpec]
    material: str
    print_technology: str
    lid_style: str
    total_wattage: float
    max_component_height: float
    thermal_data: dict = field(default_factory=dict)
    topology_params: dict = field(default_factory=dict)
    design_context: dict = field(default_factory=dict)
    ventilation_enabled: bool = True
    strategy_name: str = "RECTANGULAR_FLAT_LID"
    topology_extensions: dict = field(default_factory=dict)
