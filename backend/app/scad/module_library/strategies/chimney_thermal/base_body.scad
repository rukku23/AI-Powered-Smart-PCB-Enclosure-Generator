// EnclosureAI — Chimney Thermal: Base Body Module
// Rectangular body with chimney opening on top face and intake slots.
//
// Parameters:
//   outer_length   - Outer X dimension (mm)
//   outer_width    - Outer Y dimension (mm)
//   body_height    - Body height excluding lid (mm)
//   wall           - Wall thickness (mm)
//   chimney_x      - Chimney center X position (mm)
//   chimney_y      - Chimney center Y position (mm)
//   chimney_width  - Chimney opening width (mm)
//   chimney_length - Chimney opening length (mm)
//   intake_slot_z  - Z position of intake slots (mm)

module chimney_base_body(outer_length, outer_width, body_height, wall,
                          chimney_x, chimney_y, chimney_width, chimney_length,
                          intake_slot_z) {
    $fn = 30;
    
    difference() {
        // Outer shell
        cube([outer_length, outer_width, body_height]);
        
        // Hollow interior
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, body_height]);
        
        // Chimney opening on top
        translate([chimney_x - chimney_width/2, chimney_y - chimney_length/2, body_height - wall - 0.1])
            cube([chimney_width, chimney_length, wall + 0.2]);
        
        // Intake slots on front face (3 slots)
        for (i = [0:2]) {
            translate([-0.1, outer_width * 0.25 + i * 8, intake_slot_z + i * 5])
                cube([wall + 0.2, 5, 2]);
        }
        
        // Intake slots on back face (3 slots)
        for (i = [0:2]) {
            translate([outer_length - wall - 0.1, outer_width * 0.25 + i * 8, intake_slot_z + i * 5])
                cube([wall + 0.2, 5, 2]);
        }
    }
}
