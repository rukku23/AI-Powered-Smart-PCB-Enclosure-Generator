"""
EnclosureAI - Procedural OpenSCAD Generators (Phase 9 v2)

Each generator outputs ONLY module definitions (enclosure_body, enclosure_lid,
standoffs, vent_slots). It does NOT instantiate them. The final assembly is
written by the LLM, which adds custom_cutouts() and the difference() block.

This separation ensures the base topology is always structurally correct,
while the LLM handles board-specific port holes and component cutouts.
"""
from __future__ import annotations
import math


def _standoff_module(params: dict) -> str:
    """Generate a standoffs() module from mounting hole positions."""
    positions = params.get("mounting_hole_positions", [])
    wall = params.get("wall_thickness", 2)
    standoff_h = params.get("standoff_height", 5.0)
    standoff_od = params.get("standoff_od", 6.4)
    standoff_id = params.get("standoff_id", 3.2)

    if not positions:
        # Auto-generate 4-corner standoffs
        w = params.get("width", 50)
        d = params.get("depth", 80)
        inset = wall + standoff_od / 2 + 1
        positions = [
            [inset, inset],
            [w - inset, inset],
            [inset, d - inset],
            [w - inset, d - inset],
        ]

    pos_str = ", ".join(f"[{p[0]}, {p[1]}]" for p in positions)
    return f"""
module standoffs() {{
    positions = [{pos_str}];
    for (pos = positions) {{
        translate([pos[0], pos[1], {wall}])
            difference() {{
                cylinder(d={standoff_od}, h={standoff_h});
                cylinder(d={standoff_id}, h={standoff_h} + 0.1);
            }}
    }}
}}
"""


def _vent_slots_module(params: dict) -> str:
    """Generate a vent_slots() module with parametric count and placement."""
    vent_count = params.get("vent_count", 0)
    if vent_count <= 0:
        return "\nmodule vent_slots() { /* No vents */ }\n"

    w = params.get("width", 50)
    d = params.get("depth", 80)
    h = params.get("height", 30)
    wt = params.get("wall_thickness", 2)
    slot_w = params.get("vent_size", 2.5)
    slot_l = min(15.0, d * 0.4)
    spacing = 4.0

    total_array_w = vent_count * slot_w + (vent_count - 1) * spacing
    start_x = (w - total_array_w) / 2
    start_y = (d - slot_l) / 2

    return f"""
module vent_slots() {{
    // {vent_count} vent slots on top face
    for (i = [0 : {vent_count - 1}]) {{
        translate([{start_x} + i * ({slot_w} + {spacing}), {start_y}, {h} - {wt} - 0.1])
            cube([{slot_w}, {slot_l}, {wt} + 0.2]);
    }}
}}
"""


def generate_rectangular_scad(params: dict) -> str:
    w = params.get("width", 50)
    d = params.get("depth", 80)
    h = params.get("height", 30)
    wt = params.get("wall_thickness", 2)
    lid_t = params.get("lid_thickness", wt)

    body_h = h - lid_t

    return f"""// === ENCLOSUREAI PROCEDURAL BASE: RECTANGULAR_FLAT_LID ===
$fn = 50;

// --- Dimensions ---
outer_w = {w};
outer_d = {d};
outer_h = {h};
wall    = {wt};
lid_t   = {lid_t};
body_h  = {body_h};

module enclosure_body() {{
    difference() {{
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }}
}}

module enclosure_lid() {{
    cube([outer_w, outer_d, lid_t]);
}}
{_standoff_module(params)}
{_vent_slots_module(params)}
"""


