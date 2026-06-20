// === ENCLOSUREAI CORE MODEL: Raspberry Pi 4 ===
// Parametric base model for Raspberry Pi 4 Model B

module rpi4_enclosure_body(outer_w, outer_d, outer_h, wall, standoff_h=5.0) {
    body_h = outer_h - wall;
    $fn = 50;
    
    difference() {
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }
    
    // RPi 4 Mounting Holes (85mm x 56mm PCB)
    // Holes are at 3.5mm from edges. Pitch is 58mm x 49mm
    board_w = 56.0;
    board_l = 85.0;
    cx = outer_w / 2;
    cy = outer_d / 2;
    
    pcb_x = cx - board_w / 2;
    pcb_y = cy - board_l / 2;
    
    positions = [
        [pcb_x + 3.5, pcb_y + 3.5],
        [pcb_x + board_w - 3.5, pcb_y + 3.5],
        [pcb_x + 3.5, pcb_y + board_l - 3.5],
        [pcb_x + board_w - 3.5, pcb_y + board_l - 3.5]
    ];
    
    for (pos = positions) {
        translate([pos[0], pos[1], wall])
            difference() {
                cylinder(d=5.5, h=standoff_h);
                cylinder(d=2.75, h=standoff_h + 0.1); // M2.5 screws for pi
            }
    }
}

module rpi4_enclosure_lid(outer_w, outer_d, lid_t) {
    cube([outer_w, outer_d, lid_t]);
}
