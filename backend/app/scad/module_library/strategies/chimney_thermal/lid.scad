// EnclosureAI — Chimney Thermal: Lid Module
// Lid with chimney pass-through hole.
//
// Parameters:
//   outer_length    - Outer X dimension (mm)
//   outer_width     - Outer Y dimension (mm)
//   lid_thickness   - Lid Z thickness (mm)
//   chimney_x       - Chimney center X position (mm)
//   chimney_y       - Chimney center Y position (mm)
//   chimney_width   - Chimney opening width (mm)
//   chimney_length  - Chimney opening length (mm)

module chimney_lid(outer_length, outer_width, lid_thickness,
                    chimney_x, chimney_y, chimney_width, chimney_length) {
    difference() {
        cube([outer_length, outer_width, lid_thickness]);
        
        // Chimney pass-through
        translate([chimney_x - chimney_width/2, chimney_y - chimney_length/2, -0.1])
            cube([chimney_width, chimney_length, lid_thickness + 0.2]);
    }
}