def generate_chimney_scad(params: dict) -> str:
    w = params.get("width", 50)
    d = params.get("depth", 80)
    h = params.get("height", 30)
    wt = params.get("wall_thickness", 2)
    lid_t = params.get("lid_thickness", wt)
    body_h = h - lid_t

    ch_w = params.get("chimney_width", 20)
    ch_l = params.get("chimney_length", 20)
    ch_h = params.get("chimney_height", max(h * 2, 60.0))
    ch_x = params.get("chimney_x", w / 2)
    ch_y = params.get("chimney_y", d / 2)

    return f"""// === ENCLOSUREAI PROCEDURAL BASE: CHIMNEY_THERMAL ===
$fn = 50;

outer_w = {w};
outer_d = {d};
outer_h = {h};
wall    = {wt};
lid_t   = {lid_t};
body_h  = {body_h};
chimney_w = {ch_w};
chimney_l = {ch_l};
chimney_h = {ch_h};
chimney_x = {ch_x};
chimney_y = {ch_y};

module enclosure_body() {{
    difference() {{
        union() {{
            // Main body
            cube([outer_w, outer_d, body_h]);
            // Chimney stack - wider base, narrowing top
            translate([chimney_x - chimney_w/2, chimney_y - chimney_l/2, body_h - 0.01])
                linear_extrude(height=chimney_h, scale=0.85)
                    square([chimney_w, chimney_l]);
        }}
        // Internal cavity
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
        // Vertical internal channel through chimney
        translate([chimney_x - chimney_w/2 + wall, chimney_y - chimney_l/2 + wall, body_h - wall])
            cube([chimney_w - 2*wall, chimney_l - 2*wall, chimney_h + wall + 1]);
        // Chimney side vent slots (4 faces x 4 slots each)
        for (face = [0:3]) {{
            rotate([0, 0, face * 90])
                translate([chimney_x - chimney_w/2 - 0.1, chimney_y - 1, body_h + chimney_h * 0.3])
                    for (i = [0:3])
                        translate([0, 0, i * 6])
                            cube([wall + 0.2, 2, 3]);
        }}
    }}
}}

module chimney_vent_cap() {{
    // Rain cap above chimney opening
    translate([chimney_x - chimney_w/2 - 2, chimney_y - chimney_l/2 - 2, body_h + chimney_h + 4])
        difference() {{
            cube([chimney_w + 4, chimney_l + 4, wall]);
            // Gap for air to exit
            translate([3, 3, -0.1])
                cube([chimney_w - 2, chimney_l - 2, wall + 0.2]);
        }}
}}

module intake_slots() {{
    // Low intake slots on front face for stack-effect airflow
    for (i = [0:5]) {{
        translate([wall + 8 + i * 7, -0.1, wall + 2])
            cube([3, wall + 0.2, 8]);
    }}
}}

module enclosure_lid() {{
    difference() {{
        cube([outer_w, outer_d, lid_t]);
        // Chimney opening in lid
        translate([chimney_x - chimney_w/2 + wall/2, chimney_y - chimney_l/2 + wall/2, -0.1])
            cube([chimney_w - wall, chimney_l - wall, lid_t + 0.2]);
    }}
}}
{_standoff_module(params)}
"""


def generate_dinrail_scad(params: dict) -> str:
    w = params.get("width", 50)
    d = params.get("depth", 80)
    h = params.get("height", 30)
    wt = params.get("wall_thickness", 2)
    lid_t = params.get("lid_thickness", wt)
    body_h = h - lid_t
    din_w = params.get("din_rail_width", 35.0)
    din_engage = params.get("din_clip_engagement_depth", 5.5)
    din_spring = params.get("din_clip_spring_length", 14.0)

    return f"""// === ENCLOSUREAI PROCEDURAL BASE: DIN_RAIL_CLIP ===
$fn = 50;

outer_w = {w};
outer_d = {d};
outer_h = {h};
wall    = {wt};
lid_t   = {lid_t};
body_h  = {body_h};
din_rail_w = {din_w};

module enclosure_body() {{
    difference() {{
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }}
}}

module din_rail_clip() {{
    // IEC 60715 standard 35mm DIN rail clip on bottom face
    clip_offset_y = (outer_d - din_rail_w) / 2;
    translate([0, clip_offset_y, -{din_engage}]) {{
        difference() {{
            cube([outer_w, din_rail_w, {din_engage}]);
            // Rail channel (T-slot profile)
            translate([wall, 2, -0.1])
                cube([outer_w - 2*wall, din_rail_w - 4, {din_engage} - 1.5]);
        }}
    }}
    // Flex clip spring tab
    translate([outer_w/2 - 5, clip_offset_y - 3, -{din_engage} - 3])
        cube([10, 3, {din_spring}]);
    // Release tab
    translate([outer_w/2 - 4, clip_offset_y + din_rail_w, -{din_engage}])
        cube([8, 3, 8]);
}}

module enclosure_lid() {{
    cube([outer_w, outer_d, lid_t]);
}}
{_standoff_module(params)}
{_vent_slots_module(params)}
"""


