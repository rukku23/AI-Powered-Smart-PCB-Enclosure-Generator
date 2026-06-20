"""
EnclosureAI - Strategy-Aware Prompt Builder (Phase 9 v2 - Hybrid)

The LLM no longer generates base geometry. Instead it receives the
procedural module definitions and must ONLY output:
  1. A reasoning block comment
  2. A custom_cutouts() module with board-specific port holes
  3. The final assembly block combining base + cutouts
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, fields, is_dataclass
from typing import Union

from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.llm.strategy_prompt")


def _safe_dict(obj):
    """Convert dataclass or dict to a JSON-safe dict."""
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return {}


# ---------------------------------------------------------------
# Board-specific few-shot cutout examples
# ---------------------------------------------------------------

_ESP32_CUTOUT_EXAMPLE = """
// === EXAMPLE: ESP32 DevKit V1 cutouts ===
// The procedural base modules (enclosure_body, enclosure_lid,
// standoffs, vent_slots) are already defined above.

module custom_cutouts() {
    // USB-C port on FRONT face (Y=0)
    // position_x=25.5 on PCB -> enclosure X = wall + position_x
    translate([wall + 25.5 - 4.5, -0.1, wall + 5.0 + 1.0])
        cube([9.0, wall + 0.2, 3.5]);

    // Boot button access hole on TOP face
    translate([wall + 5.0, wall + 12.5, body_h - 0.1])
        cylinder(d=4, h=wall + 0.2);

    // LED indicator window on TOP face
    translate([wall + 45.0, wall + 12.5, body_h - 0.1])
        cylinder(d=3, h=wall + 0.2);

    // GPIO header access slot on LEFT face (X=0)
    translate([-0.1, wall + 3, wall + 5.0 + 1.5])
        cube([wall + 0.2, 19, 2.5]);

    // GPIO header access slot on RIGHT face
    translate([outer_w - wall - 0.1, wall + 3, wall + 5.0 + 1.5])
        cube([wall + 0.2, 19, 2.5]);
}

// === FINAL ASSEMBLY ===
difference() {
    enclosure_body();
    custom_cutouts();
    vent_slots();
}
standoffs();

// Lid placed beside for 3D printing
translate([outer_w + 10, 0, 0])
    enclosure_lid();
""".strip()

_ARDUINO_UNO_CUTOUT_EXAMPLE = """
// === EXAMPLE: Arduino Uno R3 cutouts ===

module custom_cutouts() {
    // USB-B port on BACK face (Y=outer_d)
    translate([wall + 11.5 - 6.0, outer_d - wall - 0.1, wall + 5.0 + 1.0])
        cube([12.0, wall + 0.2, 11.0]);

    // DC Barrel Jack on LEFT face (X=0)
    translate([-0.1, wall + 7.0, wall + 5.0 + 1.0])
        cube([wall + 0.2, 9.0, 11.0]);

    // ICSP header access hole on TOP face
    translate([wall + 50.0, wall + 26.0, body_h - 0.1])
        cube([6.0, 5.0, wall + 0.2]);

    // Reset button access hole on TOP face
    translate([wall + 52.0, wall + 44.0, body_h - 0.1])
        cylinder(d=4, h=wall + 0.2);

    // Power LED window
    translate([wall + 4.0, wall + 15.0, body_h - 0.1])
        cylinder(d=3, h=wall + 0.2);
}

// === FINAL ASSEMBLY ===
difference() {
    enclosure_body();
    custom_cutouts();
    vent_slots();
}
standoffs();

translate([outer_w + 10, 0, 0])
    enclosure_lid();
""".strip()

_RPI4_CUTOUT_EXAMPLE = """
// === EXAMPLE: Raspberry Pi 4 cutouts ===

module custom_cutouts() {
    // USB-C Power on FRONT face (Y=0)
    translate([wall + 11.2 - 4.5, -0.1, wall + 5.0 + 1.0])
        cube([9.0, wall + 0.2, 3.2]);

    // Micro HDMI 1 on FRONT face
    translate([wall + 26.0 - 3.5, -0.1, wall + 5.0 + 1.0])
        cube([7.0, wall + 0.2, 3.2]);

    // Micro HDMI 2 on FRONT face
    translate([wall + 39.5 - 3.5, -0.1, wall + 5.0 + 1.0])
        cube([7.0, wall + 0.2, 3.2]);

    // 3.5mm Audio Jack on FRONT face
    translate([wall + 53.5, -0.1, wall + 5.0 + 3.0])
        rotate([-90, 0, 0])
            cylinder(d=7.0, h=wall + 0.2);

    // Ethernet on RIGHT face (X=outer_w)
    translate([outer_w - wall - 0.1, wall + 7.5, wall + 5.0 + 1.0])
        cube([wall + 0.2, 16.0, 13.5]);

    // USB-A Ports (lower pair) on RIGHT face
    translate([outer_w - wall - 0.1, wall + 21.5, wall + 5.0 + 1.0])
        cube([wall + 0.2, 15.0, 16.0]);

    // USB-A Ports (upper pair) on RIGHT face
    translate([outer_w - wall - 0.1, wall + 39.0, wall + 5.0 + 1.0])
        cube([wall + 0.2, 15.0, 16.0]);

