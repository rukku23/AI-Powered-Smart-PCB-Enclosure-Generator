// EnclosureAI — Wearable Rounded: Band Lug Module
// Strap/band attachment lugs on left and right sides.
//
// Parameters:
//   lug_width   - Width of each lug (mm)
//   lug_height  - Protrusion height (mm)
//   lug_depth   - Depth/thickness of lug (mm)
//   slot_width  - Band slot width (mm)
//   slot_height - Band slot height (mm)

module band_lug(lug_width=8, lug_height=4, lug_depth=3,
                 slot_width=6, slot_height=2) {
    $fn = 30;
    
    difference() {
        // Lug body
        hull() {
            cube([lug_width, lug_depth, 0.1]);
            translate([0, 0, lug_height])
                cube([lug_width, lug_depth, 0.1]);
        }
        
        // Band slot
        translate([(lug_width - slot_width) / 2, -0.1, (lug_height - slot_height) / 2])
            cube([slot_width, lug_depth + 0.2, slot_height]);
    }
}

module band_lug_pair(outer_width, lug_width=8, lug_height=4, shell_height=10) {
    // Left side lug
    translate([0, -lug_height, shell_height / 2 - lug_height / 2])
        band_lug(lug_width, lug_height);
    
    // Right side lug
    translate([0, outer_width, shell_height / 2 - lug_height / 2])
        band_lug(lug_width, lug_height);
}
