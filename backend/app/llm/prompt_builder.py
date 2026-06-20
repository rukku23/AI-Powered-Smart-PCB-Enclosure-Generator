"""
EnclosureAI — Prompt Builder
Constructs LLM messages from ConstraintSchema with few-shot examples.
Implements token estimation for Ollama compatibility.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict

from app.llm.few_shot_library import get_few_shot_examples
from app.schemas.constraint_schemas import ConstraintSchema

logger = logging.getLogger("enclosureai.llm.prompt")

OLLAMA_TOKEN_LIMIT = 7000

SYSTEM_PROMPT = """You are an expert OpenSCAD engineer specialising in PCB enclosure design for 3D printing.

=== STRICT OUTPUT RULES ===
1. Output ONLY valid OpenSCAD code. No markdown fences. No prose outside comments.
2. Begin output with a design reasoning block as a multi-line OpenSCAD comment in this EXACT format:
   /* === ENCLOSUREAI DESIGN REASONING ===
   GEOMETRY: [explain outer dimension calculation]
   FEATURES: [explain each cutout and standoff decision]
   THERMAL: [explain vent placement and thermal score]
   MATERIAL: [explain wall thickness and snap-fit tolerance]
   ======================================= */
3. Use ONLY numeric values from the constraint JSON below — NEVER compute dimensions yourself.
4. Every variable must be named descriptively (no a, b, x1).
5. Structure the file as: variables → module definitions → assembly call at bottom.
6. The file must compile under OpenSCAD 2021.01 with no warnings.
7. Use $fn = 30 for curved surfaces.
8. Add 0.1mm tolerance offsets for boolean operations (translate -0.1, add +0.2 to dimensions).
9. Place the lid next to the body (translated by outer_length + 10 in X).

=== MODULES TO DEFINE ===
- enclosure_body(): main shell with wall thickness subtracted
- lid(): matching lid with appropriate closure mechanism
- standoffs(): PCB mounting standoffs inside the body
- One module per connector cutout (named descriptively)
- top_vents(): ventilation slots if ventilation_enabled is true
- snap_tabs_body() / screw_bosses(): closure mechanism matching lid_style

=== FEW-SHOT EXAMPLES ===
{few_shot_examples}
"""

USER_PROMPT_TEMPLATE = """Generate the OpenSCAD enclosure code for the following PCB specification.
Follow all rules exactly. Use ONLY the numeric values from this constraint JSON.

=== CONSTRAINT JSON ===
{constraint_json}

Generate the complete OpenSCAD file now."""


def _constraint_to_dict(constraints: ConstraintSchema) -> dict:
    """Convert ConstraintSchema to serializable dict."""
    d = {}

    d["pcb"] = {
        "length": constraints.pcb.length,
        "width": constraints.pcb.width,
        "thickness": constraints.pcb.thickness,
    }

    enc = constraints.enclosure

    d["enclosure"] = {
        "outer_length": enc.outer_length,
        "outer_width": enc.outer_width,
        "outer_height": enc.outer_height,
        "wall": enc.wall,
        "clearance": enc.clearance,
        "lid_thickness": enc.lid_thickness,
        "inner_length": enc.inner_length,
        "inner_width": enc.inner_width,
        "inner_height": enc.inner_height,
    }

    d["standoffs"] = [asdict(s) for s in constraints.standoffs]
    d["cutouts"] = [asdict(c) for c in constraints.cutouts]
    d["thermal_zones"] = [asdict(z) for z in constraints.thermal_zones]

    if constraints.snap_fit:
        d["snap_fit"] = asdict(constraints.snap_fit)

    if constraints.vent_spec:
        d["vent_spec"] = asdict(constraints.vent_spec)

    d["material"] = constraints.material
    d["print_technology"] = constraints.print_technology
    d["lid_style"] = constraints.lid_style
    d["total_wattage"] = constraints.total_wattage
    d["max_component_height"] = constraints.max_component_height
    d["ventilation_enabled"] = constraints.ventilation_enabled

    return d


def token_count_estimate(text: str) -> int:
    """Estimate token count. ~4 chars per token for English/code."""
    return len(text) // 4


def build_generation_prompt(constraints: ConstraintSchema) -> list[dict]:
    """
    Build the complete LLM message list for OpenSCAD generation.
    """

    provider = os.getenv("LLM_PROVIDER", "claude").lower()

    # Build constraint JSON
    constraint_json = json.dumps(
        _constraint_to_dict(constraints),
        indent=2
    )

    # Default few-shot examples
    few_shot = get_few_shot_examples(3)

    # Disable few-shot for Ollama tiny models
    if provider == "ollama":
        few_shot = ""
        logger.info("Few-shot examples disabled for Ollama")

    # Build prompts
    system = SYSTEM_PROMPT.format(
        few_shot_examples=few_shot
    )

    user = USER_PROMPT_TEMPLATE.format(
        constraint_json=constraint_json
    )

    total_estimate = token_count_estimate(system + user)

    # Reduce if too large
    if total_estimate > OLLAMA_TOKEN_LIMIT and provider != "ollama":
        few_shot = get_few_shot_examples(1)

        system = SYSTEM_PROMPT.format(
            few_shot_examples=few_shot
        )

        total_estimate = token_count_estimate(system + user)

    logger.info(
        f"Prompt built: ~{total_estimate} tokens"
    )

    return [
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "user",
            "content": user,
        },
    ]


# ═══════════════════════════════════════════════════════════════
# Thermal Sub-Prompt
# ═══════════════════════════════════════════════════════════════

THERMAL_SYSTEM_PROMPT = """You are a thermal management engineer.

Analyse the PCB enclosure specification and return ONLY a JSON object with these exact fields:

{
  "thermal_health_score": <0-100>,
  "verdict": <string>,
  "vent_area_required_cm2": <float>,
  "vent_area_recommended_cm2": <float>,
  "airflow_direction": <"TOP_OUTLET_BOTTOM_INLET"|"SIDE_CROSS_FLOW"|"FAN_REQUIRED">,
  "passive_cooling_sufficient": <bool>,
  "hotspot_summary": <string>,
  "recommendation": <string>
}

Return ONLY the JSON. No explanation. No markdown.
"""


def build_thermal_prompt(constraints: ConstraintSchema) -> list[dict]:
    """Build thermal analysis prompt."""

    constraint_json = json.dumps(
        _constraint_to_dict(constraints),
        indent=2
    )

    return [
        {
            "role": "system",
            "content": THERMAL_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Analyse the thermal characteristics "
                f"of this PCB enclosure:\n\n"
                f"{constraint_json}\n\n"
                f"Return the thermal analysis JSON."
            ),
        },
    ]