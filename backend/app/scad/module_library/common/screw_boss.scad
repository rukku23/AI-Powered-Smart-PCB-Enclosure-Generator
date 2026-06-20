// EnclosureAI — Common Module: Screw Boss
// Parametric screw boss for screwed lid attachment.
//
// Parameters:
//   outer_d  - Outer diameter of the boss (mm)
//   inner_d  - Screw hole diameter (mm)
//   height   - Boss height (mm)

module screw_boss(outer_d=8, inner_d=3.2, height=10) {
    $fn = 30;
    difference() {
        cylinder(d=outer_d, h=height);
        translate([0, 0, -0.1])
            cylinder(d=inner_d, h=height + 0.2);
    }
}

module screw_hole(diameter=3.2, depth=10) {
    $fn = 30;
    translate([0, 0, -0.1])
        cylinder(d=diameter, h=depth + 0.2);
}
