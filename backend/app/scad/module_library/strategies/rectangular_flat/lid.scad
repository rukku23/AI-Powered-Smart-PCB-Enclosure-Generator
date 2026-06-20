// EnclosureAI — Rectangular Flat: Lid Module
// Flat lid plate with optional snap-fit recesses or screw holes.
//
// Parameters:
//   outer_length   - Outer X dimension (mm)
//   outer_width    - Outer Y dimension (mm)
//   lid_thickness  - Lid Z thickness (mm)

module rectangular_lid(outer_length, outer_width, lid_thickness) {
    cube([outer_length, outer_width, lid_thickness]);
}
