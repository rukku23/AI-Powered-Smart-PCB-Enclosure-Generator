// === ENCLOSUREAI CORE MODEL: Generic Rectangular ===
// Parametric base model for custom/unknown boards

module generic_enclosure_body(outer_w, outer_d, outer_h, wall) {
    body_h = outer_h - wall;
    $fn = 50;
    
    difference() {
        cube([outer_w, outer_d, body_h]);
        translate([wall, wall, wall])
            cube([outer_w - 2*wall, outer_d - 2*wall, body_h]);
    }
}

module generic_enclosure_lid(outer_w, outer_d, lid_t) {
    cube([outer_w, outer_d, lid_t]);
}

module standoffs(positions, standoff_od, standoff_id, standoff_h, wall) {
    for (pos = positions) {
        translate([pos[0], pos[1], wall])
            difference() {
                cylinder(d=standoff_od, h=standoff_h);
                cylinder(d=standoff_id, h=standoff_h + 0.1);
            }
    }
}
