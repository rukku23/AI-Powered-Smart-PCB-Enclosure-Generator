"""
EnclosureAI — Strategy Library (Phase 8)

All 12 enclosure topology strategies as DesignStrategy dataclass instances.
Each strategy defines the complete specification for one enclosure topology:
topology shape, split method, closure, ventilation, mounting, and the
OpenSCAD modules required to assemble it.

The strategy selector uses `applicable_when` conditions and `score_fn`
to deterministically pick the right strategy for a given DesignContext.

CRITICAL: The LLM never chooses topology. This library is the single
source of truth for what topologies exist and when to use them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from app.core.design_context import (
    AccessFrequency,
    MountingStyle,
    Environment,
    UseCase,
    DesignContext,
)


# ═══════════════════════════════════════════════════════════════
# DesignStrategy Dataclass
# ═══════════════════════════════════════════════════════════════

@dataclass
class DesignStrategy:
    """
    Complete specification for one enclosure topology.

    Used by:
      - StrategySelector: picks one strategy per job
      - TopologyConstraintExtensions: adds computed params
      - StrategyAwarePromptBuilder: constructs LLM prompt
      - OpenSCAD module library: provides parameterised modules
    """
    # ── Identity ──
    topology_name: str                   # e.g. "CLAMSHELL_HORIZONTAL"
    display_name: str                    # e.g. "Clamshell (horizontal split)"

    # ── Geometry ──
    split_axis: str                      # "Z" (horizontal) | "Y" (vertical) | "NONE"
    piece_count: int                     # 2 for most, 3 for THREE_PIECE_ACCESS
    closure_mechanism: str               # "snap_fit" | "screwed" | "hinge_latch" | "slide" | "gasket_screwed"

    # ── Surface / Internal ──
    wall_profile: str                    # "flat" | "ribbed" | "rounded" | "flanged"
    internal_architecture: str           # "standoffs" | "pcb_groove" | "rail_mount" | "press_fit"
    vent_architecture: str               # "top_slots" | "side_louvers" | "chimney" | "sealed" | "perimeter_gap"
    mounting_interface: str              # "none" | "screw_tabs" | "din_clip" | "panel_bezel" | "band_lug"

    # ── Selection ──
    applicable_when: dict                # conditions dict for scoring
    score_fn: Optional[Callable] = None  # (context, constraints) -> float

    # ── DFM ──
    dfm_overrides: dict = field(default_factory=dict)

    # ── OpenSCAD ──
    openscad_module_set: str = ""        # path to strategy's module directory
    openscad_rules: list[str] = field(default_factory=list)

    # ── Constraint Extensions ──
    topology_constraint_extensions: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Score Functions
# ═══════════════════════════════════════════════════════════════

def _score_rectangular_flat(ctx: DesignContext, constraints) -> float:
    """Default fallback. Scores 1.0 for generic bench prototyping."""
    score = 1.0
    if ctx.use_case == UseCase.BENCH_PROTOTYPE:
        score += 2.0
    if ctx.access_frequency == AccessFrequency.RARELY:
        score += 1.0
    if ctx.mounting == MountingStyle.DESKTOP:
        score += 1.0
    return score


def _score_rectangular_ribbed(ctx: DesignContext, constraints) -> float:
    """Ribbed lid variant for industrial desktop use."""
    score = 0.5
    if ctx.use_case == UseCase.INDUSTRIAL_CONTROLLER:
        score += 2.0
    if ctx.environment == Environment.INDOOR_INDUSTRIAL:
        score += 1.5
    if ctx.mounting == MountingStyle.DESKTOP:
        score += 1.0
    return score


def _score_clamshell_horizontal(ctx: DesignContext, constraints) -> float:
    """Clamshell for frequent access / consumer products."""
    score = 0.0
    if ctx.access_frequency == AccessFrequency.DAILY:
        score += 3.0
    elif ctx.access_frequency == AccessFrequency.WEEKLY:
        score += 2.0
    elif ctx.access_frequency == AccessFrequency.MONTHLY:
        score += 1.0
    if ctx.use_case == UseCase.CONSUMER_PRODUCT:
        score += 2.0
    if ctx.use_case == UseCase.IOT_DEVICE:
        score += 1.0
    return score


def _score_clamshell_vertical(ctx: DesignContext, constraints) -> float:
    """Vertical clamshell — wall-mounted consumer."""
    score = 0.0
    if ctx.access_frequency in (AccessFrequency.DAILY, AccessFrequency.WEEKLY):
        score += 2.0
    if ctx.mounting == MountingStyle.WALL_MOUNT:
        score += 2.5
    if ctx.use_case == UseCase.CONSUMER_PRODUCT:
        score += 1.0
    return score


def _score_industrial_flanged(ctx: DesignContext, constraints) -> float:
    """Flanged industrial box for harsh environments."""
    score = 0.0
    if ctx.use_case == UseCase.INDUSTRIAL_CONTROLLER:
        score += 2.0
    if ctx.environment == Environment.INDOOR_INDUSTRIAL:
        score += 2.0
    if ctx.mounting in (MountingStyle.WALL_MOUNT, MountingStyle.DESKTOP):
        score += 1.0
    return score


def _score_din_rail_clip(ctx: DesignContext, constraints) -> float:
    """DIN rail mount — hard override in selector, but scored for completeness."""
    score = 0.0
    if ctx.mounting == MountingStyle.DIN_RAIL:
        score += 10.0  # Effectively a hard override
    return score


def _score_wearable_rounded(ctx: DesignContext, constraints) -> float:
    """Wearable — hard override in selector."""
    score = 0.0
    if ctx.mounting == MountingStyle.WEARABLE:
        score += 10.0
    if ctx.use_case == UseCase.WEARABLE:
        score += 10.0
    return score


def _score_chimney_thermal(ctx: DesignContext, constraints) -> float:
    """Chimney thermal — for high wattage boards."""
    score = 0.0
    total_wattage = getattr(constraints, 'total_wattage', 0)
    if total_wattage > 8.0:
        score += 10.0  # Hard override level
    elif total_wattage > 5.0:
        score += 3.0
    elif total_wattage > 3.0:
        score += 1.0
    return score


def _score_three_piece_access(ctx: DesignContext, constraints) -> float:
    """Three-piece for scientific instruments needing multi-zone access."""
    score = 0.0
    if ctx.use_case == UseCase.SCIENTIFIC_INSTRUMENT:
        score += 3.0
    if ctx.access_frequency == AccessFrequency.DAILY:
        score += 1.5
    return score


def _score_panel_mount_bezel(ctx: DesignContext, constraints) -> float:
    """Panel mount with bezel for panel cutout mounting."""
    score = 0.0
    if ctx.mounting == MountingStyle.PANEL_CUTOUT:
        score += 10.0
    return score


def _score_sealed_ip_rated(ctx: DesignContext, constraints) -> float:
    """Sealed IP-rated for outdoor / wet environments."""
    score = 0.0
    if ctx.environment == Environment.OUTDOOR:
        score += 10.0  # Hard override
    if ctx.environment == Environment.WET_HUMID:
        score += 10.0
    if ctx.use_case == UseCase.INDUSTRIAL_CONTROLLER:
        score += 1.0
    return score


def _score_snap_rail_modular(ctx: DesignContext, constraints) -> float:
    """Snap-rail modular for expandable IoT systems."""
    score = 0.0
    if ctx.use_case == UseCase.IOT_DEVICE:
        score += 1.5
    if ctx.mounting == MountingStyle.DESKTOP:
        score += 0.5
    # Bonus for multiple PCBs (future feature)
    return score


# ═══════════════════════════════════════════════════════════════
# Strategy Library — All 12 Strategies
# ═══════════════════════════════════════════════════════════════

STRATEGY_LIBRARY: dict[str, DesignStrategy] = {

    # ── 1. Rectangular Flat Lid ────────────────────────────────
    "RECTANGULAR_FLAT_LID": DesignStrategy(
        topology_name="RECTANGULAR_FLAT_LID",
        display_name="Rectangular (flat lid)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="snap_fit",
        wall_profile="flat",
        internal_architecture="standoffs",
        vent_architecture="top_slots",
        mounting_interface="none",
        applicable_when={
            "use_case": ["BENCH_PROTOTYPE"],
            "access_frequency": ["RARELY", "MONTHLY"],
            "mounting": ["DESKTOP"],
        },
        score_fn=_score_rectangular_flat,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Body is a hollow cube with wall subtraction",
            "Lid is a flat plate with snap-fit or screw recesses",
            "Place lid translated by outer_length + 10 in X",
        ],
        topology_constraint_extensions=[],
    ),

    # ── 2. Rectangular Ribbed Lid ──────────────────────────────
    "RECTANGULAR_RIBBED_LID": DesignStrategy(
        topology_name="RECTANGULAR_RIBBED_LID",
        display_name="Rectangular (ribbed lid)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="screwed",
        wall_profile="ribbed",
        internal_architecture="standoffs",
        vent_architecture="top_slots",
        mounting_interface="screw_tabs",
        applicable_when={
            "use_case": ["INDUSTRIAL_CONTROLLER"],
            "environment": ["INDOOR_INDUSTRIAL"],
        },
        score_fn=_score_rectangular_ribbed,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Body is a hollow cube with external ribs on long sides",
            "Lid has matching rib pattern for grip",
            "Screwed closure with 4 corner screw bosses",
            "Add 2 screw tabs on back face for wall mounting",
        ],
        topology_constraint_extensions=[],
    ),

    # ── 3. Clamshell Horizontal ────────────────────────────────
    "CLAMSHELL_HORIZONTAL": DesignStrategy(
        topology_name="CLAMSHELL_HORIZONTAL",
        display_name="Clamshell (horizontal split)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="hinge_latch",
        wall_profile="flat",
        internal_architecture="pcb_groove",
        vent_architecture="side_louvers",
        mounting_interface="none",
        applicable_when={
            "access_frequency": ["DAILY", "WEEKLY"],
            "use_case": ["CONSUMER_PRODUCT", "IOT_DEVICE"],
        },
        score_fn=_score_clamshell_horizontal,
        openscad_module_set="strategies/clamshell_horizontal",
        openscad_rules=[
            "Two halves split at Z midpoint (half_height)",
            "Living hinge on back edge (hinge_x, hinge_z)",
            "Front latch clip at (latch_x, latch_y)",
            "PCB held in side grooves (pcb_groove_z, pcb_groove_depth)",
            "Side louver vents instead of top slots",
            "Do NOT use snap-fit tabs — use hinge + latch only",
        ],
        topology_constraint_extensions=[
            "half_height", "hinge_x", "hinge_z",
            "latch_x", "latch_y",
            "pcb_groove_z", "pcb_groove_depth", "pcb_groove_width",
        ],
    ),

    # ── 4. Clamshell Vertical ──────────────────────────────────
    "CLAMSHELL_VERTICAL": DesignStrategy(
        topology_name="CLAMSHELL_VERTICAL",
        display_name="Clamshell (vertical split)",
        split_axis="Y",
        piece_count=2,
        closure_mechanism="hinge_latch",
        wall_profile="flat",
        internal_architecture="pcb_groove",
        vent_architecture="side_louvers",
        mounting_interface="screw_tabs",
        applicable_when={
            "access_frequency": ["DAILY", "WEEKLY"],
            "mounting": ["WALL_MOUNT"],
        },
        score_fn=_score_clamshell_vertical,
        openscad_module_set="strategies/clamshell_horizontal",
        openscad_rules=[
            "Two halves split at Y midpoint (vertical split)",
            "Hinge on top edge",
            "Latch on bottom edge",
            "PCB held in grooves on left/right walls",
            "Add wall mount screw tabs on back",
        ],
        topology_constraint_extensions=[
            "half_height", "hinge_x", "hinge_z",
            "latch_x", "latch_y",
            "pcb_groove_z", "pcb_groove_depth", "pcb_groove_width",
        ],
    ),

    # ── 5. Industrial Flanged ──────────────────────────────────
    "INDUSTRIAL_FLANGED": DesignStrategy(
        topology_name="INDUSTRIAL_FLANGED",
        display_name="Industrial (flanged box)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="screwed",
        wall_profile="flanged",
        internal_architecture="standoffs",
        vent_architecture="side_louvers",
        mounting_interface="screw_tabs",
        applicable_when={
            "use_case": ["INDUSTRIAL_CONTROLLER"],
            "environment": ["INDOOR_INDUSTRIAL"],
        },
        score_fn=_score_industrial_flanged,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Body has outward flange at top edge for lid seating",
            "Lid sits on flange with M3 screw pattern",
            "External screw tabs for wall/surface mounting",
            "Side louver vents for dust-tolerant airflow",
        ],
        topology_constraint_extensions=[],
    ),

    # ── 6. DIN Rail Clip ───────────────────────────────────────
    "DIN_RAIL_CLIP": DesignStrategy(
        topology_name="DIN_RAIL_CLIP",
        display_name="DIN Rail Clip",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="screwed",
        wall_profile="flat",
        internal_architecture="standoffs",
        vent_architecture="side_louvers",
        mounting_interface="din_clip",
        applicable_when={
            "mounting": ["DIN_RAIL"],
        },
        score_fn=_score_din_rail_clip,
        dfm_overrides={
            "min_wall_thickness_override": 1.5,  # Stronger walls for clip stress
        },
        openscad_module_set="strategies/din_rail_clip",
        openscad_rules=[
            "Body has DIN rail clip integrated on back face",
            "DIN rail width is ALWAYS 35.0mm (IEC 60715 standard)",
            "Clip engagement depth 5.5mm, spring length 14mm",
            "Release tab on bottom face, 8mm tall",
            "Lid screwed from top — no snap-fit (vibration environment)",
            "Side louver vents — no top vents (rail blocks top)",
        ],
        topology_constraint_extensions=[
            "din_rail_width", "din_clip_engagement_depth",
            "din_clip_spring_length", "din_clip_release_tab_height",
        ],
    ),

    # ── 7. Wearable Rounded ────────────────────────────────────
    "WEARABLE_ROUNDED": DesignStrategy(
        topology_name="WEARABLE_ROUNDED",
        display_name="Wearable (rounded)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="snap_fit",
        wall_profile="rounded",
        internal_architecture="press_fit",
        vent_architecture="perimeter_gap",
        mounting_interface="band_lug",
        applicable_when={
            "use_case": ["WEARABLE"],
            "mounting": ["WEARABLE"],
        },
        score_fn=_score_wearable_rounded,
        dfm_overrides={
            "min_wall_thickness_override": 1.0,  # Thinner for wearable comfort
        },
        openscad_module_set="strategies/wearable_rounded",
        openscad_rules=[
            "Body uses hull() or minkowski() for rounded exterior",
            "Corner radius from topology extensions (corner_radius)",
            "Edge fillet on all external edges (edge_fillet)",
            "Band lugs on left and right sides for strap attachment",
            "PCB press-fit mounting — no standoffs (size constraint)",
            "Perimeter gap ventilation — no visible vent slots",
            "MUST use curved geometry — no sharp corners",
        ],
        topology_constraint_extensions=[
            "corner_radius", "edge_fillet",
            "band_lug_width", "band_lug_height",
        ],
    ),

    # ── 8. Chimney Thermal ─────────────────────────────────────
    "CHIMNEY_THERMAL": DesignStrategy(
        topology_name="CHIMNEY_THERMAL",
        display_name="Chimney (thermal stack)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="screwed",
        wall_profile="flat",
        internal_architecture="standoffs",
        vent_architecture="chimney",
        mounting_interface="none",
        applicable_when={
            "total_wattage_gt": 8.0,
        },
        score_fn=_score_chimney_thermal,
        openscad_module_set="strategies/chimney_thermal",
        openscad_rules=[
            "Body has a chimney stack above the hottest thermal zone",
            "Chimney dimensions from topology extensions",
            "Bottom intake slots on front/back face near base",
            "Chimney top has exhaust slots",
            "Main body is standard rectangular with cutouts",
            "Lid has chimney hole pass-through",
        ],
        topology_constraint_extensions=[
            "chimney_x", "chimney_y", "chimney_width",
            "chimney_length", "chimney_height",
            "intake_slot_z", "intake_face",
        ],
    ),

    # ── 9. Three-Piece Access ──────────────────────────────────
    "THREE_PIECE_ACCESS": DesignStrategy(
        topology_name="THREE_PIECE_ACCESS",
        display_name="Three-piece (multi-access)",
        split_axis="Z",
        piece_count=3,
        closure_mechanism="screwed",
        wall_profile="flat",
        internal_architecture="standoffs",
        vent_architecture="top_slots",
        mounting_interface="none",
        applicable_when={
            "use_case": ["SCIENTIFIC_INSTRUMENT"],
            "access_frequency": ["DAILY"],
        },
        score_fn=_score_three_piece_access,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Three pieces: base, mid-frame, top lid",
            "Base holds PCB with standoffs",
            "Mid-frame provides component clearance",
            "Top lid screwed to mid-frame",
            "Mid-frame can be removed independently for PCB access",
        ],
        topology_constraint_extensions=[],
    ),

    # ── 10. Panel Mount Bezel ──────────────────────────────────
    "PANEL_MOUNT_BEZEL": DesignStrategy(
        topology_name="PANEL_MOUNT_BEZEL",
        display_name="Panel Mount (bezel)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="screwed",
        wall_profile="flat",
        internal_architecture="standoffs",
        vent_architecture="side_louvers",
        mounting_interface="panel_bezel",
        applicable_when={
            "mounting": ["PANEL_CUTOUT"],
        },
        score_fn=_score_panel_mount_bezel,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Front face has bezel flange extending 5mm beyond body",
            "Bezel has 4 corner mounting holes for panel attachment",
            "Body protrudes behind panel — all connectors on back face",
            "No top vents — use side louvers only",
        ],
        topology_constraint_extensions=[],
    ),

    # ── 11. Sealed IP-Rated ────────────────────────────────────
    "SEALED_IP_RATED": DesignStrategy(
        topology_name="SEALED_IP_RATED",
        display_name="Sealed (IP-rated)",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="gasket_screwed",
        wall_profile="flanged",
        internal_architecture="standoffs",
        vent_architecture="sealed",
        mounting_interface="screw_tabs",
        applicable_when={
            "environment": ["OUTDOOR", "WET_HUMID"],
        },
        score_fn=_score_sealed_ip_rated,
        dfm_overrides={
            "min_wall_thickness_override": 2.0,
            "ventilation_disabled": True,
        },
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "O-ring groove in lid flange for IP65+ sealing",
            "Lid flange width from topology extensions",
            "Cable gland holes instead of open cutouts",
            "NO ventilation — sealed enclosure",
            "Screwed closure with even screw spacing around perimeter",
            "Screw bosses have captive nut recesses",
        ],
        topology_constraint_extensions=[
            "oring_cross_section", "oring_groove_width", "oring_groove_depth",
            "cable_gland_od", "lid_flange_width", "screw_count",
        ],
    ),

    # ── 12. Snap-Rail Modular ──────────────────────────────────
    "SNAP_RAIL_MODULAR": DesignStrategy(
        topology_name="SNAP_RAIL_MODULAR",
        display_name="Snap-rail Modular",
        split_axis="Z",
        piece_count=2,
        closure_mechanism="snap_fit",
        wall_profile="flat",
        internal_architecture="rail_mount",
        vent_architecture="top_slots",
        mounting_interface="none",
        applicable_when={
            "use_case": ["IOT_DEVICE"],
        },
        score_fn=_score_snap_rail_modular,
        openscad_module_set="strategies/rectangular_flat",
        openscad_rules=[
            "Left and right sides have dovetail rails for module-to-module connection",
            "Modules snap together side-by-side",
            "Standard width increments (30mm, 45mm, 60mm)",
            "Top slots for ventilation",
        ],
        topology_constraint_extensions=[],
    ),
}


def get_strategy(name: str) -> DesignStrategy:
    """Get a strategy by topology name. Raises KeyError if not found."""
    if name not in STRATEGY_LIBRARY:
        raise KeyError(
            f"Unknown strategy '{name}'. "
            f"Available: {list(STRATEGY_LIBRARY.keys())}"
        )
    return STRATEGY_LIBRARY[name]
