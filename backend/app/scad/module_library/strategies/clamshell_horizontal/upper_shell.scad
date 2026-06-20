// EnclosureAI — Clamshell Horizontal: Upper Shell Module
// Top half of a horizontal-split clamshell enclosure.
// Includes hinge barrel on back edge.
//
// Parameters:
//   outer_length  - Outer X dimension (mm)
//   outer_width   - Outer Y dimension (mm)
//   half_height   - Height of this half (mm)
//   wall          - Wall thickness (mm)
//   hinge_x       - X position of hinge center (mm)
//   hinge_z       - Z position of hinge (mm)

module clamshell_upper_shell(outer_length, outer_width, half_height, wall,
                              hinge_x, hinge_z) {
    $fn = 30;
    
    difference() {
        // Outer shell (inverted — open side faces down)
        cube([outer_length, outer_width, half_height]);
        
        // Hollow interior
        translate([wall, wall, 0])
            cube([outer_length - 2*wall, outer_width - 2*wall, half_height - wall]);
    }
    
    // Hinge barrel on back edge
    translate([hinge_x, outer_width, 0])
        rotate([0, 0, 0])
            hinge_barrel(barrel_length=12, barrel_od=4, barrel_id=2);
}

module hinge_barrel(barrel_length=12, barrel_od=4, barrel_id=2) {
    $fn = 30;
    rotate([0, 90, 0])
    difference() {
        cylinder(d=barrel_od, h=barrel_length, center=true);
        cylinder(d=barrel_id, h=barrel_length + 0.2, center=true);
    }
}
