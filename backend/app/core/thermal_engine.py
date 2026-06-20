import math
from dataclasses import dataclass, asdict
from typing import Optional

# Physics constants — DO NOT CHANGE
H_NATURAL   = 10.0   # W/(m²·K) — natural convection coefficient
H_FORCED    = 25.0   # W/(m²·K) — forced convection (fan)
T_AMBIENT   = 25.0   # °C — conservative ambient
T_SAFE      = 70.0   # °C — 15°C below 85°C IC limit
DELTA_T     = 45.0   # °C — T_SAFE - T_AMBIENT
SLOT_WIDTH  = 0.0025 # m — 2.5mm vent slot width
SLOT_LENGTH = 0.015  # m — 15mm vent slot length
MIN_SLOTS   = 4      # minimum even for 0W boards (aesthetic)
MAX_SLOTS   = 40     # cap to prevent absurd geometry


@dataclass
class ThermalResult:
    # Core thermal computation
    total_wattage:          float
    required_vent_area_m2:  float
    required_vent_area_cm2: float
    slot_count:             int
    implemented_vent_area_m2:  float
    implemented_vent_area_cm2: float
    area_ratio:             float

    # Hotspot data
    hotspot_component:      Optional[str]
    hotspot_x:              float
    hotspot_y:              float
    hotspot_wattage:        float
    vent_face_primary:      str    # TOP | LEFT | RIGHT | FRONT | BACK
    vent_face_intake:       str    # face for intake slots

    # Scoring
    thermal_health_score:   int    # 0–100
    verdict:                str
    recommendation:         str
    passive_cooling_ok:     bool

    # For OpenSCAD generation — these go directly into the prompt
    openscad_slot_count:    int
    openscad_vent_face:     str
    openscad_intake_face:   str
    openscad_chimney_needed: bool
    openscad_chimney_x:     float
    openscad_chimney_y:     float
    openscad_chimney_height: float

    def to_dict(self) -> dict:
        return asdict(self)


