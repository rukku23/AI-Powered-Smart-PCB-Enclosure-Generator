"""
EnclosureAI — Generate Endpoint Router (Phase 8)
POST /api/generate — SSE streaming endpoint for enclosure generation.
Pipeline: Validate → Constrain → DFM → Strategy Select → Topology Extend → LLM → Render → Validate.
"""
from __future__ import annotations
from pathlib import Path
from app.core.topology_router import route_topology
import asyncio
import json
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.constraint_engine import ConstraintEngine
from app.core.dfm_validator import validate_dfm_compliance, DFMValidationError
from app.core.thermal_engine import compute_thermal
from app.core.strategy_selector import DesignStrategySelector
from app.core.topology_constraints import apply_topology_extensions
from app.core.design_context import DesignContext
from app.llm.interface import llm_factory
from app.llm.prompt_builder import build_thermal_prompt
from app.llm.response_parser import parse_thermal_response
from app.scad.validator import (
    generate_validated_scad,
    GenerationFailedException,
)
from app.schemas.input_schemas import EnclosureRequest
from app.core.demo_cache import get_cached_preset, stream_cached_response

logger = logging.getLogger("enclosureai.routers.generate")

router = APIRouter(prefix="/api", tags=["generation"])

GENERATED_FILES_DIR = os.getenv("GENERATED_FILES_DIR", "./generated_files")

_strategy_selector = DesignStrategySelector()


