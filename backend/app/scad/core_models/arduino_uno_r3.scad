// === ENCLOSUREAI CORE MODEL: Arduino Uno R3 ===
// Parametric base model for Arduino Uno R3

module arduino_uno_enclosure_body(outer_w, outer_d, outer_h, wall, standoff_h=5.0) {
    body_h = outer_h - wall;
    $fn = 50;
    
    difference() {
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }
    
    // Arduino Uno Mounting Holes
    // PCB is 53.4 x 68.6. Assuming placement centered.
    board_w = 53.4;
    board_l = 68.6;
    cx = outer_w / 2;
    cy = outer_d / 2;
    
    // Exact hole offsets from Arduino Uno spec (bottom left origin of PCB)
    // [14.0, 2.54], [66.04, 7.62], [66.04, 35.56], [15.24, 50.8]
    pcb_origin_x = cx - board_w / 2;
    pcb_origin_y = cy - board_l / 2;
    
    positions = [
        [pcb_origin_x + 14.0,  pcb_origin_y + 2.54],
        [pcb_origin_x + 15.24, pcb_origin_y + 50.8],
        [pcb_origin_x + 50.8,  pcb_origin_y + 15.24] // Approx
    ];
    
    for (pos = positions) {
        translate([pos[0], pos[1], wall])
            difference() {
                cylinder(d=6.4, h=standoff_h);
                cylinder(d=3.2, h=standoff_h + 0.1);
            }
    }
}

module arduino_uno_enclosure_lid(outer_w, outer_d, lid_t) {
    cube([outer_w, outer_d, lid_t]);
}
