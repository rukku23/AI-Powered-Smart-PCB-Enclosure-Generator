"""
EnclosureAI — Phase 3 Integration Tests
Tests for OpenSCAD renderer, error classifier, STL validator, and self-correction loop.
Uses mock LLM for deterministic testing without API keys.
"""
import asyncio
import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.scad.renderer import RenderResult
from app.scad.validator import (
    classify_openscad_error,
    validate_stl,
    generate_validated_scad,
    GenerationResult,
    GenerationFailedException,
    STLValidationResult,
)
from app.llm.interface import LLMInterface
from app.core.constraint_engine import ConstraintEngine
from app.schemas.input_schemas import EnclosureRequest, PCBSpec, PrintMaterial, LidStyle


# ═══════════════════════════════════════════════════════════════
# Error Classifier Tests
# ═══════════════════════════════════════════════════════════════

class TestClassifyOpenscadError:
    def test_syntax_error(self):
        stderr = "ERROR: Parser error at line 15: syntax error, unexpected ';'"
        result = classify_openscad_error(stderr)
        assert result["class"] == "SYNTAX_ERROR"
        assert result["line"] == 15

    def test_undefined_variable(self):
        stderr = 'WARNING: Ignoring unknown variable "wall_thicknes" at line 8'
        result = classify_openscad_error(stderr)
        assert result["class"] == "UNDEFINED_VARIABLE"
        assert result["line"] == 8

    def test_module_not_found(self):
        stderr = "ERROR: Requested module 'enclosuer_body' not found"
        result = classify_openscad_error(stderr)
        assert result["class"] == "MODULE_NOT_FOUND"

    def test_empty_geometry(self):
        stderr = "WARNING: Normalized tree is empty"
        result = classify_openscad_error(stderr)
        assert result["class"] == "EMPTY_GEOMETRY"

    def test_boolean_failure(self):
        stderr = "WARNING: Object may not be a valid 2-manifold and may need repair"
        result = classify_openscad_error(stderr)
        assert result["class"] == "BOOLEAN_FAILURE"

    def test_timeout(self):
        result = classify_openscad_error("TIMEOUT")
        assert result["class"] == "TIMEOUT"

    def test_unknown(self):
        result = classify_openscad_error("Some random OpenSCAD output text")
        assert result["class"] == "UNKNOWN"

    def test_empty_stderr(self):
        result = classify_openscad_error("")
        assert result["class"] == "UNKNOWN"

    def test_has_interpretation(self):
        """All classes produce human-readable interpretations."""
        for stderr in [
            "ERROR: Parser error syntax error",
            'WARNING: Ignoring unknown variable "x"',
            "WARNING: Normalized tree is empty",
            "ERROR: Requested module 'foo' not found",
            "WARNING: Object may not be a valid 2-manifold",
            "TIMEOUT",
            "random",
        ]:
            result = classify_openscad_error(stderr)
            assert len(result["interpretation"]) > 10


# ═══════════════════════════════════════════════════════════════
# STL Validator Tests
# ═══════════════════════════════════════════════════════════════

class TestValidateStl:
    def test_nonexistent_file(self):
        result = validate_stl("/nonexistent/path/file.stl")
        assert result.passed is False
        assert result.file_exists is False

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.stl"
        f.write_bytes(b"")
        result = validate_stl(str(f))
        assert result.passed is False
        assert result.file_size_bytes == 0

    def test_tiny_file(self, tmp_path):
        f = tmp_path / "tiny.stl"
        f.write_bytes(b"x" * 500)
        result = validate_stl(str(f))
        assert result.passed is False
        assert "too small" in result.errors[0] if result.errors else True


# ═══════════════════════════════════════════════════════════════
# Mock LLM for self-correction loop tests
# ═══════════════════════════════════════════════════════════════

