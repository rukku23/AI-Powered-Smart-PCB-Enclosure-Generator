"""
EnclosureAI — Topology-Keyed Few-Shot Example Library (Phase 8)

Provides strategy-specific few-shot examples for in-context learning.
Each topology has its own examples using ASSEMBLY SCRIPTS that call
module functions — not from-scratch OpenSCAD.

The LLM learns to ASSEMBLE modules, not invent geometry.
"""

# ═══════════════════════════════════════════════════════════════
# RECTANGULAR_FLAT_LID Examples (legacy format — from-scratch)
# ═══════════════════════════════════════════════════════════════

_RECT_ESP32_CONSTRAINT = """{
  "pcb": {"length": 51.0, "width": 25.0, "thickness": 1.6},
  "enclosure": {
    "outer_length": 59.4, "outer_width": 33.4, "outer_height": 10.74,
    "wall": 1.2, "clearance": 3.0, "lid_thickness": 1.44
  },
  "standoffs": [
    {"x": 6.7, "y": 6.7, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"},
    {"x": 52.7, "y": 6.7, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"},
    {"x": 6.7, "y": 26.7, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"},
    {"x": 52.7, "y": 26.7, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"}
  ],
  "cutouts": [
    {"face": "FRONT", "x_start": 23.2, "x_end": 36.2, "z_start": 5.8, "z_end": 10.74, "label": "USB-C"}
  ],
  "thermal_zones": [
    {"centre_x": 14.2, "centre_y": 16.7, "radius": 20.0, "face": "TOP", "priority": 1.5}
  ],
  "snap_fit": {"tab_count": 4, "cantilever_length": 15.0, "gap": 4.5},
  "material": "PETG", "lid_style": "SNAP_FIT", "ventilation_enabled": true,
  "strategy_name": "RECTANGULAR_FLAT_LID"
}"""

_RECT_ESP32_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
GEOMETRY: Outer 59.4 x 33.4 x 10.74mm from PCB 51x25mm + 3mm clearance + 1.2mm wall.
FEATURES: 4x M3 standoffs, USB-C cutout on front face. Snap-fit closure.
THERMAL: 1.5W generates thermal zone. 4 vent slots on top.
MATERIAL: PETG, wall 1.2mm, snap-fit gap 4.5mm.
======================================= */

outer_length = 59.4;
outer_width = 33.4;
outer_height = 10.74;
wall = 1.2;
lid_thickness = 1.44;
body_height = outer_height - lid_thickness;
standoff_height = 5.0;
standoff_od = 6.4;
standoff_id = 3.2;
vent_count = 4;
vent_slot_width = 2.5;
vent_slot_length = 15.0;
vent_slot_spacing = 4.0;
snap_tab_width = 6;
snap_tab_height = 3;
$fn = 30;

module enclosure_body() {
    difference() {
        cube([outer_length, outer_width, body_height]);
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, body_height]);
        usb_c_cutout();
        top_vents();
    }
    standoffs();
    snap_tabs_body();
}

module standoffs() {
    positions = [[6.7, 6.7], [52.7, 6.7], [6.7, 26.7], [52.7, 26.7]];
    for (pos = positions) {
        translate([pos[0], pos[1], wall])
            difference() {
                cylinder(d=standoff_od, h=standoff_height);
                cylinder(d=standoff_id, h=standoff_height + 0.1);
            }
    }
}

module usb_c_cutout() {
    translate([23.2, -0.1, 5.8])
        cube([13.0, wall + 0.2, 4.94]);
}

module top_vents() {
    start_x = (outer_length - (vent_count * vent_slot_width + (vent_count-1) * vent_slot_spacing)) / 2;
    start_y = (outer_width - vent_slot_length) / 2;
    for (i = [0 : vent_count - 1]) {
        translate([start_x + i*(vent_slot_width+vent_slot_spacing), start_y, body_height-wall-0.1])
            cube([vent_slot_width, vent_slot_length, wall + 0.2]);
    }
}

