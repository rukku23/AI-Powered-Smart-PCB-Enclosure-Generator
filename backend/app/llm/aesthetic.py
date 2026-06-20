"""
EnclosureAI — Aesthetic Style LLM Module
Optional post-processing pass that adds surface modifications to validated SCAD.
Runs AFTER main validation succeeds. Failure is non-critical.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.llm.interface import LLMInterface
from app.llm.response_parser import extract_scad_code, ResponseParseError
from app.scad.renderer import render_scad
from app.scad.validator import validate_stl

logger = logging.getLogger("enclosureai.llm.aesthetic")

# Map style names to OpenSCAD modification descriptions
AESTHETIC_PROMPTS = {
    "ROUNDED": (
        "Add ROUNDED aesthetic: apply minkowski() with sphere(r=2) to the outer shell only. "
        "This softens all exterior edges and corners. Do not modify inner geometry, cutouts, "
        "standoffs, or snap-fit features. Reduce $fn on the minkowski sphere to 12 for fast rendering."
    ),
    "CONSUMER": (
        "Add CONSUMER aesthetic: chamfer all top exterior edges with a 1.5mm 45-degree bevel. "
        "Add a subtle 0.5mm fillet on vertical edges. Do not modify cutouts, standoffs, or "
        "inner geometry."
    ),
    "INDUSTRIAL": (
        "Add INDUSTRIAL aesthetic: chamfer bottom edges only with 2mm 45-degree cuts. "
        "Add 3 horizontal grip ridges (0.8mm deep, 1.5mm tall, spaced 3mm) on the LEFT and RIGHT "
        "faces of the outer shell. Do not modify cutouts, standoffs, or inner geometry."
    ),
    "WEARABLE": (
        "Add WEARABLE aesthetic: apply aggressive rounding to all exterior surfaces using "
        "minkowski() with sphere(r=3, $fn=16). Minimize all protrusions — recess any screw "
        "bosses flush with the outer surface. Do not modify cutouts or inner geometry."
    ),
}


def build_aesthetic_prompt(scad_code: str, style: str) -> list[dict]:
    """
    Build the aesthetic modification prompt.
    Returns message list for LLM consumption.
    """
    style_desc = AESTHETIC_PROMPTS.get(style, "")
    if not style_desc:
        return []

    return [
        {
            "role": "system",
            "content": (
                "You are an OpenSCAD expert. You modify enclosure code to add aesthetic "
                "surface treatments. RULES:\n"
                "1. Only modify the OUTER SHELL geometry\n"
                "2. Never touch cutouts, standoffs, snap-fits, or ventilation slots\n"
                "3. Return the COMPLETE modified OpenSCAD file\n"
                "4. Keep all existing modules and variables\n"
                "5. Add comments marking your aesthetic modifications"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Given this validated OpenSCAD enclosure code:\n\n"
                f"```openscad\n{scad_code}\n```\n\n"
                f"{style_desc}\n\n"
                f"Return the complete modified file."
            ),
        },
    ]


async def apply_aesthetic_style(
    scad_code: str,
    style: str,
    llm: LLMInterface,
    job_id: str,
    output_dir: str,
) -> Optional[str]:
    """
    Apply aesthetic modifications to validated SCAD code.

    Returns modified SCAD code on success, None on failure.
    Failure is NON-CRITICAL — the original code is used instead.
    """
    if style == "MINIMAL" or style not in AESTHETIC_PROMPTS:
        logger.info(f"Aesthetic style '{style}' — skipping modification")
        return None

    logger.info(f"Applying aesthetic style: {style}")

    try:
        messages = build_aesthetic_prompt(scad_code, style)
        if not messages:
            return None

        response = await llm.generate(messages)
        modified_code = extract_scad_code(response)

        # Re-validate: render and check
        aesthetic_job_id = f"{job_id}_aesthetic"
        render_result = await render_scad(modified_code, aesthetic_job_id, output_dir)

        if render_result.success:
            stl_result = validate_stl(render_result.stl_path)
            if stl_result.passed:
                logger.info(f"Aesthetic style '{style}' applied successfully")
                return modified_code
            else:
                logger.warning(
                    f"Aesthetic STL validation failed: {stl_result.errors}. "
                    "Using original non-aesthetic version."
                )
        else:
            logger.warning(
                f"Aesthetic render failed: {render_result.error_message}. "
                "Using original non-aesthetic version."
            )

    except ResponseParseError as e:
        logger.warning(f"Aesthetic LLM response parse failed: {e}")
    except Exception as e:
        logger.error(f"Aesthetic modification error: {e}")

    return None
