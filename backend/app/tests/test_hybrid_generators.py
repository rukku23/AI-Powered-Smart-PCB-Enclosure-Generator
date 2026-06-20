"""
Verify that the hybrid procedural+LLM architecture produces
structurally different outputs per topology and that the procedural
base includes standoffs, vents, and topology-specific features.
"""
from app.core.topology_router import route_topology

BASE_PARAMS = {
    "width": 60,
    "depth": 80,
    "height": 30,
    "wall_thickness": 2,
    "lid_thickness": 1.5,
    "standoff_height": 5.0,
    "standoff_od": 6.4,
    "standoff_id": 3.2,
    "mounting_hole_positions": [[8, 8], [52, 8], [8, 72], [52, 72]],
    "vent_count": 6,
    "vent_size": 2.5,
    "tolerance": 0.2,
}

def test_rectangular_has_modules():
    scad = route_topology("RECTANGULAR_FLAT_LID", BASE_PARAMS)
    assert "module enclosure_body()" in scad
    assert "module enclosure_lid()" in scad
    assert "module standoffs()" in scad
    assert "module vent_slots()" in scad
    # Must NOT have instantiation calls at the end
    assert "enclosure_body();" not in scad.split("module")[-1]

def test_rectangular_has_standoff_positions():
    scad = route_topology("RECTANGULAR_FLAT_LID", BASE_PARAMS)
    assert "[8, 8]" in scad
    assert "[52, 72]" in scad

def test_rectangular_has_vent_count():
    scad = route_topology("RECTANGULAR_FLAT_LID", BASE_PARAMS)
    assert "6 vent slots" in scad.lower() or "0 : 5" in scad

def test_chimney_has_chimney_features():
    params = {**BASE_PARAMS, "chimney_width": 24, "chimney_length": 24,
              "chimney_height": 50, "chimney_x": 30, "chimney_y": 40}
    scad = route_topology("CHIMNEY_THERMAL", params)
    assert "CHIMNEY_THERMAL" in scad
    assert "chimney_stack" in scad.lower() or "chimney" in scad.lower()
    assert "linear_extrude" in scad or "chimney_h" in scad
    assert "intake_slots" in scad or "intake" in scad.lower()
    assert "vent_cap" in scad.lower() or "rain cap" in scad.lower()

def test_dinrail_has_clip():
    params = {**BASE_PARAMS, "din_rail_width": 35.0,
              "din_clip_engagement_depth": 5.5, "din_clip_spring_length": 14.0}
    scad = route_topology("DIN_RAIL_CLIP", params)
    assert "DIN_RAIL_CLIP" in scad
    assert "din_rail_clip()" in scad or "din_rail_w" in scad
    assert "35" in scad  # 35mm standard

def test_wearable_has_minkowski():
    params = {**BASE_PARAMS, "width": 40, "depth": 30, "height": 15,
              "corner_radius": 7.0, "band_lug_width": 8.0, "band_lug_height": 4.0}
    scad = route_topology("WEARABLE_ROUNDED", params)
    assert "WEARABLE_ROUNDED" in scad
    assert "minkowski" in scad
    assert "sphere" in scad
    assert "band_lug" in scad.lower()

def test_clamshell_has_two_shells():
    scad = route_topology("CLAMSHELL_HORIZONTAL", BASE_PARAMS)
    assert "CLAMSHELL_HORIZONTAL" in scad
    assert "lower_shell()" in scad
    assert "upper_shell()" in scad
    assert "Hinge" in scad or "hinge" in scad
    assert "latch" in scad.lower() or "Snap" in scad

def test_all_topologies_differ():
    names = ["RECTANGULAR_FLAT_LID", "CHIMNEY_THERMAL", "DIN_RAIL_CLIP",
             "WEARABLE_ROUNDED", "CLAMSHELL_HORIZONTAL"]
    params = {**BASE_PARAMS, "chimney_width": 24, "chimney_length": 24,
              "chimney_height": 50, "chimney_x": 30, "chimney_y": 40,
              "din_rail_width": 35.0, "corner_radius": 7.0,
              "band_lug_width": 8.0, "band_lug_height": 4.0}
    outputs = {n: route_topology(n, params) for n in names}

    # Every pair must differ by > 300 chars
    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            # Count differing characters
            s1, s2 = outputs[n1], outputs[n2]
            shared = sum(1 for a, b in zip(s1, s2) if a == b)
            diff_chars = max(len(s1), len(s2)) - shared
            assert diff_chars > 300, (
                f"{n1} vs {n2} differ by only {diff_chars} chars"
            )
