import asyncio
from app.schemas.input_schemas import EnclosureRequest, PRESETS
from app.schemas.constraint_schemas import ConstraintSchema
from app.scad.validator import generate_validated_scad
from app.llm.interface import get_llm

async def main():
    llm = get_llm()
    # Mock LLM generation output
    class MockLLM:
        async def generate(self, _):
            return """
/* === ENCLOSUREAI DESIGN REASONING ===
Test reasoning
======================================= */
module custom_cutouts() {
    translate([10, -0.1, 5]) cube([12, 3, 11]);
}
// === FINAL ASSEMBLY ===
difference() {
    enclosure_body();
    custom_cutouts();
    vent_slots();
}
standoffs();
translate([outer_w + 10, 0, 0]) enclosure_lid();
"""
    
    # Test Arduino Uno preset
    preset_data = PRESETS["ARDUINO_UNO"]
    req = EnclosureRequest(
        pcb=preset_data["pcb"],
        components=preset_data["components"],
        preset="ARDUINO_UNO"
    )
    from app.core.constraint_engine import ConstraintEngine
    constraints = ConstraintEngine.compute(req)
    
    result = await generate_validated_scad(
        llm=MockLLM(),
        constraints=constraints,
        strategy=None,
        job_id="test_inclusion_arduino"
    )
    
    print(f"Success: {result.success}")
    if result.success:
        print(f"Render time: {result.render_time_ms}ms")
    else:
        print(f"Error: {result.error.message}")

if __name__ == "__main__":
    asyncio.run(main())
