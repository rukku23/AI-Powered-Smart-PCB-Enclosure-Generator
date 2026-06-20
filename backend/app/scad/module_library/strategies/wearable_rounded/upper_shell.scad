// EnclosureAI — Wearable Rounded: Upper Shell Module
// Top half of a wearable enclosure with matching rounded profile.
//
// Parameters:
//   outer_length   - Outer X dimension (mm)
//   outer_width    - Outer Y dimension (mm)
//   half_height    - Height of this half (mm)
//   wall           - Wall thickness (mm)
//   corner_radius  - XY corner rounding radius (mm)
//   edge_fillet    - Z edge rounding (mm)

module wearable_upper_shell(outer_length, outer_width, half_height, wall,
                             corner_radius, edge_fillet) {
    $fn = 30;
    
    eff_length = outer_length - 2 * corner_radius;
    eff_width = outer_width - 2 * corner_radius;
    eff_height = half_height - edge_fillet;
    
    difference() {
        // Outer rounded shell
        minkowski() {
            translate([corner_radius, corner_radius, 0])
                cube([eff_length, eff_width, eff_height]);
            cylinder(r=corner_radius, h=edge_fillet);
        }
        
        // Inner cavity
        inner_radius = max(0.5, corner_radius - wall);
        inner_length = eff_length + 2 * (corner_radius - wall) - 2 * inner_radius;
        inner_width = eff_width + 2 * (corner_radius - wall) - 2 * inner_radius;
        
        translate([wall, wall, 0])
        minkowski() {
            translate([inner_radius, inner_radius, 0])
                cube([inner_length, inner_width, half_height - wall]);
            cylinder(r=inner_radius, h=0.01);
        }
    }
}
