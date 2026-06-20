// EnclosureAI — Chimney Thermal: Chimney Stack Module
// Vertical chimney extension above thermal hotspot for natural convection.
//
// Parameters:
//   chimney_width   - Width of chimney (mm)
//   chimney_length  - Length of chimney (mm)
//   chimney_height  - Height of chimney above body (mm)
//   wall            - Wall thickness (mm)

module chimney_stack(chimney_width, chimney_length, chimney_height, wall) {
    $fn = 30;
    
    difference() {
        // Outer chimney walls
        cube([chimney_width, chimney_length, chimney_height]);
        
        // Hollow interior
        translate([wall, wall, -0.1])
            cube([chimney_width - 2*wall, chimney_length - 2*wall, chimney_height - wall + 0.1]);
        
        // Exhaust slots on top (3 slots across width)
        slot_width = 2.5;
        slot_spacing = (chimney_width - 3 * slot_width) / 4;
        for (i = [0:2]) {
            translate([slot_spacing + i * (slot_width + slot_spacing),
                       chimney_length * 0.2,
                       chimney_height - wall - 0.1])
                cube([slot_width, chimney_length * 0.6, wall + 0.2]);
        }
    }
}
