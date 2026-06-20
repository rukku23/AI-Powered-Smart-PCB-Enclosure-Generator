// EnclosureAI — Clamshell Horizontal: Hinge Module
// Living hinge / barrel hinge for clamshell enclosure.
//
// Parameters:
//   hinge_length   - Length of the hinge barrel (mm)
//   barrel_od      - Outer diameter of hinge barrel (mm)
//   pin_d          - Hinge pin diameter (mm)

module hinge_assembly(hinge_length=12, barrel_od=4, pin_d=1.75) {
    $fn = 30;
    
    // Hinge barrel (split into two halves for body and lid)
    difference() {
        rotate([0, 90, 0])
            cylinder(d=barrel_od, h=hinge_length, center=true);
        rotate([0, 90, 0])
            cylinder(d=pin_d, h=hinge_length + 0.2, center=true);
    }
}

module hinge_pin(hinge_length=12, pin_d=1.75) {
    $fn = 30;
    rotate([0, 90, 0])
        cylinder(d=pin_d, h=hinge_length + 2, center=true);
}