    // SD card slot on BACK face (Y=outer_d), bottom edge
    translate([wall + 1.0, outer_d - wall - 0.1, wall + 0.5])
        cube([13.0, wall + 0.2, 2.0]);

    // GPIO pin header slot on TOP face
    translate([wall + 7.0, wall + 50.0, body_h - 0.1])
        cube([52.0, 5.5, wall + 0.2]);
}

// === FINAL ASSEMBLY ===
difference() {
    enclosure_body();
    custom_cutouts();
    vent_slots();
}
standoffs();

translate([outer_w + 10, 0, 0])
    enclosure_lid();
""".strip()


def build_strategy_prompt(constraints, strategy) -> list[dict]:
    """Build hybrid prompt: tell LLM to write cutouts only, not base geometry."""

    constraints_dict = _safe_dict(constraints)

    thermal = constraints_dict.get("thermal_data", {}) or {}
    slot_count = thermal.get("openscad_slot_count", 0)
    vent_face = thermal.get("openscad_vent_face", "TOP")
    total_watts = thermal.get("total_wattage", 0)

    # Pick the best matching example
    components = constraints_dict.get("components", [])
    if not components:
        components = []

    component_labels = [c.get("label", "").lower() for c in components if isinstance(c, dict)]
    label_text = " ".join(component_labels)

    if "rpi" in label_text or "raspberry" in label_text or "bcm" in label_text:
        example = _RPI4_CUTOUT_EXAMPLE
        board_hint = "Raspberry Pi 4"
    elif "arduino" in label_text or "atmega" in label_text or "barrel" in label_text:
        example = _ARDUINO_UNO_CUTOUT_EXAMPLE
        board_hint = "Arduino Uno R3"
    else:
        example = _ESP32_CUTOUT_EXAMPLE
        board_hint = "ESP32 DevKit"

    # Build the component description for the prompt
    component_lines = []
    for c in components:
        if not isinstance(c, dict):
            continue
        label = c.get("label", "unknown")
        face = c.get("face_access", "NONE")
        cw = c.get("connector_width", 0) or 0
        ch = c.get("connector_height", 0) or 0
        px = c.get("position_x", 0)
        py = c.get("position_y", 0)
        ht = c.get("height", 0)
        ct = c.get("component_type", "GENERIC")

        if face != "NONE":
            component_lines.append(
                f"  - {label}: {ct}, face={face}, pos=({px},{py}), "
                f"size={cw}x{ch}mm, height={ht}mm"
            )
        else:
            component_lines.append(
                f"  - {label}: {ct}, internal, pos=({px},{py}), height={ht}mm, {c.get('wattage',0)}W"
            )

    components_desc = "\n".join(component_lines) if component_lines else "  (no components specified)"

    strategy_name = getattr(strategy, "name", "RECTANGULAR_FLAT_LID")

    system_message = f"""You are an OpenSCAD engineer specializing in PCB enclosure cutouts.

## ARCHITECTURE
The base enclosure geometry (body, lid, standoffs, vent slots) is already
generated procedurally as OpenSCAD modules. These modules are defined in
the code block above your output. You MUST NOT redefine them.

The following modules already exist:
  - enclosure_body()   -- the main shell with walls and cavity
  - enclosure_lid()    -- the lid piece
  - standoffs()        -- PCB mounting posts inside the body
  - vent_slots()       -- thermal ventilation slots on top face

## YOUR TASK
Generate ONLY:
1. A `/* === ENCLOSUREAI DESIGN REASONING === ... */` comment block
2. A `module custom_cutouts()` containing all port holes, button access
   holes, LED windows, cable slots, and any board-specific features
3. The final assembly block that combines everything

## RULES
- Use `difference()` to subtract custom_cutouts() and vent_slots() from enclosure_body()
- Use `translate()` with exact coordinates from the component list below
- For connectors on faces, position the cutout to penetrate the wall:
    FRONT face (Y=0):  translate([wall + pos_x - w/2, -0.1, wall + standoff_h + pcb_t + offset])
    BACK face (Y=outer_d): translate([wall + pos_x - w/2, outer_d - wall - 0.1, ...])
    LEFT face (X=0):   translate([-0.1, wall + pos_y, ...])
    RIGHT face (X=outer_w): translate([outer_w - wall - 0.1, wall + pos_y, ...])
    TOP face:           translate([wall + pos_x, wall + pos_y, body_h - 0.1])
- Add 0.5mm tolerance to each cutout dimension for clearance
- Use `cylinder()` for round holes (buttons, LEDs, audio jacks)
- Use `cube()` for rectangular ports (USB, HDMI, Ethernet)
- Do NOT output any module that redefines enclosure_body, enclosure_lid, standoffs, or vent_slots
- Output ONLY valid OpenSCAD code. No markdown fences. No prose outside comments.

## BOARD & COMPONENTS
Strategy: {strategy_name}
Similar to: {board_hint}
Components requiring cutouts:
{components_desc}

## REFERENCE EXAMPLE
{example}

## CONSTRAINT DATA
{json.dumps(constraints_dict, indent=2, default=str)}

Generate the custom_cutouts module and assembly now:"""

    return [{"role": "user", "content": system_message}]
