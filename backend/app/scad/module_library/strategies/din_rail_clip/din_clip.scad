// EnclosureAI — DIN Rail Clip: DIN Clip Module
// Standard 35mm DIN rail (IEC 60715) clip mechanism.
// ALL dimensions are standards — do NOT modify.
//
// Parameters:
//   din_rail_width            - 35.0 (IEC 60715 standard, FIXED)
//   din_clip_engagement_depth - 5.5 (mm, FIXED)
//   din_clip_spring_length    - 14.0 (mm, FIXED)
//   din_clip_release_tab_height - 8.0 (mm, FIXED)
//   body_width                - Width of the enclosure body (mm)

module din_rail_clip(din_rail_width=35.0,
                      din_clip_engagement_depth=5.5,
                      din_clip_spring_length=14.0,
                      din_clip_release_tab_height=8.0,
                      body_width=40) {
    $fn = 30;
    
    clip_thickness = 1.5;
    
    // Fixed clip — upper hook
    translate([0, 0, 0]) {
        // Vertical arm
        cube([din_rail_width, clip_thickness, din_clip_spring_length]);
        // Hook overhang
        translate([0, -din_clip_engagement_depth, din_clip_spring_length - 2])
            cube([din_rail_width, din_clip_engagement_depth, 2]);
    }
    
    // Spring clip — lower hook with release tab
    translate([0, 0, -din_clip_spring_length - 2]) {
        // Spring arm (flexible)
        cube([din_rail_width, clip_thickness * 0.8, din_clip_spring_length]);
        // Hook
        translate([0, -din_clip_engagement_depth, 0])
            cube([din_rail_width, din_clip_engagement_depth, 2]);
        // Release tab extending below
        translate([din_rail_width * 0.3, clip_thickness, -din_clip_release_tab_height])
            cube([din_rail_width * 0.4, clip_thickness, din_clip_release_tab_height]);
    }
}
