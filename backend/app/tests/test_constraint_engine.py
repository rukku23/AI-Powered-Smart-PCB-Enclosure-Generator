"""
EnclosureAI — Constraint Engine Unit Tests
Comprehensive tests for all geometric computation functions.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.constraint_engine import ConstraintEngine
from app.schemas.input_schemas import (
    EnclosureRequest, PCBSpec, ComponentSpec, ComponentType,
    FaceAccess, PrintMaterial, LidStyle, PrintTechnology, PRESETS,
)


@pytest.fixture
def engine():
    return ConstraintEngine()


class TestESP32Preset:
    """ESP32 DevKit V1: 51x25mm, PETG, snap-fit."""

    def test_outer_dimensions(self, engine):
        """PETG wall=1.2, clearance=3.0 => outer = 51+8.4=59.4 x 25+8.4=33.4"""
        req = EnclosureRequest(
            pcb=PCBSpec(length=51, width=25),
            material=PrintMaterial.PETG, preset="ESP32",
        )
        r = engine.compute(req)
        # 51 + 2*3.0 + 2*1.2 = 59.4
        assert r.enclosure.outer_length == 59.4
        assert r.enclosure.outer_width == 33.4

    def test_wall_thickness_petg(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), material=PrintMaterial.PETG, preset="ESP32")
        r = engine.compute(req)
        assert r.enclosure.wall == 1.2

    def test_standoff_count(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32")
        r = engine.compute(req)
        assert len(r.standoffs) == 4

    def test_standoffs_within_bounds(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32")
        r = engine.compute(req)
        w = r.enclosure.wall
        for s in r.standoffs:
            assert s.x > w and s.y > w
            assert s.x < r.enclosure.outer_length - w
            assert s.y < r.enclosure.outer_width - w

    def test_usb_c_cutout(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32")
        r = engine.compute(req)
        front = [c for c in r.cutouts if c.face == "FRONT"]
        assert len(front) >= 1
        assert front[0].label == "USB-C"
        assert front[0].component_type == "CONNECTOR"

    def test_snap_fit_generated(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32", lid_style=LidStyle.SNAP_FIT)
        r = engine.compute(req)
        assert r.snap_fit is not None and r.snap_fit.tab_count >= 4

    def test_thermal_zones_for_regulator(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32")
        r = engine.compute(req)
        assert len(r.thermal_zones) >= 1
        assert r.thermal_zones[0].priority == 1.5

    def test_total_wattage(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=51, width=25), preset="ESP32")
        r = engine.compute(req)
        assert abs(r.total_wattage - 1.8) < 0.01


class TestArduinoUno:
    def test_outer_dimensions_pla(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=68.6, width=53.4), material=PrintMaterial.PLA, preset="ARDUINO_UNO")
        r = engine.compute(req)
        assert abs(r.enclosure.outer_length - (68.6 + 8.4)) < 0.01
        assert abs(r.enclosure.outer_width - (53.4 + 8.4)) < 0.01

    def test_standoff_count(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO")
        r = engine.compute(req)
        assert len(r.standoffs) == 4

    def test_usb_b_on_back(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO")
        r = engine.compute(req)
        back = [c for c in r.cutouts if c.face == "BACK"]
        assert len(back) >= 1 and back[0].label == "USB-B"

    def test_barrel_jack_on_left(self, engine):
        req = EnclosureRequest(pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO")
        r = engine.compute(req)
        left = [c for c in r.cutouts if c.face == "LEFT"]
        assert len(left) >= 1 and left[0].label == "Barrel Jack"


class TestEdgeCases:
    def test_min_size_board(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=10, width=10)))
        assert r.enclosure.outer_length > 10 and len(r.standoffs) == 4

    def test_max_size_board(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=500, width=500)))
        assert abs(r.enclosure.outer_length - (500 + 8.4)) < 0.01

    def test_zero_components(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), components=[]))
        assert r.max_component_height == 15.0
        assert r.total_wattage == 0.0 and len(r.cutouts) == 0

    def test_connector_on_left_face(self, engine):
        req = EnclosureRequest(
            pcb=PCBSpec(length=60, width=40),
            components=[ComponentSpec(
                component_type=ComponentType.CONNECTOR, label="Side Port",
                position_x=0, position_y=20, height=5,
                face_access=FaceAccess.LEFT, connector_width=8, connector_height=5,
            )],
        )
        r = engine.compute(req)
        assert len(r.cutouts) == 1 and r.cutouts[0].face == "LEFT"

    def test_no_snap_fit_when_screwed(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), lid_style=LidStyle.SCREWED_M3))
        assert r.snap_fit is None

    def test_abs_wall_thickness(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), material=PrintMaterial.ABS))
        assert r.enclosure.wall == 1.5

    def test_pc_wall_thickness(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30), material=PrintMaterial.PC))
        assert r.enclosure.wall == 1.8

    def test_thermal_zones_sorted(self, engine):
        req = EnclosureRequest(
            pcb=PCBSpec(length=100, width=80),
            components=[
                ComponentSpec(component_type=ComponentType.HEATSINK, label="IC1",
                              position_x=30, position_y=40, height=5, wattage=5.0),
                ComponentSpec(component_type=ComponentType.GENERIC, label="IC2",
                              position_x=70, position_y=40, height=3, wattage=3.0),
            ],
        )
        r = engine.compute(req)
        assert len(r.thermal_zones) == 2
        assert r.thermal_zones[0].priority == 5.0
        assert r.total_wattage == 8.0

    def test_below_thermal_threshold(self, engine):
        req = EnclosureRequest(
            pcb=PCBSpec(length=50, width=30),
            components=[ComponentSpec(
                component_type=ComponentType.GENERIC, label="LED",
                position_x=25, position_y=15, height=2, wattage=0.5,
            )],
        )
        r = engine.compute(req)
        assert len(r.thermal_zones) == 0

    def test_auto_generated_standoffs(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30, mounting_hole_positions=None)))
        assert len(r.standoffs) == 4

    def test_custom_mounting_holes(self, engine):
        r = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=50, width=30, mounting_hole_positions=[(5, 5), (45, 5), (5, 25)]),
        ))
        assert len(r.standoffs) == 3

    def test_m2_fastener(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30, mounting_hole_diameter=2.5)))
        assert r.standoffs[0].fastener_type == "M2" and r.standoffs[0].height == 4.0

    def test_m3_fastener(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30, mounting_hole_diameter=3.2)))
        assert r.standoffs[0].fastener_type == "M3" and r.standoffs[0].height == 5.0


class TestSnapFitDistribution:
    def test_minimum_tab_count(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=20, width=15), lid_style=LidStyle.SNAP_FIT))
        assert r.snap_fit is not None and r.snap_fit.tab_count >= 4

    def test_large_enclosure_more_tabs(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=200, width=150), lid_style=LidStyle.SNAP_FIT))
        assert r.snap_fit is not None and r.snap_fit.tab_count > 4

    def test_valid_faces(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=80, width=50), lid_style=LidStyle.SNAP_FIT))
        for pos in r.snap_fit.positions:
            assert pos["face"] in {"FRONT", "BACK", "LEFT", "RIGHT"}
            assert pos["offset_from_start"] >= 0


class TestDimensionConsistency:
    def test_inner_length(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30)))
        assert abs(r.enclosure.inner_length - (r.enclosure.outer_length - 2 * r.enclosure.wall)) < 0.01

    def test_inner_width(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30)))
        assert abs(r.enclosure.inner_width - (r.enclosure.outer_width - 2 * r.enclosure.wall)) < 0.01

    def test_inner_height(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30)))
        expected = r.enclosure.outer_height - r.enclosure.wall - r.enclosure.lid_thickness
        assert abs(r.enclosure.inner_height - expected) < 0.01

    def test_lid_thickness_ratio(self, engine):
        r = engine.compute(EnclosureRequest(pcb=PCBSpec(length=50, width=30)))
        assert r.enclosure.lid_thickness == round(r.enclosure.wall * 1.2, 2)
