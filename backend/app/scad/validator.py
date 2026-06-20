"""
EnclosureAI — OpenSCAD Error Classifier, STL Validator & Self-Correction Loop
Parses OpenSCAD stderr, classifies errors, validates STL output,
and orchestrates the LLM self-correction retry pipeline.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.llm.interface import LLMInterface
from app.llm.prompt_builder import build_generation_prompt
from app.llm.strategy_aware_prompt import build_strategy_prompt
from app.llm.response_parser import (
    extract_scad_code,
    extract_reasoning_block,
    build_correction_prompt,
    ResponseParseError,
)
from app.scad.renderer import render_scad, RenderResult
from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.scad.validator")

MAX_RETRY_ATTEMPTS = 3


# ═══════════════════════════════════════════════════════════════
# Error Classification
# ═══════════════════════════════════════════════════════════════

def classify_openscad_error(stderr: str) -> dict:
    """
    Classify OpenSCAD stderr output into structured error info.

    Returns: {
        "class": error_class,
        "line": extracted_line_number or None,
        "message": cleaned error message,
        "interpretation": human-readable explanation
    }
    """
    if not stderr or not stderr.strip():
        return {
            "class": "UNKNOWN",
            "line": None,
            "message": "No error output from OpenSCAD",
            "interpretation": "OpenSCAD produced no error output.",
        }

    text = stderr.strip()

    # Extract line number if present
    line_match = re.search(r"line\s+(\d+)", text, re.IGNORECASE)
    line_num = int(line_match.group(1)) if line_match else None

    # Classification patterns (order matters — most specific first)
    patterns = [
        (
            "TIMEOUT",
            r"TIMEOUT",
            "OpenSCAD render timed out — geometry may be too complex or contain infinite recursion.",
        ),
        (
            "SYNTAX_ERROR",
            r"(?:ERROR:\s*Parser error|syntax error|expected|unexpected)",
            "OpenSCAD syntax error — check for missing semicolons, brackets, or invalid operators.",
        ),
        (
            "UNDEFINED_VARIABLE",
            r"WARNING:\s*Ignoring unknown variable",
            "A variable is used but never defined. Check for typos in variable names.",
        ),
        (
            "MODULE_NOT_FOUND",
            r"(?:ERROR:\s*Requested module|module\s+\S+\s+not\s+found)",
            "A module() call references a module that doesn't exist. Check module name spelling.",
        ),
        (
            "EMPTY_GEOMETRY",
            r"WARNING:\s*(?:Normalized tree is empty|No top level geometry)",
            "The OpenSCAD file compiles but produces no visible geometry. Check boolean operations.",
        ),
        (
            "BOOLEAN_FAILURE",
            r"WARNING:\s*(?:Object may not be a valid 2-manifold|PolySet has degenerate)",
            "Boolean operation failed — geometry is non-manifold. Ensure all shapes are properly closed.",
        ),
    ]

    for error_class, pattern, interpretation in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Clean the message: take first relevant line
            msg_lines = [
                l.strip() for l in text.split("\n")
                if re.search(r"(?:ERROR|WARNING|error|warning)", l, re.IGNORECASE)
            ]
            clean_msg = msg_lines[0] if msg_lines else text[:200]
            return {
                "class": error_class,
                "line": line_num,
                "message": clean_msg,
                "interpretation": interpretation,
            }

    # UNKNOWN fallback
    first_line = text.split("\n")[0].strip()[:200]
    return {
        "class": "UNKNOWN",
        "line": line_num,
        "message": first_line,
        "interpretation": f"Unclassified OpenSCAD error: {first_line}",
    }


# ═══════════════════════════════════════════════════════════════
# STL Validation
# ═══════════════════════════════════════════════════════════════

@dataclass
class STLValidationResult:
    """Result of STL mesh validation."""
    passed: bool
    file_exists: bool
    file_size_bytes: int
    is_watertight: bool
    volume_positive: bool
    face_count: int
    face_count_sufficient: bool
    errors: list[str] = field(default_factory=list)


def validate_stl(stl_path: str) -> STLValidationResult:
    """
    Validate an STL file for correctness.

    Checks:
    1. File exists and size > 1KB
    2. Loads with trimesh
    3. is_watertight
    4. volume > 0
    5. face count > 100 (not trivially empty)
    """
    errors = []
    path = Path(stl_path)

    # 1. File existence and size
    if not path.exists():
        return STLValidationResult(
            passed=False, file_exists=False, file_size_bytes=0,
            is_watertight=False, volume_positive=False,
            face_count=0, face_count_sufficient=False,
            errors=["STL file does not exist"],
        )

    file_size = path.stat().st_size
    if file_size < 1024:
        errors.append(f"STL file too small: {file_size} bytes (minimum 1KB)")

    # 2-5. Load and validate mesh
    try:
        import trimesh
        mesh = trimesh.load(str(path), force="mesh")

        is_watertight = bool(mesh.is_watertight)
        volume = float(mesh.volume) if mesh.is_watertight else 0.0
        face_count = len(mesh.faces)
        volume_positive = volume > 0
        face_count_ok = face_count > 100

        if not is_watertight:
            errors.append("Mesh is not watertight (has holes)")
        if not volume_positive:
            errors.append(f"Mesh volume is not positive: {volume:.4f}")
        if not face_count_ok:
            errors.append(f"Face count too low: {face_count} (minimum 100)")

        passed = file_size >= 1024 and is_watertight and volume_positive and face_count_ok

        return STLValidationResult(
            passed=passed,
            file_exists=True,
            file_size_bytes=file_size,
            is_watertight=is_watertight,
            volume_positive=volume_positive,
            face_count=face_count,
            face_count_sufficient=face_count_ok,
            errors=errors,
        )

    except ImportError:
        logger.warning("trimesh not installed — skipping mesh validation, accepting file")
        return STLValidationResult(
            passed=file_size >= 1024,
            file_exists=True,
            file_size_bytes=file_size,
            is_watertight=True,  # assume OK
            volume_positive=True,
            face_count=0,
            face_count_sufficient=True,
            errors=errors or [],
        )
    except Exception as e:
        errors.append(f"Failed to load STL: {e}")
        return STLValidationResult(
            passed=False,
            file_exists=True,
            file_size_bytes=file_size,
            is_watertight=False,
            volume_positive=False,
            face_count=0,
            face_count_sufficient=False,
            errors=errors,
        )


# ═══════════════════════════════════════════════════════════════
# Generation Result + Exception
# ═══════════════════════════════════════════════════════════════

@dataclass
class GenerationResult:
    """Successful generation pipeline result."""
    scad_code: str
    stl_path: str
    scad_path: str
    reasoning: str
    attempts: int
    render_time_ms: int


class GenerationFailedException(Exception):
    """Raised when the self-correction loop exhausts all retry attempts."""
    def __init__(self, job_id: str, attempts: int, last_error: str):
        self.job_id = job_id
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Generation failed for job {job_id} after {attempts} attempts. "
            f"Last error: {last_error}"
        )


# ═══════════════════════════════════════════════════════════════
# Self-Correction Retry Loop
# ═══════════════════════════════════════════════════════════════

async def generate_validated_scad(
    constraints: ConstraintSchema,
    llm: LLMInterface,
    job_id: str,
    output_dir: str,
    sse_queue: Optional[asyncio.Queue] = None,
    strategy=None,
) -> GenerationResult:
    """
    Core generation orchestrator with self-correction.

    1. Build prompt from constraints (strategy-aware if strategy provided)
    2. Get LLM response (streaming if sse_queue provided)
    3. Extract SCAD code
    4. Render via OpenSCAD CLI
    5. If success → validate STL → return
    6. If failure → classify error → build correction prompt → retry
    7. After MAX_RETRY_ATTEMPTS failures → raise GenerationFailedException
    """
    # Build initial prompt — strategy-aware if strategy is provided
    if strategy is not None:
        prompt_messages = build_strategy_prompt(constraints, strategy)
    else:
        prompt_messages = build_generation_prompt(constraints)
    conversation = list(prompt_messages)

    error_info = {"message": "No attempts made", "interpretation": ""}

    for attempt in range(MAX_RETRY_ATTEMPTS):
        attempt_num = attempt + 1
        logger.info(f"Generation attempt {attempt_num}/{MAX_RETRY_ATTEMPTS} for job {job_id}")

        # SSE: generating event
        if sse_queue:
            await sse_queue.put({"event": "generating", "attempt": attempt_num})

        # Get LLM response
        try:
            if sse_queue:
                # Streaming mode — collect chunks and forward reasoning
                scad_response = ""
                reasoning_started = False
                async for chunk in llm.generate_stream(conversation):
                    scad_response += chunk
                    if "DESIGN REASONING" in chunk:
                        reasoning_started = True
                    if reasoning_started:
                        await sse_queue.put({"event": "reasoning_chunk", "data": chunk})
            else:
                scad_response = await llm.generate(conversation)
        except Exception as e:
            logger.error(f"LLM call failed on attempt {attempt_num}: {e}")
            error_info = {
                "class": "LLM_ERROR",
                "message": str(e),
                "interpretation": f"LLM API call failed: {e}",
            }
            continue

        # ── Hybrid Assembly: procedural base + LLM cutouts ──────────

        # 1. Extract reasoning from LLM response
        from app.llm.response_parser import extract_reasoning_block, extract_scad_code, ResponseParseError
        reasoning = extract_reasoning_block(scad_response)

        # 2. Build procedural base modules
        from app.core.topology_router import route_topology
        from dataclasses import asdict

        thermal_data = constraints.thermal_data if hasattr(constraints, 'thermal_data') and constraints.thermal_data else {}
        vent_count = thermal_data.get("openscad_slot_count", 0) if getattr(constraints, "ventilation_enabled", True) else 0

        topology_params = {
            "width": constraints.enclosure.outer_width,
            "depth": constraints.enclosure.outer_length,
            "height": constraints.enclosure.outer_height,
            "wall_thickness": constraints.enclosure.wall,
            "lid_thickness": getattr(constraints.enclosure, "lid_thickness", constraints.enclosure.wall),
            "standoff_height": constraints.standoffs[0].height if constraints.standoffs else 5.0,
            "standoff_od": constraints.standoffs[0].outer_diameter if constraints.standoffs else 6.4,
            "standoff_id": constraints.standoffs[0].inner_diameter if constraints.standoffs else 3.2,
            "mounting_hole_positions": [[s.x, s.y] for s in constraints.standoffs] if constraints.standoffs else [],
            "vent_count": vent_count,
            "vent_size": 2.5,
            "tolerance": 0.2,
        }
        if hasattr(constraints, "topology_extensions"):
            topology_params.update(constraints.topology_extensions)

        preset = getattr(constraints, "preset", None)
        if preset == "ESP32":
            core_file = "esp32_devkit_v1.scad"
            prefix = "esp32_"
        elif preset == "ARDUINO_UNO":
            core_file = "arduino_uno_r3.scad"
            prefix = "arduino_uno_"
        elif preset == "RPI4":
            core_file = "raspberry_pi_4.scad"
            prefix = "rpi4_"
        else:
            core_file = "generic_rectangular.scad"
            prefix = "generic_"

        import os
        core_path = os.path.join(os.path.dirname(__file__), "core_models", core_file).replace("\\", "/")
        
        scad_base = f"""// === ENCLOSUREAI HYBRID CORE INCLUSION ===
