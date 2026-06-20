"""
EnclosureAI — Phase 4 Unit Tests
Tests for STL processor, BOM generator, ZIP packager, STEP exporter, and download endpoints.
"""
import json
import math
import os
import sys
import zipfile
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.export.stl_processor import create_preview_stl, get_stl_metadata
from app.export.step_exporter import export_step, STEPExportError
from app.export.zip_packager import create_download_zip
from app.core.bom_generator import generate_bom, bom_to_csv
from app.core.constraint_engine import ConstraintEngine
from app.schemas.input_schemas import (
    EnclosureRequest, PCBSpec, PrintMaterial, LidStyle,
)


@pytest.fixture
def esp32_constraints():
    engine = ConstraintEngine()
    return engine.compute(EnclosureRequest(
        pcb=PCBSpec(length=51, width=25), preset="ESP32",
        material=PrintMaterial.PETG, lid_style=LidStyle.SCREWED_M3,
    ))


@pytest.fixture
def arduino_constraints():
    engine = ConstraintEngine()
    return engine.compute(EnclosureRequest(
        pcb=PCBSpec(length=68.6, width=53.4), preset="ARDUINO_UNO",
        material=PrintMaterial.PLA, lid_style=LidStyle.SNAP_FIT,
    ))


# ═══════════════════════════════════════════════════════════════
# STL Processor Tests
# ═══════════════════════════════════════════════════════════════

class TestSTLProcessor:
    def test_get_metadata_nonexistent(self):
        result = get_stl_metadata("/nonexistent/file.stl")
        assert result["face_count"] == 0
        assert result["volume_cm3"] == 0.0

    def test_create_preview_copies_when_no_trimesh(self, tmp_path):
        """Without trimesh, just copies the file."""
        src = tmp_path / "full.stl"
        src.write_bytes(b"fake stl data " * 100)
        dst = tmp_path / "preview.stl"
        result = create_preview_stl(str(src), str(dst))
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0


# ═══════════════════════════════════════════════════════════════
# STEP Exporter Tests
# ═══════════════════════════════════════════════════════════════

class TestSTEPExporter:
    def test_step_export_no_cadquery(self, esp32_constraints, tmp_path):
        """Without CadQuery installed, should raise STEPExportError."""
        output = str(tmp_path / "test.step")
        try:
            import cadquery
            # CadQuery IS installed — test actual export
            result = export_step(esp32_constraints, output)
            assert Path(result).exists()
        except ImportError:
            with pytest.raises(STEPExportError, match="CadQuery not installed"):
                export_step(esp32_constraints, output)

    def test_step_error_is_noncritical(self):
        """STEPExportError is a regular exception, not a system crash."""
        e = STEPExportError("test error")
        assert str(e) == "test error"
        assert isinstance(e, Exception)


# ═══════════════════════════════════════════════════════════════
# BOM Generator Tests
# ═══════════════════════════════════════════════════════════════

class TestBOMGenerator:
    def test_bom_structure(self, esp32_constraints, tmp_path):
        """BOM has correct top-level keys."""
        # Create a fake STL
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))

        assert "filament" in bom
        assert "fasteners" in bom
        assert "print_settings" in bom

    def test_filament_fields(self, esp32_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))

        fil = bom["filament"]
        assert fil["material"] == "PETG"
        assert fil["volume_cm3"] > 0
        assert fil["weight_g"] > 0
        assert fil["length_m"] > 0

    def test_density_petg(self, esp32_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))
        vol = bom["filament"]["volume_cm3"]
        weight = bom["filament"]["weight_g"]
        # PETG density = 1.27
        assert abs(weight - vol * 1.27) < 0.1

    def test_fasteners_screwed_m3(self, esp32_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))

        # SCREWED_M3: standoffs + screws + heat-set inserts
        assert len(bom["fasteners"]) == 3
        descs = [f["description"] for f in bom["fasteners"]]
        assert any("standoff" in d for d in descs)
        assert any("screw" in d for d in descs)
        assert any("heat-set" in d for d in descs)

    def test_fasteners_snap_fit(self, arduino_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(arduino_constraints, str(stl))

        # SNAP_FIT: standoffs only (no screws)
        assert len(bom["fasteners"]) == 1
        assert "standoff" in bom["fasteners"][0]["description"]

    def test_print_settings(self, esp32_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))

        ps = bom["print_settings"]
        assert ps["recommended_layer_height"] == 0.25  # PETG
        assert ps["infill_percent"] == 20
        assert ps["supports_required"] is False
        assert ps["estimated_print_hours"] > 0

    def test_bom_to_csv(self, esp32_constraints, tmp_path):
        stl = tmp_path / "test.stl"
        stl.write_bytes(b"\0" * 2048)
        bom = generate_bom(esp32_constraints, str(stl))
        csv_str = bom_to_csv(bom)

        assert "Category,Item,Value,Unit" in csv_str
        assert "Filament" in csv_str
        assert "PETG" in csv_str
        assert "Fastener" in csv_str
        assert "Print" in csv_str

    def test_filament_length_formula(self):
        """Verify filament length formula: L = V / (π * r² * 100)"""
        vol_cm3 = 10.0
        r_cm = 0.175 / 2
        expected = vol_cm3 / (math.pi * r_cm ** 2 * 100)
        assert abs(expected - 4.16) < 0.1  # ~4.16m for 10cm³


