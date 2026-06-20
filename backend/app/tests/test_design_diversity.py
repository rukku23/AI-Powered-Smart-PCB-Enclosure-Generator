import pytest
from app.core.strategy_selector import DesignStrategySelector
from app.core.design_context import (
    DesignContext, UseCase, AccessFrequency,
    MountingStyle as MountingEnvironment, Environment as DeploymentEnvironment
)

sel = DesignStrategySelector()

def test_wearable_not_rectangular():
    ctx = DesignContext(use_case=UseCase.WEARABLE)
    s = sel.select(ctx, 0.3, 30, 20, 1)
    assert s.name != "RECTANGULAR_FLAT_LID"
    assert s.name == "WEARABLE_ROUNDED"

def test_din_rail_is_din():
    ctx = DesignContext(mounting=MountingEnvironment.DIN_RAIL)
    s = sel.select(ctx, 3.0, 90, 60, 2)
    assert s.name == "DIN_RAIL_CLIP"

def test_outdoor_is_sealed():
    ctx = DesignContext(environment=DeploymentEnvironment.WET_HUMID)
    s = sel.select(ctx, 1.0, 50, 40, 1)
    assert s.name == "SEALED_OUTDOOR"

def test_frequent_access_is_clamshell():
    ctx = DesignContext(access_frequency=AccessFrequency.DAILY)
    s = sel.select(ctx, 1.0, 60, 40, 1)
    assert s.name == "CLAMSHELL_HINGED"

def test_high_watt_is_chimney():
    ctx = DesignContext()
    s = sel.select(ctx, 9.0, 80, 60, 1)
    assert s.name == "CHIMNEY_THERMAL"

def test_large_pcb_is_ribbed():
    ctx = DesignContext()
    s = sel.select(ctx, 2.0, 120, 90, 1)
    assert s.name == "RECTANGULAR_RIBBED"

def test_bench_prototype_is_flat():
    ctx = DesignContext()  # all defaults = bench prototype
    s = sel.select(ctx, 1.0, 51, 25, 1)
    assert s.name == "RECTANGULAR_FLAT_LID"

def test_same_pcb_different_context_gives_different_strategy():
    ctx_a = DesignContext(use_case=UseCase.BENCH_PROTOTYPE)
    ctx_b = DesignContext(use_case=UseCase.WEARABLE)
    s_a = sel.select(ctx_a, 0.5, 30, 20, 1)
    s_b = sel.select(ctx_b, 0.5, 30, 20, 1)
    assert s_a.name != s_b.name