VALID_SCAD = """/* === ENCLOSUREAI DESIGN REASONING ===
GEOMETRY: Test box
FEATURES: None
THERMAL: None
MATERIAL: PLA
======================================= */
$fn = 30;
outer_length = 59.4;
outer_width = 33.4;
outer_height = 10.74;
wall = 1.2;

module enclosure_body() {
    difference() {
        cube([outer_length, outer_width, outer_height]);
        translate([wall, wall, wall])
            cube([outer_length - 2*wall, outer_width - 2*wall, outer_height]);
    }
}

module lid() {
    cube([outer_length, outer_width, 1.44]);
}

enclosure_body();
translate([outer_length + 10, 0, 0]) lid();
"""

INVALID_SCAD = """$fn = 30;
cube([10, 10, 10)  // syntax error: mismatched brackets
"""


class MockLLMSuccess(LLMInterface):
    """Always returns valid SCAD on first call."""
    async def generate(self, messages):
        return VALID_SCAD

    async def generate_stream(self, messages):
        for chunk in [VALID_SCAD[:50], VALID_SCAD[50:]]:
            yield chunk


class MockLLMFixOnRetry(LLMInterface):
    """Returns invalid SCAD first, valid on second call."""
    def __init__(self):
        self._call_count = 0

    async def generate(self, messages):
        self._call_count += 1
        if self._call_count == 1:
            return INVALID_SCAD
        return VALID_SCAD

    async def generate_stream(self, messages):
        self._call_count += 1
        code = INVALID_SCAD if self._call_count == 1 else VALID_SCAD
        yield code


class MockLLMAlwaysFails(LLMInterface):
    """Always returns invalid SCAD."""
    async def generate(self, messages):
        return INVALID_SCAD

    async def generate_stream(self, messages):
        yield INVALID_SCAD


# ═══════════════════════════════════════════════════════════════
# Self-Correction Loop Tests (with mocked renderer)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def constraints():
    engine = ConstraintEngine()
    return engine.compute(EnclosureRequest(
        pcb=PCBSpec(length=51, width=25),
        preset="ESP32",
        material=PrintMaterial.PETG,
    ))


