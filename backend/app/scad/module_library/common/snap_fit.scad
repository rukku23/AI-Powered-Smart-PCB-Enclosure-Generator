// EnclosureAI — Common Module: Snap-Fit Tab
// Parametric snap-fit cantilever tab for lid-body connection.
//
// Parameters:
//   tab_width     - Width of the snap tab (mm)
//   tab_height    - Height of the cantilever (mm)
//   wall          - Wall thickness (mm)
//   overhang      - Hook overhang depth (mm)
//   gap           - Clearance gap (mm)

module snap_fit_tab(tab_width=6, tab_height=3, wall=1.2, overhang=0.8, gap=0.3) {
    // Cantilever beam with hook
    union() {
        // Main cantilever body
        cube([tab_width, wall * 0.8, tab_height]);
        // Hook overhang at top
        translate([0, -overhang, tab_height - 0.6])
            cube([tab_width, wall * 0.8 + overhang, 0.6]);
    }
}

module snap_fit_recess(tab_width=6, tab_height=3, wall=1.2, gap=0.3) {
    // Recess in lid for snap-fit tab clearance
    cube([tab_width + gap, wall + 0.2, tab_height + gap]);
}
