"""
EnclosureAI — Pydantic Input Schemas

All user-facing input models with strict validation.
These define the API contract for enclosure generation requests.

Models:
    - ComponentType, FaceAccess, LidStyle, PrintMaterial, PrintTechnology, AestheticStyle (enums)
    - ComponentSpec, PCBSpec (component models)
    - EnclosureRequest (top-level request model)
    - PRESETS dict (ESP32, Arduino Uno, Raspberry Pi 4)
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.core.design_context import DesignContext


# ═══════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════

class ComponentType(str, Enum):
    """Type of electronic component on the PCB."""
    CONNECTOR = "CONNECTOR"
    DISPLAY = "DISPLAY"
    BUTTON = "BUTTON"
    HEATSINK = "HEATSINK"
    ANTENNA = "ANTENNA"
    GENERIC = "GENERIC"


class FaceAccess(str, Enum):
    """Which enclosure face a component needs external access through."""
    NONE = "NONE"
    FRONT = "FRONT"
    BACK = "BACK"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"


class LidStyle(str, Enum):
    """Lid attachment mechanism."""
    SNAP_FIT = "SNAP_FIT"
    SCREWED_M2 = "SCREWED_M2"
    SCREWED_M3 = "SCREWED_M3"
    SLIDE = "SLIDE"
    FRICTION = "FRICTION"


class PrintMaterial(str, Enum):
    """3D printing material selection."""
    PLA = "PLA"
    PETG = "PETG"
    ABS = "ABS"
    ASA = "ASA"
    PC = "PC"
    SLA_STANDARD = "SLA_STANDARD"
    SLA_TOUGH = "SLA_TOUGH"


class PrintTechnology(str, Enum):
    """3D printing technology."""
    FDM = "FDM"
    SLA = "SLA"
    SLS = "SLS"


class AestheticStyle(str, Enum):
    """Visual style for the enclosure exterior."""
    MINIMAL = "MINIMAL"
    INDUSTRIAL = "INDUSTRIAL"
    CONSUMER = "CONSUMER"
    ROUNDED = "ROUNDED"
    WEARABLE = "WEARABLE"


# ═══════════════════════════════════════════════════════════════
# Component Models
# ═══════════════════════════════════════════════════════════════

class ComponentSpec(BaseModel):
    """
    Specification for a single component on the PCB.
    Components with face_access != NONE will generate cutouts.
    Components with wattage >= 1.0W will generate dedicated thermal vent zones.
    """
    component_type: ComponentType
    label: str = "component"
    position_x: float = Field(..., ge=0, description="mm from PCB left edge")
    position_y: float = Field(..., ge=0, description="mm from PCB bottom edge")
    height: float = Field(..., gt=0, le=100, description="mm above PCB surface")
    wattage: float = Field(0.0, ge=0, description="power dissipation in watts")
    face_access: FaceAccess = FaceAccess.NONE
    connector_width: Optional[float] = Field(
        None, gt=0, le=100, description="mm — required if component_type=CONNECTOR"
    )
    connector_height: Optional[float] = Field(
        None, gt=0, le=100, description="mm — required if component_type=CONNECTOR"
    )

    @model_validator(mode="after")
    def validate_connector_dimensions(self):
        """Connectors with face access must have width and height specified."""
        if (
            self.component_type == ComponentType.CONNECTOR
            and self.face_access != FaceAccess.NONE
        ):
            if self.connector_width is None or self.connector_height is None:
                raise ValueError(
                    "Connectors with face_access must specify "
                    "connector_width and connector_height"
                )
        return self


# ═══════════════════════════════════════════════════════════════
# PCB Specification
# ═══════════════════════════════════════════════════════════════

class PCBSpec(BaseModel):
    """
    Physical dimensions of the printed circuit board.
    Mounting hole positions are optional — if not provided, the engine
    auto-generates 4 corner standoffs.
    """
    length: float = Field(..., ge=10, le=500, description="PCB length in mm")
    width: float = Field(..., ge=10, le=500, description="PCB width in mm")
    thickness: float = Field(1.6, ge=0.8, le=4.0, description="PCB thickness in mm")
    mounting_hole_diameter: float = Field(
        3.2, ge=2.0, le=5.0, description="Mounting hole diameter in mm"
    )
    mounting_hole_positions: Optional[list[tuple[float, float]]] = Field(
        None, description="List of (x, y) mounting hole positions in mm from PCB origin"
    )


# ═══════════════════════════════════════════════════════════════
# Enclosure Generation Request
# ═══════════════════════════════════════════════════════════════

class EnclosureRequest(BaseModel):
    """
    Top-level request model for enclosure generation.
    If preset is specified, it overrides pcb dimensions and components.
    """
    pcb: PCBSpec
    components: list[ComponentSpec] = []
    material: PrintMaterial = PrintMaterial.PETG
    print_technology: PrintTechnology = PrintTechnology.FDM
    lid_style: LidStyle = LidStyle.SNAP_FIT
    ventilation: bool = True
    display_window: bool = False
    aesthetic_style: AestheticStyle = AestheticStyle.MINIMAL
    design_context: Optional[DesignContext] = Field(
        default_factory=DesignContext,
        description="Design intent context for topology selection. "
                    "Defaults to BENCH_PROTOTYPE / RARELY / DESKTOP / INDOOR.",
    )
    preset: Optional[str] = Field(
        None, description="Board preset: 'ESP32' | 'ARDUINO_UNO' | 'RPI4'"
    )


# ═══════════════════════════════════════════════════════════════
# Board Presets
# ═══════════════════════════════════════════════════════════════

PRESETS: dict[str, dict] = {
    "ESP32": {
        "pcb": {
            "length": 51.0,
            "width": 25.0,
            "thickness": 1.6,
            "mounting_hole_diameter": 3.2,
            "mounting_hole_positions": [
                (2.5, 2.5),
                (48.5, 2.5),
                (2.5, 22.5),
                (48.5, 22.5),
            ],
        },
        "components": [
            {
                "component_type": "CONNECTOR",
                "label": "USB-C",
                "position_x": 25.5,
                "position_y": 0.0,
                "height": 3.5,
                "wattage": 0.0,
                "face_access": "FRONT",
                "connector_width": 9.0,
                "connector_height": 3.5,
            },
            {
                "component_type": "ANTENNA",
                "label": "WiFi Antenna",
                "position_x": 45.0,
                "position_y": 12.5,
                "height": 2.0,
                "wattage": 0.3,
                "face_access": "NONE",
            },
            {
                "component_type": "GENERIC",
                "label": "Voltage Regulator",
                "position_x": 10.0,
                "position_y": 12.5,
                "height": 2.0,
                "wattage": 1.5,
                "face_access": "NONE",
            },
        ],
    },
    "ARDUINO_UNO": {
        "pcb": {
            "length": 68.6,
            "width": 53.4,
            "thickness": 1.6,
            "mounting_hole_diameter": 3.2,
            "mounting_hole_positions": [
                (14.0, 2.54),
                (66.04, 7.62),
                (66.04, 35.56),
                (15.24, 50.8),
            ],
        },
        "components": [
            {
                "component_type": "CONNECTOR",
                "label": "USB-B",
                "position_x": 11.5,
                "position_y": 0.0,
                "height": 11.0,
                "wattage": 0.0,
                "face_access": "BACK",
                "connector_width": 12.0,
                "connector_height": 11.0,
            },
            {
                "component_type": "CONNECTOR",
                "label": "Barrel Jack",
                "position_x": 0.0,
                "position_y": 7.0,
                "height": 11.0,
                "wattage": 0.0,
                "face_access": "LEFT",
                "connector_width": 9.0,
                "connector_height": 11.0,
            },
            {
                "component_type": "GENERIC",
                "label": "ATmega328P",
                "position_x": 34.0,
                "position_y": 20.0,
                "height": 3.0,
                "wattage": 0.5,
                "face_access": "NONE",
            },
            {
                "component_type": "GENERIC",
                "label": "Voltage Regulator",
                "position_x": 5.0,
                "position_y": 22.0,
                "height": 8.0,
                "wattage": 2.0,
                "face_access": "NONE",
            },
        ],
    },
    "RPI4": {
        "pcb": {
            "length": 85.0,
            "width": 56.0,
            "thickness": 1.6,
            "mounting_hole_diameter": 2.75,
            "mounting_hole_positions": [
                (3.5, 3.5),
                (61.5, 3.5),
                (3.5, 52.5),
                (61.5, 52.5),
            ],
        },
        "components": [
            {
                "component_type": "CONNECTOR",
                "label": "USB-C Power",
                "position_x": 11.2,
                "position_y": 0.0,
                "height": 3.2,
                "wattage": 0.0,
                "face_access": "FRONT",
                "connector_width": 9.0,
                "connector_height": 3.2,
            },
            {
                "component_type": "CONNECTOR",
                "label": "Micro HDMI 1",
                "position_x": 26.0,
                "position_y": 0.0,
                "height": 3.2,
                "wattage": 0.0,
                "face_access": "FRONT",
                "connector_width": 7.0,
                "connector_height": 3.2,
            },
            {
                "component_type": "CONNECTOR",
                "label": "Micro HDMI 2",
                "position_x": 39.5,
                "position_y": 0.0,
                "height": 3.2,
                "wattage": 0.0,
                "face_access": "FRONT",
                "connector_width": 7.0,
                "connector_height": 3.2,
            },
            {
                "component_type": "CONNECTOR",
                "label": "USB-A Ports (×2)",
                "position_x": 85.0,
                "position_y": 21.5,
                "height": 16.0,
                "wattage": 0.0,
                "face_access": "RIGHT",
                "connector_width": 15.0,
                "connector_height": 16.0,
            },
            {
                "component_type": "CONNECTOR",
                "label": "USB-A Ports (×2) Upper",
                "position_x": 85.0,
                "position_y": 39.0,
                "height": 16.0,
                "wattage": 0.0,
                "face_access": "RIGHT",
                "connector_width": 15.0,
                "connector_height": 16.0,
            },
            {
                "component_type": "CONNECTOR",
                "label": "Ethernet",
                "position_x": 85.0,
                "position_y": 7.5,
                "height": 13.5,
                "wattage": 0.0,
                "face_access": "RIGHT",
                "connector_width": 16.0,
                "connector_height": 13.5,
            },
            {
                "component_type": "HEATSINK",
                "label": "BCM2711 SoC",
                "position_x": 32.5,
                "position_y": 32.5,
                "height": 2.5,
                "wattage": 3.5,
                "face_access": "NONE",
            },
            {
                "component_type": "CONNECTOR",
                "label": "3.5mm Audio Jack",
                "position_x": 53.5,
                "position_y": 0.0,
                "height": 6.0,
                "wattage": 0.0,
                "face_access": "FRONT",
                "connector_width": 7.0,
                "connector_height": 6.0,
            },
        ],
    },
}