# ═══════════════════════════════════════════════════════════════
# ZIP Packager Tests
# ═══════════════════════════════════════════════════════════════

class TestZIPPackager:
    def test_creates_zip(self, tmp_path):
        """ZIP file is created with correct name."""
        job_id = "test-job-1234-5678"
        files_dir = tmp_path / "files"
        files_dir.mkdir()

        # Create test files
        scad = files_dir / "enclosure.scad"
        scad.write_text("$fn=30; cube([10,10,10]);")

        stl = files_dir / "body.stl"
        stl.write_bytes(b"\0" * 2048)

        result = create_download_zip(
            job_id=job_id,
            files={"scad": str(scad), "body_stl": str(stl)},
            output_dir=str(tmp_path),
        )

        assert Path(result).exists()
        assert "EnclosureAI_test-job" in result

    def test_zip_contains_manifest(self, tmp_path):
        job_id = "manifest-test-1234"
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")

        result = create_download_zip(
            job_id=job_id,
            files={"scad": str(scad)},
            output_dir=str(tmp_path),
        )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "enclosure.scad" in names

            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["job_id"] == job_id
            assert "generated_at" in manifest
            assert "checksums" in manifest
            assert "enclosure.scad" in manifest["checksums"]

    def test_skips_none_files(self, tmp_path):
        """None values in files dict are silently skipped."""
        job_id = "skip-test-1234"
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")

        result = create_download_zip(
            job_id=job_id,
            files={
                "scad": str(scad),
                "step": None,
                "body_stl": None,
            },
            output_dir=str(tmp_path),
        )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "enclosure.scad" in names
            assert "enclosure.step" not in names
            assert "body.stl" not in names

    def test_sha256_checksums(self, tmp_path):
        job_id = "checksum-test"
        scad = tmp_path / "test.scad"
        scad.write_text("cube([5,5,5]);")

        result = create_download_zip(
            job_id=job_id,
            files={"scad": str(scad)},
            output_dir=str(tmp_path),
        )

        with zipfile.ZipFile(result, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert len(manifest["checksums"]["enclosure.scad"]) == 64  # SHA-256 hex


# ═══════════════════════════════════════════════════════════════
# Download Router Tests (via TestClient)
# ═══════════════════════════════════════════════════════════════

class TestDownloadRouter:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routers.download.GENERATED_FILES_DIR", str(tmp_path))
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_404_nonexistent_job(self, client):
        resp = client.get("/api/download/nonexistent-job-id")
        assert resp.status_code == 404

    def test_download_zip(self, client, tmp_path):
        job_id = "dl-test-12345678"
        job_dir = tmp_path / job_id
        job_dir.mkdir()
        zip_path = job_dir / f"EnclosureAI_{job_id[:8]}.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("test.txt", "hello")

        resp = client.get(f"/api/download/{job_id}")
        assert resp.status_code == 200
        assert "application/zip" in resp.headers.get("content-type", "")

    def test_preview_stl_404(self, client, tmp_path):
        job_id = "preview-test"
        (tmp_path / job_id).mkdir()
        resp = client.get(f"/api/preview/{job_id}/body.stl")
        assert resp.status_code == 404

    def test_preview_invalid_filename(self, client, tmp_path):
        job_id = "bad-file-test"
        (tmp_path / job_id).mkdir()
        resp = client.get(f"/api/preview/{job_id}/malicious.exe")
        assert resp.status_code == 400

    def test_thermal_404(self, client, tmp_path):
        job_id = "thermal-test"
        (tmp_path / job_id).mkdir()
        resp = client.get(f"/api/thermal/{job_id}")
        assert resp.status_code == 404

    def test_thermal_report(self, client, tmp_path):
        job_id = "thermal-ok"
        job_dir = tmp_path / job_id
        job_dir.mkdir()
        report = {"thermal_health_score": 85, "verdict": "GOOD"}
        (job_dir / "thermal_report.json").write_text(json.dumps(report))

        resp = client.get(f"/api/thermal/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["thermal_health_score"] == 85
