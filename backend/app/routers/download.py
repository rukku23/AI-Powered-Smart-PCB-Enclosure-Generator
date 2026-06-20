"""
EnclosureAI — Download Endpoint Router
Handles GET /api/download/{job_id}, /api/preview/{job_id}, /api/thermal/{job_id}.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger("enclosureai.routers.download")

router = APIRouter(prefix="/api", tags=["downloads"])

GENERATED_FILES_DIR = os.getenv("GENERATED_FILES_DIR", "./generated_files")


def _job_dir(job_id: str) -> Path:
    """Get job directory, raising 404 if not found."""
    d = Path(GENERATED_FILES_DIR) / job_id
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return d


@router.get("/download/{job_id}")
async def download_zip(job_id: str):
    """Download generated enclosure ZIP package."""
    job_dir = _job_dir(job_id)

    # Find ZIP file
    zip_name = f"EnclosureAI_{job_id[:8]}.zip"
    zip_path = job_dir / zip_name

    if not zip_path.exists():
        # Try any zip in the directory
        zips = list(job_dir.glob("*.zip"))
        if zips:
            zip_path = zips[0]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"ZIP not found for job {job_id}. Generation may still be in progress.",
            )

    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_path.name}"',
        },
    )


@router.get("/preview/{job_id}/{filename}")
async def preview_stl(job_id: str, filename: str):
    """Serve preview STL for Three.js viewer."""
    job_dir = _job_dir(job_id)

    # Sanitize filename
    allowed = {"body.stl", "lid.stl", "preview_body.stl", "preview_lid.stl"}
    if filename not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {filename}")

    stl_path = job_dir / filename

    # Fallback to non-preview version
    if not stl_path.exists() and filename.startswith("preview_"):
        stl_path = job_dir / filename.replace("preview_", "")

    # Also check enclosure.stl as body.stl alias
    if not stl_path.exists() and filename == "body.stl":
        stl_path = job_dir / "enclosure.stl"

    if not stl_path.exists():
        raise HTTPException(status_code=404, detail=f"STL file not found: {filename}")

    return FileResponse(
        path=str(stl_path),
        media_type="application/octet-stream",
        headers={
            "Content-Type": "application/octet-stream",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/thermal/{job_id}")
async def thermal_report(job_id: str):
    """Return thermal analysis report JSON for UI display."""
    job_dir = _job_dir(job_id)

    report_path = job_dir / "thermal_report.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Thermal report not found for job {job_id}",
        )

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading thermal report: {e}")


@router.get("/bom/{job_id}")
async def bom_data(job_id: str):
    """Return BOM data as JSON for UI display."""
    job_dir = _job_dir(job_id)

    bom_path = job_dir / "bom.json"
    if not bom_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"BOM not found for job {job_id}",
        )

    try:
        data = json.loads(bom_path.read_text(encoding="utf-8"))
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading BOM: {e}")
