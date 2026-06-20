from dataclasses import dataclass
from app.schemas.input_schemas import PCBSpec
from app.core.design_context import (
    DesignContext, UseCase, AccessFrequency,
    MountingStyle as MountingEnvironment, Environment as DeploymentEnvironment
)

@dataclass
class DesignStrategy:
    name:              str
    description:       str
    piece_count:       int
    lid_mechanism:     str
    split_axis:        str
    wall_profile:      str
    vent_type:         str
    internal_structure: str
    mounting_feature:  str
    openscad_template: str
    few_shot_key:      str

STRATEGY_LIBRARY = {
    "RECTANGULAR_FLAT_LID": DesignStrategy(
        name="RECTANGULAR_FLAT_LID",
        description="Standard rectangular box with flat snap-fit or screwed lid",
        piece_count=2, lid_mechanism="SNAP_FIT", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="PARALLEL_SLOTS",
        internal_structure="EMPTY", mounting_feature="NONE",
        openscad_template="rectangular_flat", few_shot_key="rectangular_flat"
    ),
    "RECTANGULAR_RIBBED": DesignStrategy(
        name="RECTANGULAR_RIBBED",
        description="Rectangular box with structural lid ribs for large PCBs",
        piece_count=2, lid_mechanism="SCREWED", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="PARALLEL_SLOTS",
        internal_structure="RIBBED", mounting_feature="NONE",
        openscad_template="rectangular_ribbed", few_shot_key="rectangular_flat"
    ),
    "CLAMSHELL_HINGED": DesignStrategy(
        name="CLAMSHELL_HINGED",
        description="Horizontal clamshell that opens like a laptop — for frequent access",
        piece_count=2, lid_mechanism="HINGED", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="PARALLEL_SLOTS",
        internal_structure="GROOVE_RAIL", mounting_feature="NONE",
        openscad_template="clamshell_hinged", few_shot_key="clamshell_hinged"
    ),
    "WEARABLE_ROUNDED": DesignStrategy(
        name="WEARABLE_ROUNDED",
        description="Smooth rounded pill body with band lugs — no sharp edges",
        piece_count=2, lid_mechanism="SNAP_FIT", split_axis="HORIZONTAL",
        wall_profile="ROUNDED", vent_type="NONE",
        internal_structure="EMPTY", mounting_feature="BAND_LUGS",
        openscad_template="wearable_rounded", few_shot_key="wearable_rounded"
    ),
    "CHIMNEY_THERMAL": DesignStrategy(
        name="CHIMNEY_THERMAL",
        description="Box with elevated chimney vent stack over hotspot — for 8W+ boards",
        piece_count=2, lid_mechanism="SCREWED", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="CHIMNEY",
        internal_structure="EMPTY", mounting_feature="NONE",
        openscad_template="chimney_thermal", few_shot_key="chimney_thermal"
    ),
    "DIN_RAIL_CLIP": DesignStrategy(
        name="DIN_RAIL_CLIP",
        description="DIN EN 50022 rail-mount body with integrated clip",
        piece_count=3, lid_mechanism="SNAP_FIT", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="LOUVERED",
        internal_structure="EMPTY", mounting_feature="DIN_CLIP",
        openscad_template="din_rail", few_shot_key="din_rail"
    ),
    "INDUSTRIAL_FLANGED": DesignStrategy(
        name="INDUSTRIAL_FLANGED",
        description="Flanged wall-mount box with M4 mounting bosses",
        piece_count=2, lid_mechanism="SCREWED", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="LOUVERED",
        internal_structure="EMPTY", mounting_feature="FLANGES",
        openscad_template="industrial_flanged", few_shot_key="industrial_flanged"
    ),
    "SEALED_OUTDOOR": DesignStrategy(
        name="SEALED_OUTDOOR",
        description="Sealed box with O-ring groove and cable gland bosses",
        piece_count=2, lid_mechanism="SCREWED", split_axis="HORIZONTAL",
        wall_profile="UNIFORM", vent_type="NONE",
        internal_structure="EMPTY", mounting_feature="FLANGES",
        openscad_template="sealed_outdoor", few_shot_key="sealed_outdoor"
    ),
}


class DesignStrategySelector:

    def select(
        self,
        context: DesignContext,
        total_wattage: float,
        pcb_length: float,
        pcb_width: float,
        connector_face_count: int
    ) -> DesignStrategy:

        # ── HARD OVERRIDES (sufficient conditions, checked in priority order) ──
        if getattr(context, 'mounting_environment', context.mounting) == MountingEnvironment.DIN_RAIL:
            return STRATEGY_LIBRARY["DIN_RAIL_CLIP"]

        if (context.use_case == UseCase.WEARABLE or
                getattr(context, 'is_wearable', False) or
                getattr(context, 'mounting_environment', context.mounting) == MountingEnvironment.WEARABLE):
            return STRATEGY_LIBRARY["WEARABLE_ROUNDED"]

        if getattr(context, 'deployment_environment', context.environment) in [
            DeploymentEnvironment.OUTDOOR,
            DeploymentEnvironment.WET_HUMID
        ]:
            return STRATEGY_LIBRARY["SEALED_OUTDOOR"]

        # ── SCORED SELECTION ──────────────────────────────────────────────────
        scores = {name: 0.0 for name in STRATEGY_LIBRARY}

        # Thermal: chimney for very high wattage (but thermal engine also overrides)
        if total_wattage >= 8.0:
            scores["CHIMNEY_THERMAL"] += 6.0
        elif total_wattage >= 5.0:
            scores["CHIMNEY_THERMAL"] += 2.5

        # Access frequency drives clamshell
        if context.access_frequency in [AccessFrequency.DAILY, getattr(AccessFrequency, 'FREQUENT', AccessFrequency.DAILY)]:
            scores["CLAMSHELL_HINGED"] += 4.0
        if getattr(context, 'toolless_assembly', False):
            scores["CLAMSHELL_HINGED"] += 2.0

        # Industrial use case
        if context.use_case == UseCase.INDUSTRIAL_CONTROLLER:
            scores["INDUSTRIAL_FLANGED"] += 3.0

        # Wall mounting
        if getattr(context, 'mounting_environment', context.mounting) == MountingEnvironment.WALL_MOUNT:
            scores["INDUSTRIAL_FLANGED"] += 2.5

        # Large PCB needs ribbed lid to prevent warping
        if max(pcb_length, pcb_width) > 100:
            scores["RECTANGULAR_RIBBED"] += 3.0

        # Default always scores 1 so it can win against all-zero scored strategies
        scores["RECTANGULAR_FLAT_LID"] += 1.0

        best = max(scores, key=lambda k: scores[k])

        # If only the default scored (score == 1.0), just return default
        return STRATEGY_LIBRARY[best]
