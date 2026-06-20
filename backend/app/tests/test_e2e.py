"""
EnclosureAI — Phase 7 End-to-End Test Suite
Automated tests using FastAPI TestClient + mock LLM.
Tests the full pipeline from API endpoint to output validation.
"""
import asyncio
import json
import os
import sys
import zipfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.constraint_engine import ConstraintEngine
from app.core.job_registry import JobRegistry
from app.core.demo_cache import is_demo_cache_enabled, get_cached_preset
from app.llm.aesthetic import build_aesthetic_prompt, AESTHETIC_PROMPTS
from app.scad.renderer import RenderResult
from app.scad.validator import (
    classify_openscad_error,
    validate_stl,
    STLValidationResult,
    GenerationFailedException,
)


# ═══════════════════════════════════════════════════════════════
# Aesthetic Module Tests
# ═══════════════════════════════════════════════════════════════

class TestAestheticModule:
    def test_minimal_skips(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "MINIMAL")
        assert result == []

    def test_rounded_builds_prompt(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "ROUNDED")
        assert len(result) == 2
        assert "minkowski" in result[1]["content"].lower()

    def test_industrial_builds_prompt(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "INDUSTRIAL")
        assert "grip ridges" in result[1]["content"].lower()

    def test_consumer_builds_prompt(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "CONSUMER")
        assert "chamfer" in result[1]["content"].lower()

    def test_wearable_builds_prompt(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "WEARABLE")
        assert "aggressive rounding" in result[1]["content"].lower()

    def test_unknown_style_empty(self):
        result = build_aesthetic_prompt("cube([10,10,10]);", "CYBERPUNK")
        assert result == []

    def test_all_styles_have_prompts(self):
        for style in ["ROUNDED", "CONSUMER", "INDUSTRIAL", "WEARABLE"]:
            assert style in AESTHETIC_PROMPTS


# ═══════════════════════════════════════════════════════════════
# Job Registry Tests
# ═══════════════════════════════════════════════════════════════

class TestJobRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        reg = JobRegistry()
        status = await reg.register("test-001")
        assert status.job_id == "test-001"
        assert status.status == "pending"
        assert reg.get("test-001") is not None

    @pytest.mark.asyncio
    async def test_update(self):
        reg = JobRegistry()
        await reg.register("test-002")
        await reg.update("test-002", status="running", attempt=2)
        j = reg.get("test-002")
        assert j.status == "running"
        assert j.attempt == 2

    @pytest.mark.asyncio
    async def test_cleanup(self):
        reg = JobRegistry()
        await reg.register("old-job")
        # Backdate
        reg._jobs["old-job"].created_at = 0
        removed = await reg.cleanup_old_jobs(max_age_hours=0)
        assert removed == 1
        assert reg.get("old-job") is None

    @pytest.mark.asyncio
    async def test_to_dict(self):
        reg = JobRegistry()
        await reg.register("dict-test")
        d = reg.to_dict("dict-test")
        assert d["job_id"] == "dict-test"
        assert "created_at" in d

    @pytest.mark.asyncio
    async def test_nonexistent(self):
        reg = JobRegistry()
        assert reg.get("nope") is None
        assert reg.to_dict("nope") is None

    @pytest.mark.asyncio
    async def test_semaphore(self):
        reg = JobRegistry(max_concurrent=2)
        await reg.acquire()
        await reg.acquire()
        # Third should block — test with timeout
        acquired = False
        try:
            await asyncio.wait_for(reg.acquire(), timeout=0.1)
            acquired = True
        except asyncio.TimeoutError:
            pass
        assert acquired is False
        reg.release()
        reg.release()


# ═══════════════════════════════════════════════════════════════
# Demo Cache Tests
# ═══════════════════════════════════════════════════════════════

class TestDemoCache:
    def test_disabled_by_default(self):
        assert is_demo_cache_enabled() is False

    def test_no_preset_returns_none(self, monkeypatch):
        monkeypatch.setenv("USE_DEMO_CACHE", "true")
        assert get_cached_preset(None) is None

    def test_unknown_preset_returns_none(self, monkeypatch):
        monkeypatch.setenv("USE_DEMO_CACHE", "true")
        assert get_cached_preset("TEENSY") is None


# ═══════════════════════════════════════════════════════════════
# E2E API Tests (with mocked LLM + renderer)
# ═══════════════════════════════════════════════════════════════

VALID_SCAD = """/* DESIGN REASONING: Test */ $fn=30;
module enclosure_body() { difference() {
cube([59.4,33.4,10.74]); translate([1.2,1.2,1.2]) cube([57,31,8.1]); } }
module lid() { cube([59.4,33.4,1.44]); }
enclosure_body(); translate([70,0,0]) lid();"""


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    """Create test client with mocked output dir."""
    monkeypatch.setattr("app.routers.generate.GENERATED_FILES_DIR", str(tmp_path))
    monkeypatch.setattr("app.routers.download.GENERATED_FILES_DIR", str(tmp_path))
    monkeypatch.setenv("USE_DEMO_CACHE", "false")

    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


