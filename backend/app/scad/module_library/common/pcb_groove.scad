// EnclosureAI — Common Module: PCB Groove
// Side-wall groove for press-fit PCB mounting (clamshell topology).
//
// Parameters:
//   groove_length  - Length of the groove along wall (mm)
//   groove_depth   - Depth into the wall (mm)
//   groove_width   - Width of groove slot (mm, should be PCB thickness + tolerance)
//   groove_z       - Z position of groove bottom (mm)

module pcb_groove(groove_length=50, groove_depth=1.5, groove_width=2.0, groove_z=5) {
    translate([0, 0, groove_z])
        cube([groove_length, groove_depth, groove_width]);
}