class TestSelfCorrectionLoop:
    """Test the retry loop logic with mocked OpenSCAD renderer."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, constraints, tmp_path, monkeypatch):
        """Mock renderer returns success — loop should complete in 1 attempt."""
        fake_stl = tmp_path / "test_job" / "enclosure.stl"
        fake_stl.parent.mkdir(parents=True, exist_ok=True)
        # Write a valid-ish STL header (84 byte header + triangle count)
        fake_stl.write_bytes(b"\0" * 80 + b"\x01\x00\x00\x00" + b"\0" * 50 * 1)

        mock_render = AsyncMock(return_value=RenderResult(
            success=True, stl_path=str(fake_stl), scad_path=str(tmp_path / "test_job" / "enclosure.scad"),
            error_message=None, error_class=None, render_time_ms=500, stdout="", stderr="",
        ))
        mock_validate = MagicMock(return_value=STLValidationResult(
            passed=True, file_exists=True, file_size_bytes=2048,
            is_watertight=True, volume_positive=True, face_count=500,
            face_count_sufficient=True,
        ))

        monkeypatch.setattr("app.scad.validator.render_scad", mock_render)
        monkeypatch.setattr("app.scad.validator.validate_stl", mock_validate)

        result = await generate_validated_scad(
            constraints=constraints,
            llm=MockLLMSuccess(),
            job_id="test_job",
            output_dir=str(tmp_path),
        )

        assert isinstance(result, GenerationResult)
        assert result.attempts == 1
        assert "DESIGN REASONING" in result.reasoning or result.reasoning != ""
        mock_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_render_failure(self, constraints, tmp_path, monkeypatch):
        """Mock renderer fails first, succeeds second — verify retry fires."""
        fake_stl = tmp_path / "test_job" / "enclosure.stl"
        fake_stl.parent.mkdir(parents=True, exist_ok=True)
        fake_stl.write_bytes(b"\0" * 2048)

        call_count = {"n": 0}

        async def mock_render_fn(scad_code, job_id, output_dir):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return RenderResult(
                    success=False, stl_path=None, scad_path="test.scad",
                    error_message="ERROR: Parser error at line 3: syntax error",
                    error_class=None, render_time_ms=100, stdout="", stderr="ERROR: Parser error",
                )
            return RenderResult(
                success=True, stl_path=str(fake_stl), scad_path="test.scad",
                error_message=None, error_class=None, render_time_ms=300, stdout="", stderr="",
            )

        mock_validate = MagicMock(return_value=STLValidationResult(
            passed=True, file_exists=True, file_size_bytes=2048,
            is_watertight=True, volume_positive=True, face_count=500,
            face_count_sufficient=True,
        ))

        monkeypatch.setattr("app.scad.validator.render_scad", mock_render_fn)
        monkeypatch.setattr("app.scad.validator.validate_stl", mock_validate)

        result = await generate_validated_scad(
            constraints=constraints,
            llm=MockLLMFixOnRetry(),
            job_id="test_job",
            output_dir=str(tmp_path),
        )

        assert result.attempts == 2
        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self, constraints, tmp_path, monkeypatch):
        """Mock renderer always fails — should raise after 3 attempts."""
        async def mock_render_fail(scad_code, job_id, output_dir):
            return RenderResult(
                success=False, stl_path=None, scad_path="test.scad",
                error_message="ERROR: Parser error: syntax error",
                error_class=None, render_time_ms=50, stdout="",
                stderr="ERROR: Parser error: syntax error",
            )

        monkeypatch.setattr("app.scad.validator.render_scad", mock_render_fail)

        with pytest.raises(GenerationFailedException) as exc_info:
            await generate_validated_scad(
                constraints=constraints,
                llm=MockLLMAlwaysFails(),
                job_id="test_job",
                output_dir=str(tmp_path),
            )

        assert exc_info.value.attempts == 3

    @pytest.mark.asyncio
    async def test_sse_events_emitted(self, constraints, tmp_path, monkeypatch):
        """With SSE queue, verify events are emitted."""
        fake_stl = tmp_path / "test_job" / "enclosure.stl"
        fake_stl.parent.mkdir(parents=True, exist_ok=True)
        fake_stl.write_bytes(b"\0" * 2048)

        mock_render = AsyncMock(return_value=RenderResult(
            success=True, stl_path=str(fake_stl), scad_path="test.scad",
            error_message=None, error_class=None, render_time_ms=200, stdout="", stderr="",
        ))
        mock_validate = MagicMock(return_value=STLValidationResult(
            passed=True, file_exists=True, file_size_bytes=2048,
            is_watertight=True, volume_positive=True, face_count=500,
            face_count_sufficient=True,
        ))

        monkeypatch.setattr("app.scad.validator.render_scad", mock_render)
        monkeypatch.setattr("app.scad.validator.validate_stl", mock_validate)

        queue = asyncio.Queue()
        result = await generate_validated_scad(
            constraints=constraints,
            llm=MockLLMSuccess(),
            job_id="test_job",
            output_dir=str(tmp_path),
            sse_queue=queue,
        )

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        event_types = [e["event"] for e in events]
        assert "generating" in event_types
        assert "rendering" in event_types


# ═══════════════════════════════════════════════════════════════
# Renderer Tests (without OpenSCAD — tests file I/O)
# ═══════════════════════════════════════════════════════════════

class TestRendererFileIO:
    @pytest.mark.asyncio
    async def test_scad_file_written(self, tmp_path):
        """render_scad writes the .scad file even when CLI not found."""
        from app.scad.renderer import render_scad
        result = await render_scad(VALID_SCAD, "io_test", str(tmp_path))
        scad_file = Path(result.scad_path)
        assert scad_file.exists()
        assert VALID_SCAD in scad_file.read_text()

    @pytest.mark.asyncio
    async def test_cli_not_found_returns_error(self, tmp_path, monkeypatch):
        """If openscad binary doesn't exist, return CLI_NOT_FOUND."""
        monkeypatch.setattr("app.scad.renderer.OPENSCAD_CLI", "/nonexistent/openscad")
        from app.scad.renderer import render_scad
        result = await render_scad(VALID_SCAD, "cli_test", str(tmp_path))
        assert result.success is False
        assert result.error_class == "CLI_NOT_FOUND"
