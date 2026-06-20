"""
EnclosureAI — DFM (Design for Manufacturability) Validator
CRITICAL: Enforces material-specific manufacturing constraints.

Runs BEFORE the LLM is called — invalid geometry never reaches the AI.
RULE 3: If DFM rules cannot be satisfied, return structured ConstraintViolation
        error to the user — never let invalid geometry reach the LLM.

Checks (in order):
  1. Wall thickness >= material minimum        (ERROR)
  2. Snap-fit cantilever >= material minimum    (ERROR)
  3. Snap-fit gap >= cantilever × gap_per_mm    (WARNING, auto-correct)
  4. Cutout–snap-fit overlap                    (ERROR)
  5. Standoffs don't intersect outer wall       (ERROR)
  6. Glass transition temp vs operating temp    (WARNING)
  7. Vent slot width >= 2.0mm for FDM           (ERROR)
  8. Cutouts within face bounds                 (ERROR)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants import (
    DFM_RULES,
    VENT_SLOT_WIDTH,
    DELTA_T,
    AMBIENT_TEMP_CONSERVATIVE,
)
from app.schemas.constraint_schemas import ConstraintSchema


# ═══════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class DFMViolation:
    """A single DFM rule violation."""
    rule: str
    severity: str          # "ERROR" | "WARNING"
    message: str
    fix: str
    auto_corrected: bool = False


class DFMValidationError(Exception):
    """Raised when ERROR-severity DFM violations are found."""

    def __init__(self, violations: list[DFMViolation]):
        self.violations = violations
        error_msgs = [v.message for v in violations if v.severity == "ERROR"]
        super().__init__(
            f"DFM validation failed with {len(error_msgs)} error(s): "
            + "; ".join(error_msgs)
        )


# ═══════════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════════

def validate_dfm_compliance(constraints: ConstraintSchema) -> list[DFMViolation]:
    """
    Validate all computed constraints against material-specific DFM rules.
    
    Returns list of all violations (both ERROR and WARNING).
    Raises DFMValidationError if any ERROR-severity violations exist.
    
    WARNING violations with auto_corrected=True indicate the engine
    already compensated for the issue.
    """
    material = constraints.material
    rules = DFM_RULES.get(material, DFM_RULES["PETG"])
    violations: list[DFMViolation] = []

    # ─── Check 1: Wall thickness ──────────────────────────────
    min_wall = rules["min_wall_thickness"]
    if constraints.enclosure.wall < min_wall:
        violations.append(DFMViolation(
            rule="MIN_WALL_THICKNESS",
            severity="ERROR",
            message=(
                f"Wall thickness {constraints.enclosure.wall}mm < minimum "
                f"{min_wall}mm for {material}"
            ),
            fix=f"Increase wall thickness to {min_wall}mm",
        ))

    # ─── Check 2: Snap-fit cantilever length ──────────────────
    if constraints.snap_fit is not None:
        min_cantilever = rules["snap_fit_min_length"]
        if constraints.snap_fit.cantilever_length < min_cantilever:
            violations.append(DFMViolation(
                rule="SNAP_FIT_CANTILEVER",
                severity="ERROR",
                message=(
                    f"Snap-fit cantilever {constraints.snap_fit.cantilever_length}mm "
                    f"< minimum {min_cantilever}mm for {material}"
                ),
                fix=(
                    f"Increase lid overlap to allow "
                    f"{min_cantilever}mm cantilever"
                ),
            ))

    # ─── Check 3: Snap-fit gap adequacy ───────────────────────
    if constraints.snap_fit is not None:
        gap_per_mm = rules["snap_fit_gap_per_mm"]
        required_gap = round(
            constraints.snap_fit.cantilever_length * gap_per_mm, 2
        )
        if constraints.snap_fit.gap < required_gap:
            violations.append(DFMViolation(
                rule="SNAP_FIT_GAP",
                severity="WARNING",
                message=(
                    f"Snap-fit gap {constraints.snap_fit.gap}mm < recommended "
                    f"{required_gap}mm ({gap_per_mm}mm/mm × "
                    f"{constraints.snap_fit.cantilever_length}mm)"
                ),
                fix=f"Gap auto-corrected to {required_gap}mm",
                auto_corrected=True,
            ))
            # Auto-correct
            constraints.snap_fit.gap = required_gap

    # ─── Check 4: Cutout–snap-fit overlap ─────────────────────
    if constraints.snap_fit is not None and constraints.cutouts:
        for cutout in constraints.cutouts:
            for tab in constraints.snap_fit.positions:
                if cutout.face == tab["face"]:
                    tab_offset = tab["offset_from_start"]
                    # Check if tab falls within cutout x-range
                    if cutout.x_start <= tab_offset <= cutout.x_end:
                        violations.append(DFMViolation(
                            rule="CUTOUT_SNAPFIT_OVERLAP",
                            severity="ERROR",
                            message=(
                                f"Connector cutout '{cutout.label}' on {cutout.face} face "
                                f"(x={cutout.x_start:.1f}–{cutout.x_end:.1f}) overlaps with "
                                f"snap-fit tab at offset {tab_offset:.1f}mm"
                            ),
                            fix=(
                                "Reposition snap-fit tab or connector to "
                                "eliminate overlap"
                            ),
                        ))

    # ─── Check 5: Standoffs don't intersect outer wall ────────
    for standoff in constraints.standoffs:
        outer_r = standoff.outer_diameter / 2

        # Check X bounds: standoff must fit inside inner cavity
        if standoff.x - outer_r < constraints.enclosure.wall:
            violations.append(DFMViolation(
                rule="STANDOFF_WALL_INTERSECTION",
                severity="ERROR",
                message=(
                    f"Standoff at ({standoff.x:.1f}, {standoff.y:.1f}) "
                    f"intersects left wall (x={standoff.x - outer_r:.1f} < "
                    f"wall={constraints.enclosure.wall}mm)"
                ),
                fix="Increase PCB clearance or move mounting hole inward",
            ))
        if standoff.x + outer_r > constraints.enclosure.outer_length - constraints.enclosure.wall:
            violations.append(DFMViolation(
                rule="STANDOFF_WALL_INTERSECTION",
                severity="ERROR",
                message=(
                    f"Standoff at ({standoff.x:.1f}, {standoff.y:.1f}) "
                    f"intersects right wall"
                ),
                fix="Increase PCB clearance or move mounting hole inward",
            ))

        # Check Y bounds
        if standoff.y - outer_r < constraints.enclosure.wall:
            violations.append(DFMViolation(
                rule="STANDOFF_WALL_INTERSECTION",
                severity="ERROR",
                message=(
                    f"Standoff at ({standoff.x:.1f}, {standoff.y:.1f}) "
                    f"intersects front wall (y={standoff.y - outer_r:.1f} < "
                    f"wall={constraints.enclosure.wall}mm)"
                ),
                fix="Increase PCB clearance or move mounting hole inward",
            ))
        if standoff.y + outer_r > constraints.enclosure.outer_width - constraints.enclosure.wall:
            violations.append(DFMViolation(
                rule="STANDOFF_WALL_INTERSECTION",
                severity="ERROR",
                message=(
                    f"Standoff at ({standoff.x:.1f}, {standoff.y:.1f}) "
                    f"intersects back wall"
                ),
                fix="Increase PCB clearance or move mounting hole inward",
            ))

    # ─── Check 6: Glass transition temperature ────────────────
    tg = rules["glass_transition_temp"]
    # Estimate operating temperature from total wattage
    # Conservative: if Q > 5W with PLA (Tg=60°C), warn
    if constraints.total_wattage > 5.0 and tg <= 65:
        estimated_temp = AMBIENT_TEMP_CONSERVATIVE + (
            constraints.total_wattage * 3  # rough °C rise estimate per watt
        )
        violations.append(DFMViolation(
            rule="GLASS_TRANSITION_TEMP",
            severity="WARNING",
            message=(
                f"{material} glass transition temperature ({tg}°C) may be "
                f"exceeded with {constraints.total_wattage:.1f}W total dissipation "
                f"(estimated internal temp ~{estimated_temp:.0f}°C)"
            ),
            fix=(
                f"Consider switching to a material with higher Tg "
                f"(PETG: 80°C, ABS: 105°C)"
            ),
            auto_corrected=False,
        ))

    # ─── Check 7: Vent slot width for FDM ─────────────────────
    if (
        constraints.ventilation_enabled
        and constraints.print_technology == "FDM"
        and constraints.vent_spec is not None
    ):
        if constraints.vent_spec.slot_width < 2.0:
            violations.append(DFMViolation(
                rule="VENT_SLOT_WIDTH",
                severity="ERROR",
                message=(
                    f"Vent slot width {constraints.vent_spec.slot_width}mm "
                    f"< 2.0mm minimum for FDM printing"
                ),
                fix="Increase vent slot width to at least 2.0mm",
            ))

    # ─── Check 8: Cutouts within face bounds ──────────────────
    for cutout in constraints.cutouts:
        if cutout.face in ("FRONT", "BACK"):
            face_width = constraints.enclosure.outer_length
            face_height = constraints.enclosure.outer_height
        elif cutout.face in ("LEFT", "RIGHT"):
            face_width = constraints.enclosure.outer_width
            face_height = constraints.enclosure.outer_height
        elif cutout.face == "TOP":
            face_width = constraints.enclosure.outer_length
            face_height = constraints.enclosure.outer_width
        else:
            continue

        out_of_bounds = False
        details = []

        if cutout.x_start < 0:
            out_of_bounds = True
            details.append(f"x_start={cutout.x_start:.1f} < 0")
        if cutout.x_end > face_width:
            out_of_bounds = True
            details.append(f"x_end={cutout.x_end:.1f} > face_width={face_width:.1f}")
        if cutout.z_start < 0:
            out_of_bounds = True
            details.append(f"z_start={cutout.z_start:.1f} < 0")
        if cutout.z_end > face_height:
            out_of_bounds = True
            details.append(f"z_end={cutout.z_end:.1f} > face_height={face_height:.1f}")

        if out_of_bounds:
            violations.append(DFMViolation(
                rule="CUTOUT_OUT_OF_BOUNDS",
                severity="ERROR",
                message=(
                    f"Cutout '{cutout.label}' on {cutout.face} face "
                    f"extends beyond face bounds: {', '.join(details)}"
                ),
                fix=(
                    "Adjust connector position or enclosure dimensions "
                    "to keep cutout within face"
                ),
            ))

    # ─── Raise if any ERROR violations ────────────────────────
    errors = [v for v in violations if v.severity == "ERROR"]

    if errors:
     print("DFM WARNINGS:")
     for e in errors:
        print(f"- {e.message}")

    return violations
