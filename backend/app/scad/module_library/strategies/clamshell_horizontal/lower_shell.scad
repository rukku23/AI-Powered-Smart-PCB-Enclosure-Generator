// EnclosureAI — Clamshell Horizontal: Lower Shell Module
// Bottom half of a horizontal-split clamshell enclosure.
// Includes PCB side grooves and front latch pocket.
//
// Parameters:
//   outer_length     - Outer X dimension (mm)
//   outer_width      - Outer Y dimension (mm)
//   half_height      - Height of this half (mm)
//   wall             - Wall thickness (mm)
//   pcb_groove_z     - Z position of PCB groove (mm)
//   pcb_groove_depth - Groove depth into wall (mm)
//   pcb_groove_width - Groove slot width (mm)
//   latch_x          - X position of front latch (mm)
//   latch_y          - Y position of front latch (mm)

module clamshell_lower_shell(outer_length, outer_width, half_height, wall,
                              pcb_groove_z, pcb_groove_depth, pcb_groove_width,
                              latch_x, latch_y) {
    $fn = 30;
    
    difference() {
        // Outer shell
        cube([outer_length, outer_width, half_height]);
        
        // Hollow interior
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, half_height]);
        
        // PCB groove on left wall
        translate([wall, wall - 0.1, pcb_groove_z])
            cube([outer_length - 2*wall, pcb_groove_depth + 0.1, pcb_groove_width]);
        
        // PCB groove on right wall
        translate([wall, outer_width - wall - pcb_groove_depth, pcb_groove_z])
            cube([outer_length - 2*wall, pcb_groove_depth + 0.1, pcb_groove_width]);
    }
    
    // Front latch catch (small bump)
    translate([latch_x - 3, 0, half_height - 3])
        cube([6, wall * 0.5, 2]);
}
