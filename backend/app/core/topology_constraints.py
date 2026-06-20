"""
EnclosureAI — Topology Constraint Extensions (Phase 8)

Adds strategy-specific computed values to the ConstraintSchema.
Each topology requires additional parameters beyond the base
enclosure dimensions — these are computed deterministically here.

Examples:
  - CLAMSHELL_HORIZONTAL needs half_height, hinge position, latch position
  - DIN_RAIL_CLIP needs fixed DIN standard dimensions (35mm width)
  - CHIMNEY_THERMAL needs chimney dimensions based on thermal zones
  - WEARABLE_ROUNDED needs corner radius, edge fillet, band lug dims
"""

from __future__ import annotations

import logging
import math

from app.core.strategy_selector import DesignStrategy
from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.core.topology_constraints")


def apply_topology_extensions(
    strategy: DesignStrategy,
    base_constraints: ConstraintSchema,
) -> ConstraintSchema:
    """
    Add strategy-specific computed values to the constraint schema.

    Modifies base_constraints.topology_extensions dict in-place
    and returns the updated schema.

    Each strategy dispatches to its own computation function.
    Strategies without extensions return the schema unchanged.
    """
    name = getattr(strategy, "name", getattr(strategy, "topology_name", "RECTANGULAR_FLAT_LID"))
    ext = base_constraints.topology_extensions
    base_constraints.strategy_name = name

    dispatch = {
        "CLAMSHELL_HORIZONTAL": _compute_clamshell_horizontal,
        "CLAMSHELL_VERTICAL": _compute_clamshell_vertical,
        "DIN_RAIL_CLIP": _compute_din_rail_clip,
        "CHIMNEY_THERMAL": _compute_chimney_thermal,
        "WEARABLE_ROUNDED": _compute_wearable_rounded,
        "SEALED_IP_RATED": _compute_sealed_ip_rated,
    }

    compute_fn = dispatch.get(name)
    if compute_fn:
        compute_fn(base_constraints, ext)
        logger.info(
            f"Topology extensions applied for {name}: "
            f"{list(ext.keys())}"
        )
    else:
        logger.info(f"No topology extensions needed for {name}")

    return base_constraints


# ═══════════════════════════════════════════════════════════════
# CLAMSHELL_HORIZONTAL Extensions
# ═══════════════════════════════════════════════════════════════

def _compute_clamshell_horizontal(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """
    Clamshell horizontal split - compute split plane and feature positions.

    half_height: Z position of the split plane (midpoint of outer height)
    hinge: on the BACK edge, centered
    latch: on the FRONT edge, centered
    pcb_groove: side-wall grooves to hold PCB without standoffs
    """
    enc = constraints.enclosure

    # Split plane at half the outer height
    ext["half_height"] = round(enc.outer_height / 2, 2)

    # Hinge on back edge, centered along length
    ext["hinge_x"] = round(enc.outer_length / 2, 2)
    ext["hinge_z"] = ext["half_height"]

    # Latch on front edge, centered along length
    ext["latch_x"] = round(enc.outer_length / 2, 2)
    ext["latch_y"] = 0.0  # Front face

    # PCB groove in side walls
    # Groove sits at standoff height + wall thickness
    standoff_h = constraints.standoffs[0].height if constraints.standoffs else 5.0
    ext["pcb_groove_z"] = round(enc.wall + standoff_h, 2)
    ext["pcb_groove_depth"] = 1.5   # mm into the wall
    ext["pcb_groove_width"] = round(constraints.pcb.thickness + 0.4, 2)  # PCB + tolerance


def _compute_clamshell_vertical(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """Vertical clamshell - same params, different orientation."""
    _compute_clamshell_horizontal(constraints, ext)
    # Override hinge to top edge for vertical split
    ext["hinge_z"] = constraints.enclosure.outer_height


# ═══════════════════════════════════════════════════════════════
# DIN_RAIL_CLIP Extensions
# ═══════════════════════════════════════════════════════════════

def _compute_din_rail_clip(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """
    DIN rail clip - FIXED standard dimensions per IEC 60715.
    These are NOT computed from enclosure geometry - they are constants.
    """
    ext["din_rail_width"] = 35.0
    ext["din_clip_engagement_depth"] = 5.5
    ext["din_clip_spring_length"] = 14.0
    ext["din_clip_release_tab_height"] = 8.0


# ═══════════════════════════════════════════════════════════════
# CHIMNEY_THERMAL Extensions
# ═══════════════════════════════════════════════════════════════

def _compute_chimney_thermal(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """
    Chimney thermal - compute chimney position and dimensions
    based on the hottest thermal zone.
    """
    enc = constraints.enclosure

    if constraints.thermal_zones:
        # Position chimney above the hottest zone (first = highest priority)
        hottest = constraints.thermal_zones[0]
        ext["chimney_x"] = hottest.centre_x
        ext["chimney_y"] = hottest.centre_y
    else:
        # Default to centre if no thermal zones
        ext["chimney_x"] = round(enc.outer_length / 2, 2)
        ext["chimney_y"] = round(enc.outer_width / 2, 2)

    # Chimney dimensions scale with total wattage
    total_w = constraints.total_wattage
    # Width/length: min 15mm, scales with wattage
    chimney_size = min(40.0, max(15.0, total_w * 3.0))
    ext["chimney_width"] = round(chimney_size, 2)
    ext["chimney_length"] = round(chimney_size, 2)

    # Chimney height: taller for more wattage (stack effect)
    ext["chimney_height"] = round(min(50.0, max(15.0, total_w * 4.0)), 2)

    # Intake slots near base on front face
    ext["intake_slot_z"] = round(enc.wall + 2.0, 2)
    ext["intake_face"] = "FRONT"


# ═══════════════════════════════════════════════════════════════
# WEARABLE_ROUNDED Extensions
# ═══════════════════════════════════════════════════════════════

def _compute_wearable_rounded(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """
    Wearable rounded - compute corner radius and band lug dimensions.
    """
    enc = constraints.enclosure

    # Corner radius: ~25% of the smallest horizontal dimension
    min_dim = min(enc.outer_length, enc.outer_width)
    ext["corner_radius"] = round(min(min_dim * 0.25, 10.0), 2)

    # Edge fillet: ~15% of outer height
    ext["edge_fillet"] = round(min(enc.outer_height * 0.15, 3.0), 2)

    # Band lugs on left and right sides
    ext["band_lug_width"] = 8.0    # Standard watch band lug width
    ext["band_lug_height"] = 4.0   # Protrusion height


# ═══════════════════════════════════════════════════════════════
# SEALED_IP_RATED Extensions
# ═══════════════════════════════════════════════════════════════

def _compute_sealed_ip_rated(
    constraints: ConstraintSchema,
    ext: dict[str, float],
) -> None:
    """
    Sealed IP-rated - compute O-ring groove, cable gland, and flange dims.
    """
    enc = constraints.enclosure

    # O-ring groove (standard 2mm cross-section O-ring)
    ext["oring_cross_section"] = 2.0
    ext["oring_groove_width"] = 2.8    # ~1.4x cross section
    ext["oring_groove_depth"] = 1.5    # ~0.75x cross section

    # Cable gland hole (M16 standard for most cables)
    ext["cable_gland_od"] = 16.0

    # Lid flange width (enough for O-ring groove + screw clearance)
    ext["lid_flange_width"] = 8.0

    # Screw count: one per ~40mm perimeter
    perimeter = 2 * (enc.outer_length + enc.outer_width)
    ext["screw_count"] = float(max(4, math.floor(perimeter / 40.0)))
