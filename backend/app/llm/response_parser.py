"""
EnclosureAI — LLM Response Parser
Extracts OpenSCAD code, reasoning blocks, and builds correction prompts.
"""
from __future__ import annotations

import json
import re
import logging

logger = logging.getLogger("enclosureai.llm.parser")


class ResponseParseError(Exception):
    """Raised when LLM response cannot be parsed as valid OpenSCAD."""
    pass


def extract_scad_code(llm_response: str) -> str:
    """
    Strip markdown code fences if present and validate as OpenSCAD.
    Handles: ```openscad ... ```, ```scad ... ```, ``` ... ```
    """
    if not llm_response or not llm_response.strip():
        raise ResponseParseError("Empty LLM response")

    text = llm_response.strip()

    # Strip markdown fences: ```openscad\n...\n``` or ```scad\n...\n```
    fence_pattern = r"```(?:openscad|scad|)?\s*\n(.*?)```"
    matches = re.findall(fence_pattern, text, re.DOTALL)
    if matches:
        # Use the longest match (the main code block)
        text = max(matches, key=len).strip()

    # Also handle single backtick wrapping
    if text.startswith("`") and text.endswith("`"):
        text = text.strip("`").strip()

    # Validate: must start with comment, variable, module, or include
    first_line = text.split("\n")[0].strip()
    valid_starts = ("/*", "//", "$", "module", "function", "include", "use")
    if not any(first_line.startswith(s) for s in valid_starts):
        # Check if any line looks like OpenSCAD
        has_scad = any(
            kw in text for kw in ["module ", "cube(", "cylinder(", "difference(", "union(", "translate("]
        )
        if not has_scad:
            raise ResponseParseError(
                f"Response does not appear to be OpenSCAD code. "
                f"First line: {first_line[:80]}"
            )

    return text


def extract_reasoning_block(scad_code: str) -> str:
    """
    Extract content between === ENCLOSUREAI DESIGN REASONING === markers.
    Returns empty string if not found (non-blocking).
    """
    pattern = r"/\*\s*===\s*ENCLOSUREAI DESIGN REASONING\s*===\s*(.*?)\s*={3,}\s*\*/"
    match = re.search(pattern, scad_code, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback: try to find any leading block comment
    block_pattern = r"^/\*(.*?)\*/"
    match = re.search(block_pattern, scad_code, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""


def build_correction_prompt(
    original_scad: str,
    error_message: str,
    attempt_number: int,
) -> dict:
    """
    Build correction user message for the retry loop.
    Instructs the LLM to fix only the specific error.
    """
    return {
        "role": "user",
        "content": (
            f"The OpenSCAD code produced this compiler error on attempt {attempt_number}:\n\n"
            f"ERROR: {error_message}\n\n"
            f"Fix ONLY the specific issue above.\n"
            f"Do not restructure the file or change any variable values.\n"
            f"Output the complete corrected file.\n\n"
            f"Original code:\n{original_scad}"
        ),
    }


def parse_thermal_response(response: str) -> dict:
    """
    Parse thermal analysis JSON from LLM response.
    Returns dict with safe fallback values if parsing fails.
    """
    defaults = {
        "thermal_health_score": 0,
        "verdict": "UNKNOWN",
        "vent_area_required_cm2": 0.0,
        "vent_area_recommended_cm2": 0.0,
        "airflow_direction": "TOP_OUTLET_BOTTOM_INLET",
        "passive_cooling_sufficient": True,
        "hotspot_summary": "",
        "recommendation": "",
    }

    text = response.strip()

    # Strip markdown fences
    json_pattern = r"```(?:json)?\s*\n(.*?)```"
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # Try to find JSON object
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]

    try:
        parsed = json.loads(text)
        # Merge with defaults for missing keys
        result = {**defaults, **parsed}
        # Clamp score
        result["thermal_health_score"] = max(0, min(100, int(result["thermal_health_score"])))
        return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse thermal response: {e}")
        return defaults
