// EnclosureAI — DIN Rail Clip: Body Module
// Enclosure body with integrated DIN rail clip mounting on back face.
//
// Parameters:
//   outer_length  - Outer X dimension (mm)
//   outer_width   - Outer Y dimension (mm)
//   body_height   - Body height excluding lid (mm)
//   wall          - Wall thickness (mm)

module din_rail_body(outer_length, outer_width, body_height, wall) {
    $fn = 30;
    
    difference() {
        // Outer shell
        cube([outer_length, outer_width, body_height]);
        
        // Hollow interior
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, body_height]);
        
        // Side louver vents (left side)
        louver_count = 4;
        louver_spacing = (body_height - 2 * wall - 10) / louver_count;
        for (i = [0 : louver_count - 1]) {
            translate([-0.1, outer_width * 0.3, wall + 5 + i * louver_spacing])
                cube([wall + 0.2, outer_width * 0.4, 2]);
        }
        
        // Side louver vents (right side)
        for (i = [0 : louver_count - 1]) {
            translate([outer_length - wall - 0.1, outer_width * 0.3, wall + 5 + i * louver_spacing])
                cube([wall + 0.2, outer_width * 0.4, 2]);
        }
    }
}
