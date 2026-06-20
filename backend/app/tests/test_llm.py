"""
EnclosureAI — Phase 2 Unit Tests
Tests for LLM interface, response parser, prompt builder, few-shot library.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.llm.response_parser import (
    extract_scad_code, extract_reasoning_block,
    build_correction_prompt, parse_thermal_response,
    ResponseParseError,
)
from app.llm.prompt_builder import (
    build_generation_prompt, build_thermal_prompt,
    token_count_estimate, OLLAMA_TOKEN_LIMIT,
)
from app.llm.few_shot_library import get_few_shot_examples
from app.llm.interface import llm_factory
from app.core.constraint_engine import ConstraintEngine
from app.schemas.input_schemas import (
    EnclosureRequest, PCBSpec, PrintMaterial, LidStyle,
)


# ═══════════════════════════════════════════════════════════════
# extract_scad_code tests (5 test cases per spec)
# ═══════════════════════════════════════════════════════════════

class TestExtractScadCode:
    def test_plain_scad(self):
        code = "// comment\ncube([10, 10, 10]);"
        assert extract_scad_code(code) == code.strip()

    def test_strip_openscad_fence(self):
        raw = "```openscad\ncube([10,10,10]);\n```"
        assert "cube([10,10,10]);" in extract_scad_code(raw)
        assert "```" not in extract_scad_code(raw)

    def test_strip_scad_fence(self):
        raw = "```scad\n$fn=30;\ncube([5,5,5]);\n```"
        result = extract_scad_code(raw)
        assert "$fn=30;" in result
        assert "```" not in result

    def test_strip_generic_fence(self):
        raw = "```\nmodule box() { cube([1,1,1]); }\n```"
        result = extract_scad_code(raw)
        assert "module box()" in result

    def test_prose_raises_error(self):
        with pytest.raises(ResponseParseError):
            extract_scad_code("Here is how to create a box in OpenSCAD...")

    def test_empty_raises_error(self):
        with pytest.raises(ResponseParseError):
            extract_scad_code("")

    def test_comment_start_valid(self):
        code = "/* Design */\ncube([1,1,1]);"
        assert "Design" in extract_scad_code(code)

    def test_variable_start_valid(self):
        code = "$fn = 30;\ncube([1,1,1]);"
        assert extract_scad_code(code) == code.strip()


# ═══════════════════════════════════════════════════════════════
# extract_reasoning_block tests
# ═══════════════════════════════════════════════════════════════

class TestExtractReasoning:
    def test_extracts_reasoning(self):
        scad = """/* === ENCLOSUREAI DESIGN REASONING ===
GEOMETRY: Outer 59.4 x 33.4mm
FEATURES: 4x M3 standoffs
THERMAL: 1.5W passive
MATERIAL: PETG 1.2mm wall
======================================= */
$fn = 30;
cube([59.4, 33.4, 10.74]);"""
        result = extract_reasoning_block(scad)
        assert "GEOMETRY" in result
        assert "THERMAL" in result

    def test_no_reasoning_returns_empty(self):
        scad = "$fn = 30;\ncube([10,10,10]);"
        assert extract_reasoning_block(scad) == ""

    def test_fallback_block_comment(self):
        scad = "/* My design notes */\ncube([1,1,1]);"
        result = extract_reasoning_block(scad)
        assert "design notes" in result


# ═══════════════════════════════════════════════════════════════
# build_correction_prompt tests
# ═══════════════════════════════════════════════════════════════

class TestCorrectionPrompt:
    def test_contains_error(self):
        result = build_correction_prompt("cube();", "syntax error line 5", 1)
        assert result["role"] == "user"
        assert "syntax error line 5" in result["content"]
        assert "attempt 1" in result["content"]

    def test_contains_original(self):
        result = build_correction_prompt("cube();", "err", 2)
        assert "cube();" in result["content"]


# ═══════════════════════════════════════════════════════════════
# parse_thermal_response tests
# ═══════════════════════════════════════════════════════════════

class TestParseThermalResponse:
    def test_valid_json(self):
        resp = '{"thermal_health_score": 85, "verdict": "GOOD", "passive_cooling_sufficient": true}'
        result = parse_thermal_response(resp)
        assert result["thermal_health_score"] == 85
        assert result["verdict"] == "GOOD"

    def test_json_in_fences(self):
        resp = '```json\n{"thermal_health_score": 72}\n```'
        result = parse_thermal_response(resp)
        assert result["thermal_health_score"] == 72

    def test_malformed_returns_defaults(self):
        result = parse_thermal_response("not json at all")
        assert result["thermal_health_score"] == 0
        assert result["verdict"] == "UNKNOWN"

    def test_clamps_score(self):
        result = parse_thermal_response('{"thermal_health_score": 150}')
        assert result["thermal_health_score"] == 100

    def test_json_with_extra_text(self):
        resp = 'Here is the analysis: {"thermal_health_score": 60, "verdict": "MARGINAL"} done.'
        result = parse_thermal_response(resp)
        assert result["thermal_health_score"] == 60


# ═══════════════════════════════════════════════════════════════
# Few-Shot Library tests
# ═══════════════════════════════════════════════════════════════

class TestFewShotLibrary:
    def test_3_examples(self):
        text = get_few_shot_examples(3)
        assert "EXAMPLE 1" in text
        assert "EXAMPLE 2" in text
        assert "EXAMPLE 3" in text

    def test_1_example(self):
        text = get_few_shot_examples(1)
        assert "EXAMPLE 1" in text
        assert "EXAMPLE 2" not in text

    def test_examples_contain_scad(self):
        text = get_few_shot_examples(3)
        assert "module enclosure_body()" in text
        assert "module lid()" in text

    def test_examples_contain_json(self):
        text = get_few_shot_examples(3)
        assert '"outer_length"' in text
        assert '"standoffs"' in text


# ═══════════════════════════════════════════════════════════════
# Prompt Builder tests
# ═══════════════════════════════════════════════════════════════

class TestPromptBuilder:
    @pytest.fixture
    def constraints(self):
        engine = ConstraintEngine()
        req = EnclosureRequest(
            pcb=PCBSpec(length=51, width=25),
            preset="ESP32", material=PrintMaterial.PETG,
        )
        return engine.compute(req)

    def test_builds_system_and_user(self, constraints):
        msgs = build_generation_prompt(constraints)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_system_has_rules(self, constraints):
        msgs = build_generation_prompt(constraints)
        system = msgs[0]["content"]
        assert "STRICT OUTPUT RULES" in system
        assert "OpenSCAD" in system

    def test_user_has_json(self, constraints):
        msgs = build_generation_prompt(constraints)
        user = msgs[1]["content"]
        assert '"outer_length"' in user
        assert "59.4" in user

    def test_has_few_shot(self, constraints):
        msgs = build_generation_prompt(constraints)
        assert "FEW-SHOT EXAMPLE" in msgs[0]["content"]

    def test_token_estimate(self):
        assert token_count_estimate("a" * 400) == 100
        assert token_count_estimate("") == 0


class TestThermalPrompt:
    def test_builds_messages(self):
        engine = ConstraintEngine()
        c = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=51, width=25), preset="ESP32",
        ))
        msgs = build_thermal_prompt(c)
        assert len(msgs) == 2
        assert "thermal" in msgs[0]["content"].lower()
        assert '"outer_length"' in msgs[1]["content"]


# ═══════════════════════════════════════════════════════════════
# LLM Factory tests
# ═══════════════════════════════════════════════════════════════

class TestLLMFactory:
    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError):
            llm_factory("invalid_provider")

    def test_ollama_instantiates(self):
        client = llm_factory("ollama")
        assert client is not None
        from app.llm.ollama_client import OllamaClient
        assert isinstance(client, OllamaClient)

    def test_claude_requires_key(self):
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                llm_factory("claude")
        finally:
            if old:
                os.environ["ANTHROPIC_API_KEY"] = old