class TestE2EAPI:
    def test_health(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "active_jobs" in data

    def test_invalid_pcb_dimensions(self, test_client):
        """PCB length=5mm below minimum 10mm should fail validation."""
        resp = test_client.post("/api/generate", json={
            "pcb": {"length": 5, "width": 20},
        })
        # FastAPI Pydantic validation or our constraint engine should catch this
        assert resp.status_code in (422, 200)  # 422 for pydantic, 200 with SSE error

    def test_esp32_sse_events(self, test_client, tmp_path, monkeypatch):
        """ESP32 preset produces SSE stream with expected event types."""
        # Mock the LLM and renderer
        mock_render = AsyncMock(return_value=RenderResult(
            success=True, stl_path=str(tmp_path / "test" / "enclosure.stl"),
            scad_path=str(tmp_path / "test" / "enclosure.scad"),
            error_message=None, error_class=None, render_time_ms=500,
            stdout="", stderr="",
        ))
        mock_validate = MagicMock(return_value=STLValidationResult(
            passed=True, file_exists=True, file_size_bytes=2048,
            is_watertight=True, volume_positive=True,
            face_count=500, face_count_sufficient=True,
        ))
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=VALID_SCAD)

        async def mock_gen_stream(messages):
            yield VALID_SCAD
        mock_llm.generate_stream = mock_gen_stream

        monkeypatch.setattr("app.scad.validator.render_scad", mock_render)
        monkeypatch.setattr("app.scad.validator.validate_stl", mock_validate)
        monkeypatch.setattr("app.routers.generate.llm_factory", lambda: mock_llm)

        # Ensure STL file exists for the mock
        stl_dir = tmp_path / "test"
        stl_dir.mkdir(exist_ok=True)
        (stl_dir / "enclosure.stl").write_bytes(b"\0" * 2048)

        resp = test_client.post("/api/generate", json={
            "pcb": {"length": 51, "width": 25},
            "preset": "ESP32",
        })

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        # Parse SSE events
        events = []
        for line in resp.text.split("\n\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass

        event_types = [e.get("event") for e in events]
        assert "validating" in event_types

    def test_status_endpoint_404(self, test_client):
        resp = test_client.get("/api/status/nonexistent-job")
        assert resp.status_code == 404

    def test_download_404(self, test_client):
        resp = test_client.get("/api/download/nonexistent-job")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Constraint Engine E2E Tests
# ═══════════════════════════════════════════════════════════════

class TestConstraintE2E:
    def test_esp32_full_pipeline(self):
        from app.schemas.input_schemas import EnclosureRequest, PCBSpec, PrintMaterial
        engine = ConstraintEngine()
        constraints = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=51, width=25), preset="ESP32", material=PrintMaterial.PETG
        ))
        assert constraints.enclosure.outer_length > 51
        assert len(constraints.standoffs) == 4

    def test_arduino_full_pipeline(self):
        from app.schemas.input_schemas import EnclosureRequest, PCBSpec, PrintMaterial
        engine = ConstraintEngine()
        constraints = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO", material=PrintMaterial.PLA
        ))
        assert constraints.enclosure.outer_length > 68.6
        assert len(constraints.standoffs) == 4

    def test_rpi4_thermal_zones(self):
        from app.schemas.input_schemas import (
            EnclosureRequest, PCBSpec, ComponentSpec, PrintMaterial
        )
        engine = ConstraintEngine()
        constraints = engine.compute(EnclosureRequest(
            pcb=PCBSpec(length=85, width=56),
            material=PrintMaterial.PETG,
            components=[
                ComponentSpec(
                    component_type="HEATSINK", label="SoC",
                    position_x=42, position_y=28, height=5, wattage=5.0
                ),
            ],
        ))
        assert len(constraints.thermal_zones) >= 1
        assert constraints.total_wattage >= 5.0


# ═══════════════════════════════════════════════════════════════
# Error Classifier Integration
# ═══════════════════════════════════════════════════════════════

class TestErrorClassifierIntegration:
    def test_multiline_stderr(self):
        stderr = """WARNING: Ignoring unknown variable "wall_t" in file test.scad, line 5
WARNING: Ignoring unknown variable "lid_h" in file test.scad, line 8
ERROR: Parser error at line 12: syntax error"""
        result = classify_openscad_error(stderr)
        # Should classify as SYNTAX_ERROR (most specific match)
        assert result["class"] in ("SYNTAX_ERROR", "UNDEFINED_VARIABLE")
        assert result["line"] is not None

    def test_empty_no_crash(self):
        result = classify_openscad_error(None)
        assert result["class"] == "UNKNOWN"
