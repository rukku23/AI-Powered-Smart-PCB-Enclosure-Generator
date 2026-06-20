"""
EnclosureAI — Engineering Constants

All hardcoded engineering values used by the constraint engine,
thermal engine, and DFM validator. These are NON-NEGOTIABLE values
derived from the project specification.

RULE: The LLM never computes dimensions. These constants feed
deterministic Python calculations only.
"""

# ═══════════════════════════════════════════════════════════════
# Geometric Constants (mm)
# ═══════════════════════════════════════════════════════════════

PCB_TO_WALL_CLEARANCE = 3.0       # mm — minimum clearance, all sides
STANDOFF_CORNER_OFFSET = 6.0      # mm — from PCB corner to standoff centre
CONNECTOR_CUTOUT_MARGIN = 2.0     # mm — added each side of connector width/height

# ═══════════════════════════════════════════════════════════════
# Thermal Constants
# ═══════════════════════════════════════════════════════════════

NATURAL_CONVECTION_H = 10.0       # W/(m²·K) — convection coefficient
FORCED_CONVECTION_H = 25.0        # W/(m²·K) — with fan
AMBIENT_TEMP_CONSERVATIVE = 25.0  # °C
COMPONENT_SAFE_TEMP = 70.0        # °C — 15°C below 85°C IC limit
DELTA_T = 45.0                    # °C — COMPONENT_SAFE_TEMP - AMBIENT

THERMAL_VENT_MIN_WATTAGE = 1.0    # W — components below this don't get dedicated vents
THERMAL_VENT_RADIUS = 20.0        # mm — vent cluster radius around hotspot

# ═══════════════════════════════════════════════════════════════
# Vent Slot Geometry (mm)
# ═══════════════════════════════════════════════════════════════

VENT_SLOT_WIDTH = 2.5             # mm — printable without bridging on FDM
VENT_SLOT_LENGTH = 15.0           # mm
VENT_SLOT_SPACING = 4.0           # mm — structural web between slots

# ═══════════════════════════════════════════════════════════════
# Snap-Fit Constants
# ═══════════════════════════════════════════════════════════════

SNAP_FIT_TAB_SPACING = 60.0       # mm — one tab per 60mm perimeter
SNAP_FIT_MIN_TABS = 4

# ═══════════════════════════════════════════════════════════════
# System Limits
# ═══════════════════════════════════════════════════════════════

MAX_RETRY_ATTEMPTS = 3
STL_PREVIEW_MAX_TRIANGLES = 50000

# ═══════════════════════════════════════════════════════════════
# DFM Rules Table — Material-Specific Manufacturing Constraints
# ═══════════════════════════════════════════════════════════════

DFM_RULES: dict[str, dict] = {
    "PLA": {
        "min_wall_thickness": 1.2,        # mm
        "min_feature_size": 0.8,           # mm
        "max_overhang_angle": 45,          # degrees from vertical
        "snap_fit_gap_per_mm": 0.25,       # mm gap per mm cantilever
        "snap_fit_min_length": 15,         # mm
        "snap_fit_max_deflection": 0.02,   # mm/mm (2% of cantilever length)
        "glass_transition_temp": 60,       # °C — max continuous operating temp
        "screw_boss_wall_multiplier": 1.5,
        "recommended_layer_height": 0.2,   # mm
    },
    "PETG": {
        "min_wall_thickness": 1.2,
        "min_feature_size": 0.8,
        "max_overhang_angle": 45,
        "snap_fit_gap_per_mm": 0.30,
        "snap_fit_min_length": 12,
        "snap_fit_max_deflection": 0.025,
        "glass_transition_temp": 80,
        "screw_boss_wall_multiplier": 1.5,
        "recommended_layer_height": 0.25,
    },
    "ABS": {
        "min_wall_thickness": 1.5,
        "min_feature_size": 1.0,
        "max_overhang_angle": 50,
        "snap_fit_gap_per_mm": 0.20,
        "snap_fit_min_length": 10,
        "snap_fit_max_deflection": 0.03,
        "glass_transition_temp": 105,
        "screw_boss_wall_multiplier": 2.0,
        "recommended_layer_height": 0.2,
    },
    "ASA": {
        "min_wall_thickness": 1.5,
        "min_feature_size": 1.0,
        "max_overhang_angle": 50,
        "snap_fit_gap_per_mm": 0.20,
        "snap_fit_min_length": 10,
        "snap_fit_max_deflection": 0.03,
        "glass_transition_temp": 100,
        "screw_boss_wall_multiplier": 2.0,
        "recommended_layer_height": 0.2,
    },
    "PC": {
        "min_wall_thickness": 1.8,
        "min_feature_size": 1.0,
        "max_overhang_angle": 55,
        "snap_fit_gap_per_mm": 0.15,
        "snap_fit_min_length": 8,
        "snap_fit_max_deflection": 0.025,
        "glass_transition_temp": 147,
        "screw_boss_wall_multiplier": 2.0,
        "recommended_layer_height": 0.2,
    },
    "NYLON": {
        "min_wall_thickness": 1.5,
        "min_feature_size": 1.0,
        "max_overhang_angle": 45,
        "snap_fit_gap_per_mm": 0.20,
        "snap_fit_min_length": 10,
        "snap_fit_max_deflection": 0.04,
        "glass_transition_temp": 80,
        "screw_boss_wall_multiplier": 1.5,
        "recommended_layer_height": 0.2,
    },
    "SLA_STANDARD": {
        "min_wall_thickness": 0.4,
        "min_feature_size": 0.3,
        "max_overhang_angle": 60,
        "snap_fit_gap_per_mm": 0.10,
        "snap_fit_min_length": 8,
        "snap_fit_max_deflection": 0.015,
        "glass_transition_temp": 55,
        "screw_boss_wall_multiplier": 1.2,
        "recommended_layer_height": 0.05,
    },
    "SLA_TOUGH": {
        "min_wall_thickness": 0.4,
        "min_feature_size": 0.3,
        "max_overhang_angle": 60,
        "snap_fit_gap_per_mm": 0.12,
        "snap_fit_min_length": 8,
        "snap_fit_max_deflection": 0.02,
        "glass_transition_temp": 65,
        "screw_boss_wall_multiplier": 1.2,
        "recommended_layer_height": 0.05,
    },
}

# ═══════════════════════════════════════════════════════════════
# Filament Densities (g/cm³) — for BOM generation
# ═══════════════════════════════════════════════════════════════

MATERIAL_DENSITY: dict[str, float] = {
    "PLA": 1.24,
    "PETG": 1.27,
    "ABS": 1.04,
    "ASA": 1.07,
    "PC": 1.20,
    "NYLON": 1.14,
    "SLA_STANDARD": 1.10,
    "SLA_TOUGH": 1.15,
}