def generate_wearable_scad(params: dict) -> str:
    w = params.get("width", 40)
    d = params.get("depth", 30)
    h = params.get("height", 15)
    wt = params.get("wall_thickness", 1.5)
    corner_r = params.get("corner_radius", min(w, d) * 0.2)
    fillet = params.get("edge_fillet", 1.5)
    lug_w = params.get("band_lug_width", 8.0)
    lug_h = params.get("band_lug_height", 4.0)

    inner_w = max(0.1, w - 2 * corner_r)
    inner_d = max(0.1, d - 2 * corner_r)
    inner_h = max(0.1, h - corner_r)

    return f"""// === ENCLOSUREAI PROCEDURAL BASE: WEARABLE_ROUNDED ===
$fn = 60;

outer_w = {w};
outer_d = {d};
outer_h = {h};
wall    = {wt};
corner_r = {corner_r};

module enclosure_body() {{
    difference() {{
        // Rounded exterior via minkowski
        minkowski() {{
            translate([{corner_r}, {corner_r}, 0])
                cube([{inner_w}, {inner_d}, {inner_h}]);
            sphere(r={corner_r});
        }}
        // Internal cavity
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, outer_h]);
        // Flat bottom for body contact / printing
        translate([-1, -1, -{corner_r} - 1])
            cube([outer_w + 2, outer_d + 2, {corner_r} + 1]);
    }}
}}

module band_lugs() {{
    // Left lug
    translate([outer_w/2 - {lug_w}/2, -{lug_h}, 0])
        cube([{lug_w}, {lug_h}, outer_h * 0.6]);
    // Right lug
    translate([outer_w/2 - {lug_w}/2, outer_d, 0])
        cube([{lug_w}, {lug_h}, outer_h * 0.6]);
}}

module enclosure_lid() {{
    // Wearable lid clips in from bottom
    translate([wall + 0.2, wall + 0.2, 0])
        cube([outer_w - 2*wall - 0.4, outer_d - 2*wall - 0.4, wall]);
}}
{_standoff_module(params)}
"""


def generate_clamshell_scad(params: dict) -> str:
    w = params.get("width", 50)
    d = params.get("depth", 80)
    h = params.get("height", 40)
    wt = params.get("wall_thickness", 2)
    half_h = h / 2
    hinge_r = 2.5
    pin_r = 1.3

    return f"""// === ENCLOSUREAI PROCEDURAL BASE: CLAMSHELL_HORIZONTAL ===
$fn = 50;

outer_w = {w};
outer_d = {d};
outer_h = {h};
wall    = {wt};
half_h  = {half_h};

module lower_shell() {{
    difference() {{
        cube([outer_w, outer_d, half_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, half_h]);
    }}
    // Hinge barrels on back edge (3 cylinders)
    for (y_pos = [outer_d * 0.2, outer_d * 0.5, outer_d * 0.8]) {{
        translate([outer_w, y_pos, half_h])
            rotate([0, 90, 0])
                difference() {{
                    cylinder(r={hinge_r}, h=5);
                    cylinder(r={pin_r}, h=5.2);
                }}
    }}
}}

module upper_shell() {{
    difference() {{
        cube([outer_w, outer_d, half_h]);
        translate([wall, wall, 0])
            cube([outer_w - 2*wall, outer_d - 2*wall, half_h - wall]);
    }}
    // Snap latch hooks on front edge
    for (x_pos = [outer_w * 0.3, outer_w * 0.7]) {{
        translate([x_pos - 3, -2, 0])
            cube([6, 2, 4]);
        translate([x_pos - 2, -3, 3])
            cube([4, 3, 1.5]); // Hook lip
    }}
    // Hinge barrels matching lower shell
    for (y_pos = [outer_d * 0.2, outer_d * 0.5, outer_d * 0.8]) {{
        translate([outer_w, y_pos, 0])
            rotate([0, 90, 0])
                difference() {{
                    cylinder(r={hinge_r}, h=5);
                    cylinder(r={pin_r}, h=5.2);
                }}
    }}
}}

// NOTE: Lid is the upper_shell itself (clamshell = 2-piece)
module enclosure_body() {{ lower_shell(); }}
module enclosure_lid()  {{ upper_shell(); }}
{_standoff_module(params)}
{_vent_slots_module(params)}
"""
