"""
EnclosureAI — Design Context Schema (Phase 8)

Enums and Pydantic model defining the design intent context.
The Design Strategy Selector uses these values DETERMINISTICALLY
to choose enclosure topology — the LLM is never asked to choose.

Enums:
    - UseCase: intended product lifecycle stage
    - AccessFrequency: how often the enclosure is opened
    - MountingStyle: physical mounting / form factor
    - Environment: operating environment constraints

Model:
    - DesignContext: composite of all four enums with safe defaults
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Use Case Enum
# ═══════════════════════════════════════════════════════════════

class UseCase(str, Enum):
    """Intended product lifecycle stage / use case category."""
    BENCH_PROTOTYPE = "BENCH_PROTOTYPE"
    IOT_DEVICE = "IOT_DEVICE"
    INDUSTRIAL_CONTROLLER = "INDUSTRIAL_CONTROLLER"
    CONSUMER_PRODUCT = "CONSUMER_PRODUCT"
    WEARABLE = "WEARABLE"
    SCIENTIFIC_INSTRUMENT = "SCIENTIFIC_INSTRUMENT"


# ═══════════════════════════════════════════════════════════════
# Access Frequency Enum
# ═══════════════════════════════════════════════════════════════

class AccessFrequency(str, Enum):
    """How often the enclosure needs to be opened for maintenance."""
    RARELY = "RARELY"           # Sealed after assembly
    MONTHLY = "MONTHLY"         # Periodic maintenance
    WEEKLY = "WEEKLY"           # Regular access
    DAILY = "DAILY"             # Frequent access — needs tool-less opening


# ═══════════════════════════════════════════════════════════════
# Mounting Style Enum
# ═══════════════════════════════════════════════════════════════

class MountingStyle(str, Enum):
    """Physical mounting method / form factor constraint."""
    DESKTOP = "DESKTOP"             # Sits on a surface
    WALL_MOUNT = "WALL_MOUNT"       # Screw-mount to wall
    DIN_RAIL = "DIN_RAIL"           # Clips onto 35mm DIN rail
    PANEL_CUTOUT = "PANEL_CUTOUT"   # Mounts in panel cutout with bezel
    HANDHELD = "HANDHELD"           # Held in hand
    WEARABLE = "WEARABLE"           # Worn on body


# ═══════════════════════════════════════════════════════════════
# Environment Enum
# ═══════════════════════════════════════════════════════════════

class Environment(str, Enum):
    """Operating environment affecting sealing and material choices."""
    INDOOR = "INDOOR"                   # Normal indoor conditions
    INDOOR_INDUSTRIAL = "INDOOR_INDUSTRIAL"  # Dust, vibration, wider temp range
    OUTDOOR = "OUTDOOR"                 # Rain, UV, temperature extremes
    WET_HUMID = "WET_HUMID"             # Submersion risk, high humidity


# ═══════════════════════════════════════════════════════════════
# Design Context Model
# ═══════════════════════════════════════════════════════════════

class DesignContext(BaseModel):
    """
    Composite design intent context.
    
    All fields default to the safest, most generic values
    (BENCH_PROTOTYPE / RARELY / DESKTOP / INDOOR) which produce
    the standard rectangular flat-lid enclosure — maintaining
    full backward compatibility with existing API calls.
    """
    use_case: UseCase = Field(
        default=UseCase.BENCH_PROTOTYPE,
        description="Intended product lifecycle stage",
    )
    access_frequency: AccessFrequency = Field(
        default=AccessFrequency.RARELY,
        description="How often the enclosure is opened",
    )
    mounting: MountingStyle = Field(
        default=MountingStyle.DESKTOP,
        description="Physical mounting method",
    )
    environment: Environment = Field(
        default=Environment.INDOOR,
        description="Operating environment",
    )
