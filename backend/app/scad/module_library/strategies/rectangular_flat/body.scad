// EnclosureAI — Rectangular Flat: Body Module
// Standard rectangular enclosure body with hollow interior.
//
// Parameters:
//   outer_length  - Outer X dimension (mm)
//   outer_width   - Outer Y dimension (mm)
//   body_height   - Body height excluding lid (mm)
//   wall          - Wall thickness (mm)

module rectangular_body(outer_length, outer_width, body_height, wall) {
    difference() {
        cube([outer_length, outer_width, body_height]);
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, body_height]);
    }
}
