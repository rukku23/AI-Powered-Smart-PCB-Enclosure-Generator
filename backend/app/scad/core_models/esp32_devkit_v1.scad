// === ENCLOSUREAI CORE MODEL: ESP32 DevKit V1 ===
// Parametric base model for ESP32 DevKit V1

module esp32_enclosure_body(outer_w, outer_d, outer_h, wall, standoff_h=5.0) {
    body_h = outer_h - wall;
    $fn = 50;
    
    difference() {
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }
    
    // ESP32 Standard Mounting Holes (relative to origin)
    // Board is 51x25. Inset usually 2.5mm
    // Let's assume board is centered in the enclosure
    board_w = 25.0;
    board_l = 51.0;
    cx = outer_w / 2;
    cy = outer_d / 2;
    
    positions = [
        [cx - board_w/2 + 2.5, cy - board_l/2 + 2.5],
        [cx + board_w/2 - 2.5, cy - board_l/2 + 2.5],
        [cx - board_w/2 + 2.5, cy + board_l/2 - 2.5],
        [cx + board_w/2 - 2.5, cy + board_l/2 - 2.5]
    ];
    
    for (pos = positions) {
        translate([pos[0], pos[1], wall])
            difference() {
                cylinder(d=6.4, h=standoff_h);
                cylinder(d=3.2, h=standoff_h + 0.1);
            }
    }
}

module esp32_enclosure_lid(outer_w, outer_d, lid_t) {
    cube([outer_w, outer_d, lid_t]);
}
