// EnclosureAI — Common Module: Standoff
// PCB mounting standoff with screw hole.
//
// Parameters:
//   outer_d   - Outer diameter (mm)
//   inner_d   - Screw hole diameter (mm)
//   height    - Standoff height from base (mm)

module standoff(outer_d=6.4, inner_d=3.2, height=5) {
    $fn = 30;
    difference() {
        cylinder(d=outer_d, h=height);
        translate([0, 0, -0.1])
            cylinder(d=inner_d, h=height + 0.2);
    }
}

module standoff_array(positions, outer_d=6.4, inner_d=3.2, height=5) {
    // positions = [[x,y], [x,y], ...]
    for (pos = positions) {
        translate([pos[0], pos[1], 0])
            standoff(outer_d, inner_d, height);
    }
}
