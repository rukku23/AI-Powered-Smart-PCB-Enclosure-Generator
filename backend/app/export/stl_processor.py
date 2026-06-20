"""
EnclosureAI — STL Post-Processor
Preview decimation and mesh metadata extraction.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("enclosureai.export.stl")

STL_PREVIEW_MAX_TRIANGLES = 50000


def create_preview_stl(
    full_stl_path: str,
    preview_stl_path: str,
    max_triangles: int = STL_PREVIEW_MAX_TRIANGLES,
) -> str:
    """
    Create a decimated preview STL for the Three.js viewer.
    If face count <= max_triangles, copies as-is.
    Returns preview_stl_path.
    """
    try:
        import trimesh

        mesh = trimesh.load(full_stl_path, force="mesh")
        face_count = len(mesh.faces)

        if face_count > max_triangles:
            logger.info(
                f"Decimating STL: {face_count} → {max_triangles} faces"
            )
            mesh = mesh.simplify_quadric_decimation(max_triangles)
            logger.info(f"Decimated to {len(mesh.faces)} faces")

        mesh.export(preview_stl_path, file_type="stl")
        logger.info(f"Preview STL saved: {preview_stl_path}")
        return preview_stl_path

    except ImportError:
        # No trimesh — just copy the file
        logger.warning("trimesh not installed — copying full STL as preview")
        import shutil
        shutil.copy2(full_stl_path, preview_stl_path)
        return preview_stl_path


def get_stl_metadata(stl_path: str) -> dict:
    """
    Extract mesh metadata from an STL file.

    Returns:
        {
            "volume_cm3": float,
            "bounding_box_mm": [x, y, z],
            "face_count": int,
            "is_watertight": bool,
        }
    """
    try:
        import trimesh

        mesh = trimesh.load(stl_path, force="mesh")
        extents = mesh.bounding_box.extents.tolist()

        return {
            "volume_cm3": round(float(mesh.volume) / 1000.0, 4) if mesh.is_watertight else 0.0,
            "bounding_box_mm": [round(e, 2) for e in extents],
            "face_count": int(len(mesh.faces)),
            "is_watertight": bool(mesh.is_watertight),
        }

    except ImportError:
        logger.warning("trimesh not installed — returning empty metadata")
        file_size = Path(stl_path).stat().st_size if Path(stl_path).exists() else 0
        return {
            "volume_cm3": 0.0,
            "bounding_box_mm": [0.0, 0.0, 0.0],
            "face_count": 0,
            "is_watertight": False,
        }
    except Exception as e:
        logger.error(f"Failed to read STL metadata: {e}")
        return {
            "volume_cm3": 0.0,
            "bounding_box_mm": [0.0, 0.0, 0.0],
            "face_count": 0,
            "is_watertight": False,
        }