def compute_thermal(
    components: list[dict],   # list of {label, wattage, position_x, position_y}
    pcb_length: float,        # mm
    pcb_width:  float,        # mm
    enclosure_length: float,  # mm — outer
    enclosure_width:  float,  # mm — outer
    ventilation_enabled: bool = True
) -> ThermalResult:
    """
    Full thermal analysis. Returns ThermalResult with all values
    needed for BOTH the UI score card AND the OpenSCAD generator.
    """

    # ── Step 1: Total wattage ─────────────────────────────────────────
    total_w = sum(c.get("wattage", 0.0) for c in components)
    total_w = max(0.0, total_w)

    # ── Step 2: Find hottest component ───────────────────────────────
    hot_components = [c for c in components if c.get("wattage", 0) >= 0.5]
    if hot_components:
        hotspot = max(hot_components, key=lambda c: c.get("wattage", 0))
    else:
        hotspot = None

    hotspot_x       = hotspot["position_x"]       if hotspot else pcb_length / 2
    hotspot_y       = hotspot["position_y"]        if hotspot else pcb_width / 2
    hotspot_w       = hotspot.get("wattage", 0.0)  if hotspot else 0.0
    hotspot_label   = hotspot.get("label", "unknown") if hotspot else "none"

    # ── Step 3: Determine vent face based on hotspot position ─────────
    # Map PCB coordinates to relative position (0.0 to 1.0)
    rel_x = hotspot_x / pcb_length if pcb_length > 0 else 0.5
    rel_y = hotspot_y / pcb_width  if pcb_width  > 0 else 0.5

    if not ventilation_enabled:
        vent_face   = "NONE"
        intake_face = "NONE"
    elif rel_x < 0.2:
        vent_face   = "LEFT"
        intake_face = "RIGHT"
    elif rel_x > 0.8:
        vent_face   = "RIGHT"
        intake_face = "LEFT"
    elif rel_y < 0.2:
        vent_face   = "FRONT"
        intake_face = "BACK"
    elif rel_y > 0.8:
        vent_face   = "BACK"
        intake_face = "FRONT"
    else:
        # Hotspot in middle — top vents are best for natural convection
        vent_face   = "TOP"
        intake_face = "BOTTOM_SLOTS"

    # ── Step 4: Required vent area ────────────────────────────────────
    if total_w > 0 and ventilation_enabled:
        required_area_m2 = total_w / (H_NATURAL * DELTA_T)
    else:
        required_area_m2 = 0.0

    required_area_cm2 = required_area_m2 * 10000

    # ── Step 5: Slot count from required area ─────────────────────────
    area_per_slot_m2 = SLOT_WIDTH * SLOT_LENGTH   # 2.5mm × 15mm
    if required_area_m2 > 0:
        raw_count = math.ceil(required_area_m2 / area_per_slot_m2 * 1.2)  # 20% margin
        slot_count = max(MIN_SLOTS, min(MAX_SLOTS, raw_count))
    else:
        slot_count = MIN_SLOTS if ventilation_enabled else 0

    # ── Step 6: Implemented area ──────────────────────────────────────
    implemented_area_m2  = slot_count * area_per_slot_m2
    implemented_area_cm2 = implemented_area_m2 * 10000

    area_ratio = (implemented_area_m2 / required_area_m2
                  if required_area_m2 > 0 else 2.0)

    # ── Step 7: Thermal Health Score ──────────────────────────────────
    if not ventilation_enabled and total_w > 3:
        # Sealed enclosure with high wattage — always poor
        area_score      = 5
        path_score      = 0
        proximity_score = 5
    elif not ventilation_enabled:
        # Sealed but low power — OK
        area_score      = 40
        path_score      = 20
        proximity_score = 15
    else:
        area_score = min(50, area_ratio * 40)

        # Airflow path: TOP with BOTTOM_SLOTS is ideal (stack effect)
        path_score = (
            30 if (vent_face == "TOP" and intake_face == "BOTTOM_SLOTS") else
            25 if vent_face in ["LEFT", "RIGHT"] else
            20 if vent_face in ["FRONT", "BACK"] else 10
        )

        # Hotspot proximity to vents (simplified — assume vents directly above)
        if hotspot_w == 0:
            proximity_score = 20
        elif vent_face == "TOP":
            proximity_score = 20   # top vents always directly above hotspot
        else:
            proximity_score = 12   # side vents are less direct

    total_score = round(area_score + path_score + proximity_score)
    total_score = max(0, min(100, total_score))

    if total_score >= 85:
        verdict     = "EXCELLENT — passive cooling optimal"
        passive_ok  = True
    elif total_score >= 70:
        verdict     = "GOOD — passive cooling sufficient"
        passive_ok  = True
    elif total_score >= 50:
        verdict     = "MARGINAL — consider adding a fan cutout"
        passive_ok  = False
    else:
        verdict     = "POOR — active cooling required"
        passive_ok  = False

    if total_w == 0:
        recommendation = "No thermal management needed — board draws no significant power"
    elif passive_ok:
        recommendation = (
            f"Vent area {implemented_area_cm2:.1f}cm² on {vent_face} face "
            f"provides adequate cooling for {total_w:.1f}W total dissipation"
        )
    else:
        recommendation = (
            f"Add 40mm fan cutout on {intake_face} face. "
            f"Current passive area {implemented_area_cm2:.1f}cm² is "
            f"insufficient for {total_w:.1f}W — active cooling needed."
        )

    # ── Step 8: Chimney decision ──────────────────────────────────────
    chimney_needed = (total_w >= 8.0 and ventilation_enabled)
    chimney_height = max(15.0, total_w * 2.0) if chimney_needed else 0.0

    # Chimney centre in ENCLOSURE coordinates (not PCB coordinates)
    # Assumes 3mm clearance + 2.5mm wall offset
    wall_offset      = 5.5   # clearance + wall
    chimney_enc_x    = hotspot_x + wall_offset
    chimney_enc_y    = hotspot_y + wall_offset

    return ThermalResult(
        total_wattage=total_w,
        required_vent_area_m2=round(required_area_m2, 6),
        required_vent_area_cm2=round(required_area_cm2, 2),
        slot_count=slot_count,
        implemented_vent_area_m2=round(implemented_area_m2, 6),
        implemented_vent_area_cm2=round(implemented_area_cm2, 2),
        area_ratio=round(area_ratio, 2),

        hotspot_component=hotspot_label,
        hotspot_x=hotspot_x,
        hotspot_y=hotspot_y,
        hotspot_wattage=hotspot_w,
        vent_face_primary=vent_face,
        vent_face_intake=intake_face,

        thermal_health_score=total_score,
        verdict=verdict,
        recommendation=recommendation,
        passive_cooling_ok=passive_ok,

        openscad_slot_count=slot_count,
        openscad_vent_face=vent_face,
        openscad_intake_face=intake_face,
        openscad_chimney_needed=chimney_needed,
        openscad_chimney_x=round(chimney_enc_x, 2),
        openscad_chimney_y=round(chimney_enc_y, 2),
        openscad_chimney_height=round(chimney_height, 2),
    )
