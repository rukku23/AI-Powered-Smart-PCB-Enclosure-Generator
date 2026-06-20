import pytest
from app.core.thermal_engine import compute_thermal

def test_zero_watt_board():
    result = compute_thermal(
        components=[], pcb_length=51, pcb_width=25,
        enclosure_length=63, enclosure_width=37, ventilation_enabled=True
    )
    assert result.total_wattage == 0.0
    assert result.slot_count == 4          # minimum aesthetic vents
    assert result.thermal_health_score > 60  # 0W board should score well

def test_low_watt_board():
    result = compute_thermal(
        components=[{"label": "ESP32", "wattage": 0.5, "position_x": 25, "position_y": 12}],
        pcb_length=51, pcb_width=25, enclosure_length=63, enclosure_width=37,
        ventilation_enabled=True
    )
    assert result.total_wattage == 0.5
    assert result.slot_count == 36          # 0.5W needs ~36 slots with 20% margin
    assert result.thermal_health_score >= 70

def test_medium_watt_board():
    result = compute_thermal(
        components=[
            {"label": "Regulator", "wattage": 3.0, "position_x": 30, "position_y": 12},
            {"label": "MCU",       "wattage": 0.5, "position_x": 10, "position_y": 12},
        ],
        pcb_length=51, pcb_width=25, enclosure_length=63, enclosure_width=37,
        ventilation_enabled=True
    )
    assert result.total_wattage == 3.5
    # 3.5W / (10 * 45) = 0.00778 m² needed
    # Each slot = 0.0025 * 0.015 = 0.0000375 m²
    # min slots = ceil(0.00778 / 0.0000375 * 1.2) = ceil(249) ≈ but capped differently
    assert result.slot_count > 4       # more slots than 0W board
    assert result.vent_face_primary == "TOP"   # hotspot in middle

def test_high_watt_board_triggers_chimney():
    result = compute_thermal(
        components=[
            {"label": "MOSFET_1", "wattage": 5.0, "position_x": 40, "position_y": 20},
            {"label": "MOSFET_2", "wattage": 4.0, "position_x": 50, "position_y": 20},
        ],
        pcb_length=80, pcb_width=60, enclosure_length=92, enclosure_width=72,
        ventilation_enabled=True
    )
    assert result.total_wattage == 9.0
    assert result.openscad_chimney_needed == True
    assert result.openscad_chimney_height >= 15.0
    assert result.thermal_health_score < 70   # 9W passive = marginal/poor

def test_hotspot_on_left_edge_gives_left_vents():
    result = compute_thermal(
        components=[{"label": "Hot_chip", "wattage": 2.0, "position_x": 5, "position_y": 25}],
        pcb_length=80, pcb_width=50, enclosure_length=92, enclosure_width=62,
        ventilation_enabled=True
    )
    # position_x=5 on an 80mm board = 6.25% from left edge < 20%
    assert result.vent_face_primary == "LEFT"
    assert result.vent_face_intake  == "RIGHT"

def test_no_ventilation_no_slots():
    result = compute_thermal(
        components=[{"label": "Sensor", "wattage": 0.1, "position_x": 25, "position_y": 12}],
        pcb_length=50, pcb_width=30, enclosure_length=62, enclosure_width=42,
        ventilation_enabled=False
    )
    assert result.slot_count == 0

def test_slot_count_changes_with_wattage():
    low  = compute_thermal([{"label":"c","wattage":0.5,"position_x":25,"position_y":12}],
                            51, 25, 63, 37, True)
    high = compute_thermal([{"label":"c","wattage":8.0,"position_x":25,"position_y":12}],
                            51, 25, 63, 37, True)
    # High wattage must produce more slots than low wattage
    assert high.slot_count > low.slot_count, (
        f"slot_count should increase with wattage: "
        f"low={low.slot_count} high={high.slot_count}"
    )

def test_score_decreases_with_more_heat():
    low  = compute_thermal([{"label":"c","wattage":0.5,"position_x":25,"position_y":12}],
                            51, 25, 63, 37, True)
    high = compute_thermal([{"label":"c","wattage":12.0,"position_x":25,"position_y":12}],
                            51, 25, 63, 37, True)
    assert high.thermal_health_score < low.thermal_health_score
