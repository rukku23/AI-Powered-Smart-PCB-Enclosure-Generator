"""
EnclosureAI — STEP Exporter
Reconstructs enclosure geometry from ConstraintSchema using CadQuery.
STEP is reconstructed from constraints, NOT from SCAD source.
STEP export failure is non-critical — the job continues without it.
"""
from __future__ import annotations

import logging
from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.export.step")


class STEPExportError(Exception):
    """Non-critical error during STEP export."""
    pass


def export_step(constraints: ConstraintSchema, output_path: str) -> str:
    """
    Reconstruct enclosure geometry from ConstraintSchema using CadQuery
    and export as STEP file.

    Non-critical: wraps everything in try/except. Failure is logged
    but does not crash the job.

    Returns output_path on success.
    Raises STEPExportError on failure.
    """
    try:
        import cadquery as cq
    except ImportError:
        raise STEPExportError(
            "CadQuery not installed. STEP export unavailable. "
            "Install with: pip install cadquery"
        )

    try:
        enc = constraints.enclosure
        ol = enc.outer_length
        ow = enc.outer_width
        oh = enc.outer_height
        wall = enc.wall
        lid_t = enc.lid_thickness
        body_h = oh - lid_t

        # ── Step 1: Hollow body box ──
        body = (
            cq.Workplane("XY")
            .box(ol, ow, body_h, centered=False)
        )
        # Shell: remove top face, hollow out
        body = body.faces(">Z").shell(-wall)

        # ── Step 2: Add standoffs ──
        for s in constraints.standoffs:
            # Position standoff inside the body
            standoff = (
                cq.Workplane("XY")
                .transformed(offset=(s.x, s.y, wall))
                .circle(s.outer_diameter / 2)
                .extrude(s.height)
            )
            # Drill hole
            hole = (
                cq.Workplane("XY")
                .transformed(offset=(s.x, s.y, wall))
                .circle(s.inner_diameter / 2)
                .extrude(s.height)
            )
            body = body.union(standoff).cut(hole)

        # ── Step 3: Subtract connector cutouts ──
        for cut in constraints.cutouts:
            width = cut.x_end - cut.x_start
            height = cut.z_end - cut.z_start

            if cut.face == "FRONT":
                cutout = (
                    cq.Workplane("XY")
                    .transformed(offset=(cut.x_start, -0.1, cut.z_start))
                    .box(width, wall + 0.2, height, centered=False)
                )
            elif cut.face == "BACK":
                cutout = (
                    cq.Workplane("XY")
                    .transformed(offset=(cut.x_start, ow - wall - 0.1, cut.z_start))
                    .box(width, wall + 0.2, height, centered=False)
                )
            elif cut.face == "LEFT":
                cutout = (
                    cq.Workplane("XY")
                    .transformed(offset=(-0.1, cut.x_start, cut.z_start))
                    .box(wall + 0.2, width, height, centered=False)
                )
            elif cut.face == "RIGHT":
                cutout = (
                    cq.Workplane("XY")
                    .transformed(offset=(ol - wall - 0.1, cut.x_start, cut.z_start))
                    .box(wall + 0.2, width, height, centered=False)
                )
            else:
                continue

            body = body.cut(cutout)

        # ── Step 4: Create lid ──
        lid = (
            cq.Workplane("XY")
            .transformed(offset=(0, 0, body_h + 5))  # Offset above body
            .box(ol, ow, lid_t, centered=False)
        )

        # ── Step 5: Combine and export ──
        assembly = body.union(lid)
        assembly.val().exportStep(output_path)

        logger.info(f"STEP exported: {output_path}")
        return output_path

    except Exception as e:
        raise STEPExportError(f"STEP export failed: {e}")
