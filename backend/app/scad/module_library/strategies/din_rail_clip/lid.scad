// EnclosureAI — DIN Rail Clip: Lid Module
// Screwed lid for DIN rail enclosure (no snap-fit — vibration env).
//
// Parameters:
//   outer_length   - Outer X dimension (mm)
//   outer_width    - Outer Y dimension (mm)
//   lid_thickness  - Lid Z thickness (mm)
//   screw_d        - Screw hole diameter (mm)
//   screw_inset    - Screw hole inset from edges (mm)

module din_rail_lid(outer_length, outer_width, lid_thickness,
                     screw_d=3.2, screw_inset=5) {
    $fn = 30;
    
    difference() {
        cube([outer_length, outer_width, lid_thickness]);
        
        // 4 corner screw holes
        positions = [
            [screw_inset, screw_inset],
            [outer_length - screw_inset, screw_inset],
            [screw_inset, outer_width - screw_inset],
            [outer_length - screw_inset, outer_width - screw_inset]
        ];
        for (pos = positions) {
            translate([pos[0], pos[1], -0.1])
                cylinder(d=screw_d, h=lid_thickness + 0.2);
        }
    }
}
