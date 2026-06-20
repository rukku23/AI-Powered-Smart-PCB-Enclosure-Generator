"""
EnclosureAI — Topology Diversity Test Suite (Phase 8)

Tests:
  1. Strategy selector produces correct strategy for hard overrides
  2. Strategy selector scoring picks correct strategy for soft conditions
  3. Topology constraint extensions add correct keys per strategy
  4. Strategy-aware prompt includes topology directive + correct few-shot
  5. Two identical PCBs with different contexts produce different strategies
  6. Diversity score across test suite >= 0.85
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from app.core.design_context import (
    DesignContext,
    UseCase,
    AccessFrequency,
    MountingStyle,
    Environment,
)
from app.core.strategy_selector import DesignStrategySelector
from app.core.strategy_library import STRATEGY_LIBRARY, get_strategy
from app.core.topology_constraints import apply_topology_extensions
from app.llm.strategy_aware_prompt import build_strategy_prompt
from app.llm.few_shot_library import get_topology_few_shot, FEW_SHOT_LIBRARY
from app.schemas.constraint_schemas import (
    ConstraintSchema,
    EnclosureDimensions,
    StandoffSpec,
)
from app.schemas.input_schemas import PCBSpec


# ═══════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════

def _make_constraints(total_wattage=2.0) -> ConstraintSchema:
    """Create a minimal valid ConstraintSchema for testing."""
    return ConstraintSchema(
        pcb=PCBSpec(length=50.0, width=30.0, thickness=1.6, mounting_hole_diameter=3.2),
        enclosure=EnclosureDimensions(
            outer_length=58.4, outer_width=38.4, outer_height=14.0,
            wall=1.2, clearance=3.0, lid_thickness=1.44,
            inner_length=56.0, inner_width=36.0, inner_height=11.36,
        ),
        standoffs=[
            StandoffSpec(x=10, y=10, inner_diameter=3.2, outer_diameter=6.4,
                         height=5.0, fastener_type="M3"),
            StandoffSpec(x=48, y=10, inner_diameter=3.2, outer_diameter=6.4,
                         height=5.0, fastener_type="M3"),
        ],
        cutouts=[],
        thermal_zones=[],
        snap_fit=None,
        vent_spec=None,
        material="PETG",
        print_technology="FDM",
        lid_style="SNAP_FIT",
        total_wattage=total_wattage,
        max_component_height=5.0,
        ventilation_enabled=True,
    )


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 1: Strategy Library Completeness
# ═══════════════════════════════════════════════════════════════

class TestStrategyLibrary:
    def test_all_12_strategies_defined(self):
        """All 12 strategies must be defined in STRATEGY_LIBRARY."""
        expected = [
            "RECTANGULAR_FLAT_LID", "RECTANGULAR_RIBBED_LID",
            "CLAMSHELL_HORIZONTAL", "CLAMSHELL_VERTICAL",
            "INDUSTRIAL_FLANGED", "DIN_RAIL_CLIP",
            "WEARABLE_ROUNDED", "CHIMNEY_THERMAL",
            "THREE_PIECE_ACCESS", "PANEL_MOUNT_BEZEL",
            "SEALED_IP_RATED", "SNAP_RAIL_MODULAR",
        ]
        for name in expected:
            assert name in STRATEGY_LIBRARY, f"Strategy {name} not found"

    def test_all_strategies_have_score_fn(self):
        """Every strategy must have a score function."""
        for name, strategy in STRATEGY_LIBRARY.items():
            assert strategy.score_fn is not None, f"{name} has no score_fn"

    def test_get_strategy_raises_for_unknown(self):
        with pytest.raises(KeyError):
            get_strategy("NONEXISTENT_STRATEGY")


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 2: Hard Override Strategy Selection
# ═══════════════════════════════════════════════════════════════

class TestStrategyHardOverrides:
    def setup_method(self):
        self.selector = DesignStrategySelector()
        self.constraints = _make_constraints()

    def test_din_rail_override(self):
        """DIN rail mounting → DIN_RAIL_CLIP."""
        ctx = DesignContext(mounting=MountingStyle.DIN_RAIL)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "DIN_RAIL_CLIP"

    def test_wearable_mounting_override(self):
        """Wearable mounting → WEARABLE_ROUNDED."""
        ctx = DesignContext(mounting=MountingStyle.WEARABLE)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "WEARABLE_ROUNDED"

    def test_wearable_usecase_override(self):
        """Wearable use case → WEARABLE_ROUNDED."""
        ctx = DesignContext(use_case=UseCase.WEARABLE)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "WEARABLE_ROUNDED"

    def test_outdoor_override(self):
        """Outdoor environment → SEALED_IP_RATED."""
        ctx = DesignContext(environment=Environment.OUTDOOR)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "SEALED_IP_RATED"

    def test_wet_humid_override(self):
        """Wet/humid environment → SEALED_IP_RATED."""
        ctx = DesignContext(environment=Environment.WET_HUMID)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "SEALED_IP_RATED"

    def test_panel_cutout_override(self):
        """Panel cutout mounting → PANEL_MOUNT_BEZEL."""
        ctx = DesignContext(mounting=MountingStyle.PANEL_CUTOUT)
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "PANEL_MOUNT_BEZEL"

    def test_high_wattage_override(self):
        """Total wattage > 8W → CHIMNEY_THERMAL."""
        ctx = DesignContext()
        constraints = _make_constraints(total_wattage=9.0)
        result = self.selector.select(ctx, constraints)
        assert result.strategy.topology_name == "CHIMNEY_THERMAL"


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 3: Scoring-Based Selection
# ═══════════════════════════════════════════════════════════════

class TestStrategyScoringSelection:
    def setup_method(self):
        self.selector = DesignStrategySelector()
        self.constraints = _make_constraints()

    def test_bench_prototype_default(self):
        """Default context → RECTANGULAR_FLAT_LID."""
        ctx = DesignContext()
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "RECTANGULAR_FLAT_LID"

    def test_frequent_access_consumer(self):
        """Daily access + consumer → CLAMSHELL_HORIZONTAL."""
        ctx = DesignContext(
            access_frequency=AccessFrequency.DAILY,
            use_case=UseCase.CONSUMER_PRODUCT,
        )
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "CLAMSHELL_HORIZONTAL"

    def test_weekly_access_iot(self):
        """Weekly access + IoT → CLAMSHELL_HORIZONTAL (frequent access wins)."""
        ctx = DesignContext(
            access_frequency=AccessFrequency.WEEKLY,
            use_case=UseCase.IOT_DEVICE,
        )
        result = self.selector.select(ctx, self.constraints)
        assert result.strategy.topology_name == "CLAMSHELL_HORIZONTAL"


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 4: Topology Constraint Extensions
# ═══════════════════════════════════════════════════════════════

class TestTopologyConstraintExtensions:
    def test_clamshell_extensions(self):
        """CLAMSHELL_HORIZONTAL adds all required keys."""
        constraints = _make_constraints()
        strategy = get_strategy("CLAMSHELL_HORIZONTAL")
        result = apply_topology_extensions(strategy, constraints)
        required_keys = [
            "half_height", "hinge_x", "hinge_z",
            "latch_x", "latch_y",
            "pcb_groove_z", "pcb_groove_depth", "pcb_groove_width",
        ]
        for key in required_keys:
            assert key in result.topology_extensions, f"Missing key: {key}"

    def test_din_rail_fixed_values(self):
        """DIN_RAIL_CLIP uses fixed IEC 60715 standard values."""
        constraints = _make_constraints()
        strategy = get_strategy("DIN_RAIL_CLIP")
        result = apply_topology_extensions(strategy, constraints)
        assert result.topology_extensions["din_rail_width"] == 35.0
        assert result.topology_extensions["din_clip_engagement_depth"] == 5.5
        assert result.topology_extensions["din_clip_spring_length"] == 14.0
        assert result.topology_extensions["din_clip_release_tab_height"] == 8.0

    def test_chimney_thermal_extensions(self):
        """CHIMNEY_THERMAL adds chimney dimensions."""
        constraints = _make_constraints(total_wattage=10.0)
        strategy = get_strategy("CHIMNEY_THERMAL")
        result = apply_topology_extensions(strategy, constraints)
        required_keys = [
            "chimney_x", "chimney_y", "chimney_width",
            "chimney_length", "chimney_height",
            "intake_slot_z", "intake_face",
        ]
        for key in required_keys:
            assert key in result.topology_extensions, f"Missing key: {key}"

    def test_wearable_extensions(self):
        """WEARABLE_ROUNDED adds corner radius and band lug dims."""
        constraints = _make_constraints()
        strategy = get_strategy("WEARABLE_ROUNDED")
        result = apply_topology_extensions(strategy, constraints)
        required_keys = ["corner_radius", "edge_fillet", "band_lug_width", "band_lug_height"]
        for key in required_keys:
            assert key in result.topology_extensions, f"Missing key: {key}"

    def test_sealed_ip_extensions(self):
        """SEALED_IP_RATED adds O-ring and cable gland dims."""
        constraints = _make_constraints()
        strategy = get_strategy("SEALED_IP_RATED")
        result = apply_topology_extensions(strategy, constraints)
        required_keys = [
            "oring_cross_section", "oring_groove_width", "oring_groove_depth",
            "cable_gland_od", "lid_flange_width", "screw_count",
        ]
        for key in required_keys:
            assert key in result.topology_extensions, f"Missing key: {key}"

    def test_rectangular_no_extensions(self):
        """RECTANGULAR_FLAT_LID adds no topology extensions."""
        constraints = _make_constraints()
        strategy = get_strategy("RECTANGULAR_FLAT_LID")
        result = apply_topology_extensions(strategy, constraints)
        assert len(result.topology_extensions) == 0

    def test_strategy_name_set(self):
        """Strategy name is set on the constraints after extension."""
        constraints = _make_constraints()
        strategy = get_strategy("CHIMNEY_THERMAL")
        result = apply_topology_extensions(strategy, constraints)
        assert result.strategy_name == "CHIMNEY_THERMAL"


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 5: Strategy-Aware Prompt
# ═══════════════════════════════════════════════════════════════

class TestStrategyAwarePrompt:
    def test_prompt_contains_topology_directive(self):
        """Prompt must contain TOPOLOGY DIRECTIVE block."""
        constraints = _make_constraints()
        strategy = get_strategy("CLAMSHELL_HORIZONTAL")
        apply_topology_extensions(strategy, constraints)
        messages = build_strategy_prompt(constraints, strategy)
        system = messages[0]["content"]
        assert "TOPOLOGY DIRECTIVE" in system
        assert "CLAMSHELL_HORIZONTAL" in system

    def test_prompt_contains_correct_few_shot(self):
        """Prompt includes few-shot for the correct topology only."""
        constraints = _make_constraints()
        strategy = get_strategy("DIN_RAIL_CLIP")
        apply_topology_extensions(strategy, constraints)
        messages = build_strategy_prompt(constraints, strategy)
        system = messages[0]["content"]
        assert "DIN Rail" in system or "din_rail" in system.lower()

    def test_prompt_excludes_other_topology_examples(self):
        """Prompt must NOT include examples from other topologies."""
        constraints = _make_constraints()
        strategy = get_strategy("WEARABLE_ROUNDED")
        apply_topology_extensions(strategy, constraints)
        messages = build_strategy_prompt(constraints, strategy)
        system = messages[0]["content"]
        # Should not contain clamshell or chimney keywords in few-shot
        assert "clamshell_lower_shell" not in system
        assert "chimney_stack" not in system

    def test_prompt_has_constraint_json(self):
        """User message includes constraint JSON."""
        constraints = _make_constraints()
        strategy = get_strategy("RECTANGULAR_FLAT_LID")
        messages = build_strategy_prompt(constraints, strategy)
        user = messages[1]["content"]
        assert "outer_length" in user
        assert "58.4" in user

    def test_prompt_no_generic_instruction(self):
        """System must NOT contain generic 'write an enclosure' instruction."""
        constraints = _make_constraints()
        strategy = get_strategy("CHIMNEY_THERMAL")
        apply_topology_extensions(strategy, constraints)
        messages = build_strategy_prompt(constraints, strategy)
        system = messages[0]["content"]
        assert "write an enclosure" not in system.lower()


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 6: Topology Diversity
# ═══════════════════════════════════════════════════════════════

class TestTopologyDiversity:
    """Test that different contexts produce different strategies."""

    def setup_method(self):
        self.selector = DesignStrategySelector()

    def test_same_pcb_different_contexts_different_strategies(self):
        """Two identical PCBs with different design contexts → different strategies."""
        constraints = _make_constraints()

        ctx1 = DesignContext()  # bench prototype
        ctx2 = DesignContext(
            access_frequency=AccessFrequency.DAILY,
            use_case=UseCase.CONSUMER_PRODUCT,
        )

        r1 = self.selector.select(ctx1, constraints)
        r2 = self.selector.select(ctx2, constraints)

        assert r1.strategy.topology_name != r2.strategy.topology_name, (
            f"Same strategy for different contexts: {r1.strategy.topology_name}"
        )

    def test_diversity_score(self):
        """Diversity score across test suite >= 0.85."""
        test_contexts = [
            DesignContext(),
            DesignContext(mounting=MountingStyle.DIN_RAIL),
            DesignContext(use_case=UseCase.WEARABLE),
            DesignContext(environment=Environment.OUTDOOR),
            DesignContext(access_frequency=AccessFrequency.DAILY,
                          use_case=UseCase.CONSUMER_PRODUCT),
            DesignContext(mounting=MountingStyle.PANEL_CUTOUT),
        ]
        high_wattage = _make_constraints(total_wattage=10.0)

        strategies = set()
        constraints = _make_constraints()

        for ctx in test_contexts:
            c = high_wattage if ctx == test_contexts[0] and False else constraints
            result = self.selector.select(ctx, c)
            strategies.add(result.strategy.topology_name)

        # Also test high wattage
        result_thermal = self.selector.select(DesignContext(), high_wattage)
        strategies.add(result_thermal.strategy.topology_name)

        # Diversity = unique strategies / total tests
        diversity = len(strategies) / (len(test_contexts) + 1)
        assert diversity >= 0.85, (
            f"Diversity score {diversity:.2f} < 0.85. "
            f"Strategies: {strategies}"
        )

    def test_six_diversity_cases(self):
        """All 6 key test cases from the spec."""
        selector = self.selector
        constraints = _make_constraints()

        # Case 1: WEARABLE → WEARABLE_ROUNDED
        r = selector.select(
            DesignContext(use_case=UseCase.WEARABLE), constraints)
        assert r.strategy.topology_name == "WEARABLE_ROUNDED"

        # Case 2: DIN_RAIL → DIN_RAIL_CLIP
        r = selector.select(
            DesignContext(mounting=MountingStyle.DIN_RAIL), constraints)
        assert r.strategy.topology_name == "DIN_RAIL_CLIP"

        # Case 3: >8W → CHIMNEY_THERMAL
        high_w = _make_constraints(total_wattage=9.0)
        r = selector.select(DesignContext(), high_w)
        assert r.strategy.topology_name == "CHIMNEY_THERMAL"

        # Case 4: Frequent access → CLAMSHELL_HORIZONTAL
        r = selector.select(
            DesignContext(access_frequency=AccessFrequency.DAILY,
                          use_case=UseCase.CONSUMER_PRODUCT), constraints)
        assert r.strategy.topology_name == "CLAMSHELL_HORIZONTAL"

        # Case 5: Generic bench → RECTANGULAR_FLAT_LID
        r = selector.select(DesignContext(), constraints)
        assert r.strategy.topology_name == "RECTANGULAR_FLAT_LID"

        # Case 6: Same PCB, different contexts → different strategies
        r1 = selector.select(DesignContext(), constraints)
        r2 = selector.select(
            DesignContext(mounting=MountingStyle.DIN_RAIL), constraints)
        assert r1.strategy.topology_name != r2.strategy.topology_name


# ═══════════════════════════════════════════════════════════════
# P8-10 Test 7: Few-Shot Library Coverage
# ═══════════════════════════════════════════════════════════════

class TestFewShotLibrary:
    def test_all_strategies_have_examples(self):
        """Every strategy in STRATEGY_LIBRARY has few-shot examples."""
        for name in STRATEGY_LIBRARY:
            assert name in FEW_SHOT_LIBRARY, f"No few-shot for {name}"
            assert len(FEW_SHOT_LIBRARY[name]) > 0, f"Empty few-shot for {name}"

    def test_clamshell_example_uses_modules(self):
        """CLAMSHELL few-shot uses module assembly, not from-scratch."""
        examples = FEW_SHOT_LIBRARY["CLAMSHELL_HORIZONTAL"]
        scad = examples[0][2]
        assert "use <" in scad, "Clamshell example must use module imports"
        assert "clamshell_lower_shell" in scad

    def test_chimney_example_contains_chimney(self):
        """CHIMNEY few-shot mentions chimney."""
        examples = FEW_SHOT_LIBRARY["CHIMNEY_THERMAL"]
        scad = examples[0][2]
        assert "chimney" in scad.lower()

    def test_din_rail_example_contains_35(self):
        """DIN_RAIL few-shot contains 35.0 (DIN standard)."""
        examples = FEW_SHOT_LIBRARY["DIN_RAIL_CLIP"]
        scad = examples[0][2]
        assert "35.0" in scad