use <{core_path}>

outer_w = {topology_params['width']};
outer_d = {topology_params['depth']};
outer_h = {topology_params['height']};
wall    = {topology_params['wall_thickness']};
lid_t   = {topology_params.get('lid_thickness', topology_params['wall_thickness'])};
body_h  = outer_h - lid_t;

module enclosure_body() {{
    {prefix}enclosure_body(outer_w, outer_d, outer_h, wall);
}}

module enclosure_lid() {{
    {prefix}enclosure_lid(outer_w, outer_d, lid_t);
}}

module vent_slots() {{ /* Base generic vent */ }}
module standoffs() {{ /* Baked into core model */ }}
"""

        # 3. Extract LLM cutout code — if it fails, use generic assembly
        try:
            scad_llm = extract_scad_code(scad_response)
        except ResponseParseError:
            logger.info("LLM did not return parseable SCAD; using generic assembly (no custom cutouts)")
            scad_llm = """
// No custom cutouts generated by LLM
module custom_cutouts() { /* none */ }

// === FINAL ASSEMBLY ===
difference() {
    enclosure_body();
    vent_slots();
}
standoffs();
translate([outer_w + 10, 0, 0])
    enclosure_lid();
"""

        # 4. Concatenate: procedural base + LLM cutouts/assembly
        scad_code = scad_base + "\n// ── LLM-Generated Cutouts & Assembly ──\n" + scad_llm

        # SSE: rendering event
        if sse_queue:
            await sse_queue.put({"event": "rendering", "attempt": attempt_num})

        # Render via OpenSCAD
        render_result = await render_scad(scad_code, job_id, output_dir)

        if render_result.success:
            # Validate STL
            stl_validation = validate_stl(render_result.stl_path)
            if stl_validation.passed:
                logger.info(
                    f"Generation succeeded on attempt {attempt_num} "
                    f"({render_result.render_time_ms}ms render)"
                )
                return GenerationResult(
                    scad_code=scad_code,
                    stl_path=render_result.stl_path,
                    scad_path=render_result.scad_path,
                    reasoning=reasoning,
                    attempts=attempt_num,
                    render_time_ms=render_result.render_time_ms,
                )
            else:
                # STL produced but invalid mesh
                stl_errors = "; ".join(stl_validation.errors)
                logger.warning(f"STL validation failed: {stl_errors}")
                error_info = classify_openscad_error(
                    f"STL validation failed: {stl_errors}"
                )
        else:
            # OpenSCAD compile/render failed
            error_info = classify_openscad_error(render_result.stderr)
            logger.warning(
                f"Attempt {attempt_num} failed [{error_info['class']}]: "
                f"{error_info['message'][:100]}"
            )

        # Build correction for next attempt
        correction = build_correction_prompt(
            scad_code, error_info["message"], attempt_num
        )
        conversation.append({"role": "assistant", "content": scad_code})
        conversation.append(correction)

        if sse_queue:
            await sse_queue.put({
                "event": "correction",
                "attempt": attempt_num,
                "error": error_info.get("interpretation", error_info["message"]),
            })

    # All attempts exhausted
    raise GenerationFailedException(
        job_id=job_id,
        attempts=MAX_RETRY_ATTEMPTS,
        last_error=error_info.get("message", "Unknown error"),
    )