def _sse_event(data: dict) -> str:
    """Format dict as SSE event line."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/generate")
async def generate_enclosure(request: EnclosureRequest):
    """
    Generate an enclosure from PCB specifications.
    Returns SSE stream with generation progress events:
      - validating → constraints computed
      - dfm_result → DFM validation results
      - strategy_selected → topology strategy chosen
      - generating → LLM generation started (per attempt)
      - reasoning_chunk → design reasoning text
      - rendering → OpenSCAD rendering started
      - correction → self-correction retry
      - complete → generation succeeded
      - error → generation failed
    """
    job_id = str(uuid4())

    # Check demo cache first
    cache_key = get_cached_preset(getattr(request, 'preset', None))
    if cache_key:
        logger.info(f"Using demo cache for preset: {cache_key}")
        return StreamingResponse(
            stream_cached_response(cache_key, job_id, GENERATED_FILES_DIR),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async def event_stream():
        try:
            # ── Step 1: Compute constraints ──
            yield _sse_event({"event": "validating", "job_id": job_id})

            engine = ConstraintEngine()
            constraints = engine.compute(request)

            yield _sse_event({
                "event": "constraints_computed",
                "job_id": job_id,
                "enclosure": {
                    "outer_length": constraints.enclosure.outer_length,
                    "outer_width": constraints.enclosure.outer_width,
                    "outer_height": constraints.enclosure.outer_height,
                    "wall": constraints.enclosure.wall,
                    "material": constraints.material,
                },
                "standoff_count": len(constraints.standoffs),
                "cutout_count": len(constraints.cutouts),
                "thermal_zone_count": len(constraints.thermal_zones),
                "total_wattage": constraints.total_wattage,
            })

            # ── Step 2: DFM Validation (strategy-agnostic) ──
            try:
                violations = validate_dfm_compliance(constraints)
                dfm_warnings = [
                    {"rule": v.rule, "severity": v.severity, "message": v.message}
                    for v in violations
                ]
                yield _sse_event({
                    "event": "dfm_result",
                    "job_id": job_id,
                    "passed": True,
                    "warnings": dfm_warnings,
                })
            except DFMValidationError as e:
                yield _sse_event({
                    "event": "dfm_result",
                    "job_id": job_id,
                    "passed": False,
                    "violations": [
                        {"rule": v.rule, "severity": v.severity, "message": v.message}
                        for v in e.violations
                    ],
                })
                yield _sse_event({
                    "event": "error",
                    "job_id": job_id,
                    "message": "DFM validation failed with errors. Adjust parameters.",
                })
                return

            # ── 2. Compute thermal analysis (THE FIX — was disconnected before) ──
            from app.core.thermal_engine import compute_thermal
            thermal = compute_thermal(
                components=[
                    {
                        "label":      c.label,
                        "wattage":    c.wattage,
                        "position_x": c.position_x,
                        "position_y": c.position_y,
                    }
                    for c in getattr(request, 'components', [])
                ],
                pcb_length=request.pcb.length,
                pcb_width=request.pcb.width,
                enclosure_length=constraints.enclosure.outer_length,
                enclosure_width=constraints.enclosure.outer_width,
                ventilation_enabled=request.ventilation,
            )

            # ── 3. Inject thermal into constraints (THE FIX — was missing) ───────
            constraints.thermal_data = thermal.to_dict()

            # ── 4. Strategy selection ─────────────────────────────────────────────
            from app.core.strategy_selector import DesignStrategySelector
            selector = DesignStrategySelector()
            design_context = getattr(request, 'design_context', None) or DesignContext()
            
            connector_face_count = len({
                c.face_access for c in getattr(request, 'components', [])
                if getattr(c, 'face_access', "NONE") != "NONE"
            })
            
            strategy = selector.select(
                context=design_context,
                total_wattage=thermal.total_wattage,
                pcb_length=request.pcb.length,
                pcb_width=request.pcb.width,
                connector_face_count=connector_face_count
            )

            # Override strategy to CHIMNEY if thermal engine says chimney needed
            if thermal.openscad_chimney_needed:
                from app.core.strategy_selector import STRATEGY_LIBRARY
                strategy = STRATEGY_LIBRARY["CHIMNEY_THERMAL"]

            # ── 5. Apply topology constraint extensions ───────────────────────────
            from app.core.topology_constraints import apply_topology_extensions
            
            # Note: We keep constraints as ConstraintSchema but add strategy to it.
            constraints.strategy_name = strategy.name
            constraints = apply_topology_extensions(strategy, constraints)
            
            yield _sse_event({
                "event": "strategy_selected",
                "job_id": job_id,
                "strategy": strategy.name,
                "display_name": getattr(strategy, "display_name", strategy.name),
                "reason": strategy.description,
                "score": 10.0,
            })

            yield _sse_event({
                "event": "thermal_computed",
                "job_id": job_id,
                "thermal": {
                    "thermal_health_score":   thermal.thermal_health_score,
                    "verdict":                thermal.verdict,
                    "slot_count":             thermal.slot_count,
                    "vent_face":              thermal.vent_face_primary,
                    "required_area_cm2":      thermal.required_vent_area_cm2,
                    "implemented_area_cm2":   thermal.implemented_vent_area_cm2,
                    "passive_cooling_ok":     thermal.passive_cooling_ok,
                    "recommendation":         thermal.recommendation,
                    "chimney_needed":         thermal.openscad_chimney_needed,
                }
            })
            
            

            # ── Step 6: LLM Generation with self-correction ──
            sse_queue = asyncio.Queue()
            llm = llm_factory()

            gen_task = asyncio.create_task(
                generate_validated_scad(
                    constraints=constraints,
                    llm=llm,
                    job_id=job_id,
                    output_dir=GENERATED_FILES_DIR,
                    sse_queue=sse_queue,
                    strategy=strategy,
                )
            )

            while not gen_task.done():
                try:
                    event = await asyncio.wait_for(sse_queue.get(), timeout=1.0)
                    yield _sse_event({**event, "job_id": job_id})
                except asyncio.TimeoutError:
                    continue

            while not sse_queue.empty():
                event = sse_queue.get_nowait()
                yield _sse_event({**event, "job_id": job_id})

            result = gen_task.result()

            # ── Export & Packaging ──
            job_dir = Path(GENERATED_FILES_DIR) / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Write thermal report
            thermal_path = job_dir / "thermal_report.json"
            with open(thermal_path, "w") as f:
                json.dump(thermal.__dict__, f, indent=2)
                
            # Write BOM (dummy for now if engine doesn't produce it, or empty)
            bom_path = job_dir / "bom.json"
            with open(bom_path, "w") as f:
                json.dump({"components": []}, f, indent=2)
                
            # Write AI Reasoning
            reasoning_path = job_dir / "ai_reasoning.txt"
            with open(reasoning_path, "w") as f:
                f.write(result.reasoning or "No reasoning extracted.")
                
            # Create ZIP
            from app.export.zip_packager import create_download_zip
            files_to_zip = {
                "body_stl": result.stl_path,
                "scad": result.scad_path,
                "thermal_report": str(thermal_path),
                "reasoning_txt": str(reasoning_path)
            }
            zip_path = create_download_zip(job_id, files_to_zip, GENERATED_FILES_DIR)

            # ── Step 7: Success ──
            yield _sse_event({
                "event": "complete",
                "job_id": job_id,
                "attempts": result.attempts,
                "render_time_ms": result.render_time_ms,
                "stl_path": result.stl_path,
                "scad_path": result.scad_path,
                "zip_path": zip_path,
                "reasoning": result.reasoning,
                "thermal": thermal.__dict__,
                "strategy": strategy.name,
            })

        except GenerationFailedException as e:
            yield _sse_event({
                "event": "error",
                "job_id": job_id,
                "message": f"Generation failed after {e.attempts} attempts: {e.last_error}",
            })
        except Exception as e:
            logger.error(f"Generation error for job {job_id}: {e}", exc_info=True)
            yield _sse_event({
                "event": "error",
                "job_id": job_id,
                "message": str(e),
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
