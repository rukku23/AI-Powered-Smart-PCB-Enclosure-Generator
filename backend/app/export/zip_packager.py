"""
EnclosureAI — ZIP Packager
Creates download ZIP with all generated files + manifest.
"""
from __future__ import annotations

import hashlib
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("enclosureai.export.zip")


def _sha256(filepath: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


FILE_DESCRIPTIONS = {
    "body.stl": "3D-printable enclosure body (binary STL)",
    "lid.stl": "3D-printable enclosure lid (binary STL)",
    "enclosure.scad": "OpenSCAD source code (editable parametric model)",
    "enclosure.step": "STEP CAD file (for Fusion 360, SolidWorks, FreeCAD)",
    "thermal_report.json": "Thermal analysis report with health score",
    "bom.csv": "Bill of Materials with filament and fastener estimates",
    "ai_reasoning.txt": "AI design reasoning and decision log",
}


def create_download_zip(
    job_id: str,
    files: dict[str, str | None],
    output_dir: str,
) -> str:
    """
    Create a ZIP package with all generated files + manifest.

    Args:
        job_id: Unique job identifier
        files: Dict mapping archive names to filesystem paths.
               Keys: "body_stl", "lid_stl", "scad", "step",
                     "thermal_report", "bom_csv", "reasoning_txt"
               Values: file paths (None if not available)
        output_dir: Directory to write the ZIP

    Returns: Path to the created ZIP file.
    """
    job_dir = Path(output_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"EnclosureAI_{job_id[:8]}.zip"
    zip_path = job_dir / zip_name

    # Map dict keys to archive filenames
    key_to_filename = {
        "body_stl": "body.stl",
        "lid_stl": "lid.stl",
        "scad": "enclosure.scad",
        "step": "enclosure.step",
        "thermal_report": "thermal_report.json",
        "bom_csv": "bom.csv",
        "reasoning_txt": "ai_reasoning.txt",
    }

    manifest_files = []
    checksums = {}

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for key, archive_name in key_to_filename.items():
            filepath = files.get(key)

            if filepath is None:
                continue

            p = Path(filepath)
            if not p.exists():
                logger.warning(f"File not found, skipping: {filepath}")
                continue

            # Add to ZIP
            zf.write(str(p), archive_name)

            # Track metadata
            size = p.stat().st_size
            manifest_files.append({
                "name": archive_name,
                "description": FILE_DESCRIPTIONS.get(archive_name, ""),
                "size_bytes": size,
            })
            checksums[archive_name] = _sha256(str(p))

            logger.info(f"  Added: {archive_name} ({size} bytes)")

        # Add manifest
        manifest = {
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest_files,
            "checksums": checksums,
        }
        manifest_json = json.dumps(manifest, indent=2)
        zf.writestr("manifest.json", manifest_json)

    logger.info(f"ZIP created: {zip_path} ({len(manifest_files)} files)")
    return str(zip_path)
