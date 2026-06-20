"""
EnclosureAI — DFM Validator Unit Tests
Tests for all 8 DFM compliance checks.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.dfm_validator import validate_dfm_compliance, DFMValidationError
from app.core.constraint_engine import ConstraintEngine
from app.schemas.input_schemas import (
    EnclosureRequest, PCBSpec, ComponentSpec, ComponentType,
    FaceAccess, PrintMaterial, LidStyle,
)


@pytest.fixture
def engine():
    return ConstraintEngine()


class TestWallThickness:
    def test_petg_wall_ok(self, engine):
        c = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), material=PrintMaterial.PETG))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "MIN_WALL_THICKNESS" for x in v)

    def test_abs_wall_ok(self, engine):
        c = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), material=PrintMaterial.ABS))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "MIN_WALL_THICKNESS" for x in v)


class TestSnapFitValidation:
    def test_snap_fit_petg_valid(self, engine):
        c = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), material=PrintMaterial.PETG, lid_style=LidStyle.SNAP_FIT))
        v = validate_dfm_compliance(c)
        assert not any(x.rule.startswith("SNAP_FIT") and x.severity == "ERROR" for x in v)

    def test_no_snap_fit_when_screwed(self, engine):
        c = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), lid_style=LidStyle.SCREWED_M3))
        v = validate_dfm_compliance(c)
        assert not any("SNAP_FIT" in x.rule for x in v)


class TestGlassTransitionTemp:
    def test_8w_pla_warning(self, engine):
        """8W + PLA (Tg=60) -> WARNING"""
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=100, width=80), material=PrintMaterial.PLA,
            components=[ComponentSpec(component_type=ComponentType.HEATSINK, label="IC",
                                     position_x=50, position_y=40, height=5, wattage=8.0)],
        ))
        v = validate_dfm_compliance(c)
        tg = [x for x in v if x.rule == "GLASS_TRANSITION_TEMP"]
        assert len(tg) == 1 and tg[0].severity == "WARNING"

    def test_8w_abs_no_warning(self, engine):
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=100, width=80), material=PrintMaterial.ABS,
            components=[ComponentSpec(component_type=ComponentType.HEATSINK, label="IC",
                                     position_x=50, position_y=40, height=5, wattage=8.0)],
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "GLASS_TRANSITION_TEMP" for x in v)

    def test_3w_pla_no_warning(self, engine):
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=50, width=30), material=PrintMaterial.PLA,
            components=[ComponentSpec(component_type=ComponentType.GENERIC, label="IC",
                                     position_x=25, position_y=15, height=3, wattage=3.0)],
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "GLASS_TRANSITION_TEMP" for x in v)


class TestStandoffWallIntersection:
    def test_normal_board_no_intersection(self, engine):
        c = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30)))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "STANDOFF_WALL_INTERSECTION" for x in v)

    def test_standoff_at_extreme_edge(self, engine):
        """Mounting hole at (0.1, 0.1) on PCB -> standoff OD=6.4, radius=3.2.
           Enc pos = 0.1 + 3.0 + 1.2 = 4.3. 4.3 - 3.2 = 1.1 < wall(1.2) -> ERROR"""
        req = EnclosureRequest(
            pcb=PCBSpec(length=50, width=30, mounting_hole_diameter=3.2,
                        mounting_hole_positions=[(0.1, 0.1)]),
        )
        c = engine.compute(req)
        with pytest.raises(DFMValidationError) as exc:
            validate_dfm_compliance(c)
        assert any(x.rule == "STANDOFF_WALL_INTERSECTION" for x in exc.value.violations)


class TestCutoutBounds:
    def test_normal_cutout_within_bounds(self, engine):
        """Connector in centre of front face — should be within bounds."""
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=60, width=40),
            lid_style=LidStyle.SCREWED_M3,  # avoid snap-fit overlap
            components=[ComponentSpec(
                component_type=ComponentType.CONNECTOR, label="USB",
                position_x=30, position_y=0, height=5,
                face_access=FaceAccess.FRONT, connector_width=9, connector_height=3.5,
            )],
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.rule == "CUTOUT_OUT_OF_BOUNDS" for x in v)


class TestFullPipeline:
    def test_esp32_passes_dfm(self, engine):
        """ESP32 with PETG + screwed lid (avoid snap-fit overlap)."""
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=51, width=25), material=PrintMaterial.PETG,
            preset="ESP32", lid_style=LidStyle.SCREWED_M3,
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.severity == "ERROR" for x in v)

    def test_arduino_passes_dfm(self, engine):
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO",
            lid_style=LidStyle.SCREWED_M3,
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.severity == "ERROR" for x in v)

    def test_rpi4_passes_dfm(self, engine):
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=85, width=56), preset="RPI4",
            lid_style=LidStyle.SCREWED_M3,
        ))
        v = validate_dfm_compliance(c)
        assert not any(x.severity == "ERROR" for x in v)

    def test_dfm_error_raises_exception(self, engine):
        """Standoff at extreme edge -> DFMValidationError."""
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=50, width=30,
                        mounting_hole_positions=[(0.1, 0.1)]),
        ))
        with pytest.raises(DFMValidationError) as exc:
            validate_dfm_compliance(c)
        assert len(exc.value.violations) > 0
        assert any(v.severity == "ERROR" for v in exc.value.violations)

    def test_all_materials_valid(self, engine):
        """All 7 materials should produce valid constraints for a simple board."""
        for mat in PrintMaterial:
            c = engine.compute(EnclosureRequest(
                pcb=PCBSpec(length=50, width=30), material=mat,
                lid_style=LidStyle.SCREWED_M3,
            ))
            v = validate_dfm_compliance(c)
            errors = [x for x in v if x.severity == "ERROR"]
            assert len(errors) == 0, f"{mat.value} produced errors: {errors}"
