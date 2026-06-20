"""
EnclosureAI — BOM Generator
Generates Bill of Materials from ConstraintSchema and STL volume data.
"""
from __future__ import annotations

import csv
import io
import logging
import math
from pathlib import Path

from app.core.constants import MATERIAL_DENSITY, DFM_RULES
from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.core.bom")


def generate_bom(constraints: ConstraintSchema, stl_path: str) -> dict:
    """
    Generate Bill of Materials from constraints and STL mesh volume.

    Returns dict with filament, fasteners, and print_settings.
    """
    material = constraints.material

    # ── Get volume from STL ──
    volume_cm3 = 0.0
    try:
        import trimesh
        mesh = trimesh.load(stl_path, force="mesh")
        if mesh.is_watertight:
            volume_cm3 = float(mesh.volume) / 1000.0  # mm³ → cm³
        else:
            # Estimate from bounding box with ~15% fill for hollow enclosure
            extents = mesh.bounding_box.extents
            bbox_vol = float(extents[0] * extents[1] * extents[2]) / 1000.0
            volume_cm3 = bbox_vol * 0.15
            logger.warning("Mesh not watertight — estimating volume from bounding box")
    except ImportError:
        # Estimate from enclosure dimensions
        enc = constraints.enclosure
        outer_vol = enc.outer_length * enc.outer_width * enc.outer_height / 1000.0
        inner_vol = enc.inner_length * enc.inner_width * enc.inner_height / 1000.0
        volume_cm3 = outer_vol - inner_vol
        logger.warning("trimesh not installed — estimating volume from dimensions")
    except Exception as e:
        logger.error(f"Failed to read STL volume: {e}")
        # Fallback estimate
        enc = constraints.enclosure
        outer_vol = enc.outer_length * enc.outer_width * enc.outer_height / 1000.0
        inner_vol = enc.inner_length * enc.inner_width * enc.inner_height / 1000.0
        volume_cm3 = outer_vol - inner_vol

    volume_cm3 = round(max(volume_cm3, 0.01), 4)

    # ── Filament calculations ──
    density = MATERIAL_DENSITY.get(material, 1.24)
    weight_g = round(volume_cm3 * density, 2)

    # Filament length for 1.75mm diameter
    filament_radius_cm = 0.175 / 2  # cm
    filament_area_cm2 = math.pi * filament_radius_cm ** 2
    length_m = round(volume_cm3 / (filament_area_cm2 * 100), 2)

    # ── Fasteners ──
    fasteners = []
    standoff_count = len(constraints.standoffs)
    if standoff_count > 0:
        ft = constraints.standoffs[0].fastener_type
        sh = constraints.standoffs[0].height

        fasteners.append({
            "description": f"{ft} standoff, {sh}mm height",
            "quantity": standoff_count,
            "material": "Brass (printed)",
        })

        if constraints.lid_style != "SNAP_FIT":
            fasteners.append({
                "description": f"{ft} × 6mm pan head screw",
                "quantity": standoff_count,
                "material": "Stainless steel",
            })

        if constraints.lid_style == "SCREWED_M3":
            fasteners.append({
                "description": "M3 heat-set insert",
                "quantity": standoff_count,
                "material": "Brass",
            })

    # ── Print settings ──
    dfm = DFM_RULES.get(material, DFM_RULES.get("PETG", {}))
    estimated_hours = round(weight_g / 3.0, 1)  # ~3g/hr rough estimate

    print_settings = {
        "recommended_layer_height": dfm.get("recommended_layer_height", 0.2),
        "infill_percent": 20,
        "supports_required": False,
        "estimated_print_hours": estimated_hours,
    }

    bom = {
        "filament": {
            "material": material,
            "volume_cm3": volume_cm3,
            "length_m": length_m,
            "weight_g": weight_g,
        },
        "fasteners": fasteners,
        "print_settings": print_settings,
    }

    logger.info(
        f"BOM generated: {weight_g}g {material}, {length_m}m filament, "
        f"{len(fasteners)} fastener types"
    )
    return bom


def bom_to_csv(bom: dict) -> str:
    """Convert BOM dict to CSV string for file export."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Category", "Item", "Value", "Unit"])

    # Filament section
    fil = bom["filament"]
    writer.writerow(["Filament", "Material", fil["material"], ""])
    writer.writerow(["Filament", "Volume", fil["volume_cm3"], "cm³"])
    writer.writerow(["Filament", "Length", fil["length_m"], "m"])
    writer.writerow(["Filament", "Weight", fil["weight_g"], "g"])

    # Fasteners
    for f in bom["fasteners"]:
        writer.writerow([
            "Fastener", f["description"],
            f["quantity"], f["material"],
        ])

    # Print settings
    ps = bom["print_settings"]
    writer.writerow(["Print", "Layer Height", ps["recommended_layer_height"], "mm"])
    writer.writerow(["Print", "Infill", ps["infill_percent"], "%"])
    writer.writerow(["Print", "Supports Required", ps["supports_required"], ""])
    writer.writerow(["Print", "Estimated Time", ps["estimated_print_hours"], "hours"])

    return output.getvalue()
