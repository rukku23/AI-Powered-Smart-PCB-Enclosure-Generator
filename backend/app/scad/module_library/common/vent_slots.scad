// EnclosureAI — Common Module: Vent Slots
// Parametric ventilation slot array.
//
// Parameters:
//   slot_count    - Number of slots
//   slot_width    - Width of each slot (mm)
//   slot_length   - Length of each slot (mm)
//   slot_spacing  - Space between slots (mm)
//   wall          - Wall thickness to cut through (mm)

module vent_slots(slot_count=4, slot_width=2.5, slot_length=15, slot_spacing=4, wall=1.2) {
    total_width = slot_count * slot_width + (slot_count - 1) * slot_spacing;
    start_x = -total_width / 2;
    
    for (i = [0 : slot_count - 1]) {
        translate([start_x + i * (slot_width + slot_spacing), -slot_length/2, -0.1])
            cube([slot_width, slot_length, wall + 0.2]);
    }
}

module side_louvers(count=5, louver_width=2, louver_height=8, spacing=3, wall=1.2) {
    // Side-mounted louver vents (horizontal slats)
    total_height = count * louver_width + (count - 1) * spacing;
    start_z = -total_height / 2;
    
    for (i = [0 : count - 1]) {
        translate([-0.1, 0, start_z + i * (louver_width + spacing)])
            cube([wall + 0.2, louver_height, louver_width]);
    }
}