module snap_tabs_body() {
    tab_z = body_height - snap_tab_height - 1;
    for (x_pos = [outer_length/4, 3*outer_length/4]) {
        translate([x_pos - snap_tab_width/2, -0.5, tab_z])
            cube([snap_tab_width, 1.5, snap_tab_height]);
        translate([x_pos - snap_tab_width/2, outer_width - 1.0, tab_z])
            cube([snap_tab_width, 1.5, snap_tab_height]);
    }
}

module lid() {
    cube([outer_length, outer_width, lid_thickness]);
}

enclosure_body();
translate([outer_length + 10, 0, 0]) lid();"""

_RECT_ARDUINO_CONSTRAINT = """{
  "pcb": {"length": 68.6, "width": 53.4, "thickness": 1.6},
  "enclosure": {
    "outer_length": 77.0, "outer_width": 61.8, "outer_height": 19.04,
    "wall": 1.2, "clearance": 3.0, "lid_thickness": 1.44
  },
  "standoffs": [
    {"x": 18.2, "y": 6.74, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"},
    {"x": 70.24, "y": 11.82, "outer_diameter": 6.4, "inner_diameter": 3.2, "height": 5.0, "fastener_type": "M3"}
  ],
  "cutouts": [
    {"face": "BACK", "x_start": 9.7, "x_end": 25.7, "z_start": 4.8, "z_end": 18.8, "label": "USB-B"}
  ],
  "material": "PLA", "lid_style": "SCREWED_M3", "ventilation_enabled": true,
  "strategy_name": "RECTANGULAR_FLAT_LID"
}"""

_RECT_ARDUINO_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
GEOMETRY: Outer 77.0 x 61.8 x 19.04mm. M3 screw bosses.
FEATURES: USB-B cutout on back. Screwed lid.
======================================= */
outer_length = 77.0;
outer_width = 61.8;
outer_height = 19.04;
wall = 1.2;
lid_thickness = 1.44;
body_height = outer_height - lid_thickness;
$fn = 30;

module enclosure_body() {
    difference() {
        cube([outer_length, outer_width, body_height]);
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, body_height]);
        translate([9.7, -0.1, 4.8]) cube([16.0, wall+0.2, 14.0]);
    }
    standoffs();
    screw_bosses();
}
module standoffs() {
    for (pos = [[18.2,6.74],[70.24,11.82]]) {
        translate([pos[0],pos[1],wall])
            difference() { cylinder(d=6.4,h=5); cylinder(d=3.2,h=5.1); }
    }
}
module screw_bosses() {
    for (pos = [[5,5],[outer_length-5,5],[5,outer_width-5],[outer_length-5,outer_width-5]]) {
        translate([pos[0],pos[1],wall]) cylinder(d=8,h=body_height-wall);
    }
}
module lid() {
    difference() {
        cube([outer_length, outer_width, lid_thickness]);
        for (pos = [[5,5],[outer_length-5,5],[5,outer_width-5],[outer_length-5,outer_width-5]]) {
            translate([pos[0],pos[1],-0.1]) cylinder(d=3.2,h=lid_thickness+0.2);
        }
    }
}
enclosure_body();
translate([outer_length+10, 0, 0]) lid();"""

# ═══════════════════════════════════════════════════════════════
# CLAMSHELL_HORIZONTAL Examples (assembly scripts)
# ═══════════════════════════════════════════════════════════════

_CLAMSHELL_SMALL_CONSTRAINT = """{
  "pcb": {"length": 50.0, "width": 30.0, "thickness": 1.6},
  "enclosure": {
    "outer_length": 58.4, "outer_width": 38.4, "outer_height": 14.0,
    "wall": 1.2, "clearance": 3.0, "lid_thickness": 1.44
  },
  "topology_extensions": {
    "half_height": 7.0, "hinge_x": 29.2, "hinge_z": 7.0,
    "latch_x": 29.2, "latch_y": 0.0,
    "pcb_groove_z": 6.2, "pcb_groove_depth": 1.5, "pcb_groove_width": 2.0
  },
  "cutouts": [{"face": "FRONT", "x_start": 20, "x_end": 33, "z_start": 5.8, "z_end": 10, "label": "USB-C"}],
  "material": "PETG", "strategy_name": "CLAMSHELL_HORIZONTAL", "ventilation_enabled": true
}"""

_CLAMSHELL_SMALL_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
TOPOLOGY: CLAMSHELL_HORIZONTAL — two halves split at Z midpoint.
GEOMETRY: 58.4 x 38.4 x 14mm, split at half_height=7mm.
FEATURES: Hinge on back edge, latch on front. PCB in side grooves.
======================================= */

use <../module_library/strategies/clamshell_horizontal/lower_shell.scad>
use <../module_library/strategies/clamshell_horizontal/upper_shell.scad>
use <../module_library/strategies/clamshell_horizontal/hinge.scad>

outer_length = 58.4;
outer_width = 38.4;
outer_height = 14.0;
wall = 1.2;
half_height = 7.0;
hinge_x = 29.2;
hinge_z = 7.0;
latch_x = 29.2;
latch_y = 0.0;
pcb_groove_z = 6.2;
pcb_groove_depth = 1.5;
pcb_groove_width = 2.0;
$fn = 30;

// Lower shell with PCB grooves and latch
difference() {
    clamshell_lower_shell(outer_length, outer_width, half_height, wall,
                          pcb_groove_z, pcb_groove_depth, pcb_groove_width,
                          latch_x, latch_y);
    // USB-C cutout on front
    translate([20, -0.1, 5.8]) cube([13, wall+0.2, 4.2]);
}

// Upper shell placed beside for printing
translate([outer_length + 10, 0, 0])
    clamshell_upper_shell(outer_length, outer_width, half_height, wall,
                          hinge_x, hinge_z);"""

# ═══════════════════════════════════════════════════════════════
# CHIMNEY_THERMAL Example
# ═══════════════════════════════════════════════════════════════

_CHIMNEY_8W_CONSTRAINT = """{
  "pcb": {"length": 80.0, "width": 50.0, "thickness": 1.6},
  "enclosure": {
    "outer_length": 88.4, "outer_width": 58.4, "outer_height": 16.0,
    "wall": 1.2, "clearance": 3.0, "lid_thickness": 1.44
  },
  "topology_extensions": {
    "chimney_x": 44.2, "chimney_y": 29.2, "chimney_width": 24.0,
    "chimney_length": 24.0, "chimney_height": 32.0,
    "intake_slot_z": 3.2, "intake_face": "FRONT"
  },
  "total_wattage": 8.5, "material": "ABS",
  "strategy_name": "CHIMNEY_THERMAL", "ventilation_enabled": true
}"""

_CHIMNEY_8W_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
TOPOLOGY: CHIMNEY_THERMAL — chimney stack above hottest zone.
GEOMETRY: 88.4 x 58.4 x 16mm body + 32mm chimney.
THERMAL: 8.5W requires chimney convection. 24x24mm chimney above centre.
======================================= */

use <../module_library/strategies/chimney_thermal/base_body.scad>
use <../module_library/strategies/chimney_thermal/chimney_stack.scad>
use <../module_library/strategies/chimney_thermal/lid.scad>

outer_length = 88.4;
outer_width = 58.4;
outer_height = 16.0;
wall = 1.2;
lid_thickness = 1.44;
body_height = outer_height - lid_thickness;
chimney_x = 44.2;
chimney_y = 29.2;
chimney_width = 24.0;
chimney_length = 24.0;
chimney_height = 32.0;
intake_slot_z = 3.2;
$fn = 30;

// Main body with chimney opening and intake slots
chimney_base_body(outer_length, outer_width, body_height, wall,
                   chimney_x, chimney_y, chimney_width, chimney_length,
                   intake_slot_z);

// Chimney stack on top
translate([chimney_x - chimney_width/2, chimney_y - chimney_length/2, body_height])
    chimney_stack(chimney_width, chimney_length, chimney_height, wall);

// Lid (placed beside)
translate([outer_length + 10, 0, 0])
    chimney_lid(outer_length, outer_width, lid_thickness,
                chimney_x, chimney_y, chimney_width, chimney_length);"""

# ═══════════════════════════════════════════════════════════════
# DIN_RAIL_CLIP Example
# ═══════════════════════════════════════════════════════════════

_DIN_RAIL_CONSTRAINT = """{
  "pcb": {"length": 60.0, "width": 40.0, "thickness": 1.6},
  "enclosure": {
    "outer_length": 68.4, "outer_width": 48.4, "outer_height": 18.0,
    "wall": 1.5, "clearance": 3.0, "lid_thickness": 1.8
  },
  "topology_extensions": {
    "din_rail_width": 35.0, "din_clip_engagement_depth": 5.5,
    "din_clip_spring_length": 14.0, "din_clip_release_tab_height": 8.0
  },
  "material": "ABS", "strategy_name": "DIN_RAIL_CLIP", "ventilation_enabled": true
}"""

_DIN_RAIL_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
TOPOLOGY: DIN_RAIL_CLIP — IEC 60715 standard 35.0mm rail.
GEOMETRY: 68.4 x 48.4 x 18mm. DIN clip on back face.
MOUNTING: 35.0mm rail width, 5.5mm engagement, 14mm spring.
======================================= */

use <../module_library/strategies/din_rail_clip/body.scad>
use <../module_library/strategies/din_rail_clip/din_clip.scad>
use <../module_library/strategies/din_rail_clip/lid.scad>

outer_length = 68.4;
outer_width = 48.4;
outer_height = 18.0;
wall = 1.5;
lid_thickness = 1.8;
body_height = outer_height - lid_thickness;
din_rail_width = 35.0;
$fn = 30;

// Body with side louver vents
din_rail_body(outer_length, outer_width, body_height, wall);

// DIN rail clip on back face
translate([(outer_length - din_rail_width) / 2, outer_width, wall + 2])
    din_rail_clip(35.0, 5.5, 14.0, 8.0, outer_width);

// Screwed lid (placed beside)
translate([outer_length + 10, 0, 0])
    din_rail_lid(outer_length, outer_width, lid_thickness);"""

# ═══════════════════════════════════════════════════════════════
# WEARABLE_ROUNDED Example
# ═══════════════════════════════════════════════════════════════

_WEARABLE_CONSTRAINT = """{
  "pcb": {"length": 30.0, "width": 20.0, "thickness": 1.0},
  "enclosure": {
    "outer_length": 38.4, "outer_width": 28.4, "outer_height": 10.0,
    "wall": 1.0, "clearance": 3.0, "lid_thickness": 1.2
  },
  "topology_extensions": {
    "corner_radius": 7.0, "edge_fillet": 1.5,
    "band_lug_width": 8.0, "band_lug_height": 4.0
  },
  "material": "SLA_TOUGH", "strategy_name": "WEARABLE_ROUNDED", "ventilation_enabled": false
}"""

_WEARABLE_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
TOPOLOGY: WEARABLE_ROUNDED — rounded exterior with band lugs.
GEOMETRY: 38.4 x 28.4 x 10mm. Corner radius 7mm, edge fillet 1.5mm.
FEATURES: Band lugs on sides. No visible vents — perimeter gap only.
======================================= */

use <../module_library/strategies/wearable_rounded/lower_shell.scad>
use <../module_library/strategies/wearable_rounded/upper_shell.scad>
use <../module_library/strategies/wearable_rounded/band_lug.scad>

outer_length = 38.4;
outer_width = 28.4;
outer_height = 10.0;
wall = 1.0;
half_height = 5.0;
corner_radius = 7.0;
edge_fillet = 1.5;
band_lug_width = 8.0;
band_lug_height = 4.0;
$fn = 30;

// Lower shell with rounded corners
wearable_lower_shell(outer_length, outer_width, half_height, wall,
                      corner_radius, edge_fillet);

// Band lugs on sides
translate([outer_length/2 - band_lug_width/2, 0, 0])
    band_lug_pair(outer_width, band_lug_width, band_lug_height, half_height);

// Upper shell (placed beside)
translate([outer_length + 10, 0, 0])
    wearable_upper_shell(outer_length, outer_width, half_height, wall,
                          corner_radius, edge_fillet);"""


# ═══════════════════════════════════════════════════════════════
# Legacy Aliases (backward compatibility for interface.py)
# ═══════════════════════════════════════════════════════════════

ESP32_SCAD_OUTPUT = _RECT_ESP32_SCAD
ARDUINO_SCAD_OUTPUT = _RECT_ARDUINO_SCAD
CUSTOM_SCAD_OUTPUT = _RECT_ESP32_SCAD  # Fallback for custom boards


# ═══════════════════════════════════════════════════════════════
# Topology-Keyed Library
# ═══════════════════════════════════════════════════════════════

FEW_SHOT_LIBRARY: dict[str, list[tuple[str, str, str]]] = {
    "RECTANGULAR_FLAT_LID": [
        ("ESP32 DevKit V1", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
        ("Arduino Uno R3", _RECT_ARDUINO_CONSTRAINT, _RECT_ARDUINO_SCAD),
    ],
    "RECTANGULAR_RIBBED_LID": [
        ("ESP32 DevKit V1 (ribbed)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
    "CLAMSHELL_HORIZONTAL": [
        ("Clamshell Small (50x30)", _CLAMSHELL_SMALL_CONSTRAINT, _CLAMSHELL_SMALL_SCAD),
    ],
    "CLAMSHELL_VERTICAL": [
        ("Clamshell Small (vertical)", _CLAMSHELL_SMALL_CONSTRAINT, _CLAMSHELL_SMALL_SCAD),
    ],
    "CHIMNEY_THERMAL": [
        ("Chimney 8W Board", _CHIMNEY_8W_CONSTRAINT, _CHIMNEY_8W_SCAD),
    ],
    "DIN_RAIL_CLIP": [
        ("DIN Rail Small Controller", _DIN_RAIL_CONSTRAINT, _DIN_RAIL_SCAD),
    ],
    "WEARABLE_ROUNDED": [
        ("Wearable 30x20mm", _WEARABLE_CONSTRAINT, _WEARABLE_SCAD),
    ],
    "INDUSTRIAL_FLANGED": [
        ("ESP32 DevKit V1 (flanged)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
    "THREE_PIECE_ACCESS": [
        ("ESP32 DevKit V1 (3-piece)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
    "PANEL_MOUNT_BEZEL": [
        ("ESP32 DevKit V1 (panel)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
    "SEALED_IP_RATED": [
        ("ESP32 DevKit V1 (sealed)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
    "SNAP_RAIL_MODULAR": [
        ("ESP32 DevKit V1 (modular)", _RECT_ESP32_CONSTRAINT, _RECT_ESP32_SCAD),
    ],
}


def get_topology_few_shot(topology_name: str, count: int = 2) -> str:
    """Get formatted few-shot examples for a specific topology."""
    examples = FEW_SHOT_LIBRARY.get(topology_name, FEW_SHOT_LIBRARY["RECTANGULAR_FLAT_LID"])
    
    parts = []
    for i, (name, json_str, scad_str) in enumerate(examples[:count]):
        parts.append(
            f"=== FEW-SHOT EXAMPLE {i+1}: {name} ===\n"
            f"// INPUT:\n{json_str.strip()}\n"
            f"// OUTPUT:\n{scad_str.strip()}"
        )
    return "\n\n".join(parts)


def get_few_shot_examples(count: int = 3) -> str:
    """Legacy function — returns rectangular flat lid examples."""
    return get_topology_few_shot("RECTANGULAR_FLAT_LID", count)
