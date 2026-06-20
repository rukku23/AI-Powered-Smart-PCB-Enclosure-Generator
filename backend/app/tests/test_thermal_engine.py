"""
EnclosureAI — Thermal Engine Unit Tests
Tests for Newton's Law calculations, health scoring, and slot counts.
"""
import pytest
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.thermal_engine import (
    compute_required_vent_area,
    compute_implemented_vent_area,
    compute_thermal_health_score,
    determine_slot_count,
    compute_vent_spec,
)
from app.core.constants import (
    NATURAL_CONVECTION_H, FORCED_CONVECTION_H, DELTA_T,
    VENT_SLOT_WIDTH, VENT_SLOT_LENGTH, VENT_SLOT_SPACING,
)
from app.schemas.constraint_schemas import EnclosureDimensions, ThermalZone


def _dims(ol=100, ow=60):
    return EnclosureDimensions(
        outer_length=ol, outer_width=ow, outer_height=25,
        wall=1.2, clearance=3.0, lid_thickness=1.44,
        inner_length=ol - 2.4, inner_width=ow - 2.4, inner_height=22.36,
    )


def _zone(w=5.0):
    return ThermalZone(
        centre_x=50, centre_y=30, radius=20, face="TOP",
        priority=w, required_vent_area=w / 450,
    )


class TestRequiredVentArea:
    def test_zero_wattage(self):
        assert compute_required_vent_area(0.0) == 0.0

    def test_negative_wattage(self):
        assert compute_required_vent_area(-1.0) == 0.0

    def test_5w_natural(self):
        r = compute_required_vent_area(5.0, forced=False)
        assert abs(r - 5.0 / 450.0) < 1e-6

    def test_5w_forced(self):
        r = compute_required_vent_area(5.0, forced=True)
        assert abs(r - 5.0 / 1125.0) < 1e-6

    def test_1w_natural(self):
        r = compute_required_vent_area(1.0)
        assert abs(r - 1.0 / 450.0) < 1e-6

    def test_forced_less_area(self):
        for q in [1, 5, 10, 20]:
            assert compute_required_vent_area(q, True) < compute_required_vent_area(q, False)


class TestImplementedVentArea:
    def test_single_slot(self):
        r = compute_implemented_vent_area(2.5, 15.0, 1)
        assert abs(r - 0.0000375) < 1e-8

    def test_ten_slots(self):
        r = compute_implemented_vent_area(2.5, 15.0, 10)
        assert abs(r - 0.000375) < 1e-8

    def test_zero_slots(self):
        assert compute_implemented_vent_area(2.5, 15.0, 0) == 0.0


class TestThermalHealthScore:
    def test_zero_wattage_perfect(self):
        r = compute_thermal_health_score(0, 0, True, 0)
        assert r["score"] == 100 and "EXCELLENT" in r["verdict"]

    def test_excellent(self):
        req = compute_required_vent_area(5.0)
        r = compute_thermal_health_score(5, req * 1.2, True, 8)
        assert r["score"] >= 85 and "EXCELLENT" in r["verdict"]

    def test_good(self):
        req = compute_required_vent_area(5.0)
        r = compute_thermal_health_score(5, req, True, 15)
        assert 70 <= r["score"] < 85 and "GOOD" in r["verdict"]

    def test_marginal(self):
        req = compute_required_vent_area(5.0)
        r = compute_thermal_health_score(5, req * 0.8, False, 30)
        assert r["score"] < 70

    def test_poor(self):
        req = compute_required_vent_area(10.0)
        r = compute_thermal_health_score(10, req * 0.3, False, 50)
        assert r["score"] < 50 and "POOR" in r["verdict"]

    def test_clamped_100(self):
        r = compute_thermal_health_score(1, 1.0, True, 5)
        assert r["score"] <= 100

    def test_proximity_tiers(self):
        req = compute_required_vent_area(5.0)
        s1 = compute_thermal_health_score(5, req, True, 8)["score"]
        s2 = compute_thermal_health_score(5, req, True, 20)["score"]
        s3 = compute_thermal_health_score(5, req, True, 40)["score"]
        assert s1 > s2 > s3


class TestSlotCount:
    def test_no_zones(self):
        assert determine_slot_count(_dims(), []) == 0

    def test_1w_zone(self):
        c = determine_slot_count(_dims(), [_zone(1)])
        assert 0 < c < 20

    def test_5w_more_than_1w(self):
        # Use very large enclosure so space cap doesn't limit either
        big = _dims(ol=1000, ow=500)
        c1 = determine_slot_count(big, [_zone(1)])
        c5 = determine_slot_count(big, [_zone(5)])
        assert c5 > c1

    def test_capped_by_space(self):
        d = _dims(ol=30, ow=20)
        c = determine_slot_count(d, [_zone(20)])
        avail = d.outer_length - 20
        mx = max(0, math.floor(avail / (VENT_SLOT_WIDTH + VENT_SLOT_SPACING)))
        assert c <= mx


class TestVentSpec:
    def test_none_without_zones(self):
        assert compute_vent_spec(_dims(), []) is None

    def test_returns_spec(self):
        r = compute_vent_spec(_dims(), [_zone(5)])
        assert r is not None and r.slot_count > 0 and r.total_area_m2 > 0
