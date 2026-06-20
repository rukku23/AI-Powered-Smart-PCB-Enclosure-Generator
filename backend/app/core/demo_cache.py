"""
EnclosureAI — Demo Cache
Pre-generated outputs for preset boards for hackathon demo resilience.
If USE_DEMO_CACHE=true and request matches a preset, return cached output
with simulated SSE streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("enclosureai.core.demo_cache")

DEMO_CACHE_DIR = Path(__file__).parent.parent.parent / "demo_cache"

# Preset mappings
PRESET_CACHE_MAP = {
    "ESP32": "esp32",
    "ARDUINO_UNO": "arduino_uno",
    "RPI4": "rpi4",
}


def is_demo_cache_enabled() -> bool:
    """Check if demo cache mode is active."""
    return os.getenv("USE_DEMO_CACHE", "false").lower() in ("true", "1", "yes")


def get_cached_preset(preset: Optional[str]) -> Optional[str]:
    """
    Check if a preset has a cached demo output.
    Returns the cache directory name, or None.
    """
    if not preset or not is_demo_cache_enabled():
        return None

    cache_key = PRESET_CACHE_MAP.get(preset)
    if not cache_key:
        return None

    cache_dir = DEMO_CACHE_DIR / cache_key
    if cache_dir.exists() and any(cache_dir.iterdir()):
        return cache_key

    return None


def copy_cached_output(cache_key: str, job_id: str, output_dir: str) -> dict:
    """
    Copy cached files to the job output directory.
    Returns file paths dict.
    """
    src_dir = DEMO_CACHE_DIR / cache_key
    dst_dir = Path(output_dir) / job_id
    dst_dir.mkdir(parents=True, exist_ok=True)

    files = {}
    for src_file in src_dir.iterdir():
        if src_file.is_file():
            dst_file = dst_dir / src_file.name
            shutil.copy2(str(src_file), str(dst_file))
            files[src_file.stem] = str(dst_file)

    logger.info(f"Copied {len(files)} cached files for preset '{cache_key}' to {dst_dir}")
    return files


async def stream_cached_response(cache_key: str, job_id: str, output_dir: str):
    """
    Generator that yields simulated SSE events with artificial delays.
    Mimics the real generation pipeline for demo purposes.
    """
    def sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    # Load cached thermal report if available
    thermal_report = {}
    thermal_path = DEMO_CACHE_DIR / cache_key / "thermal_report.json"
    if thermal_path.exists():
        try:
            thermal_report = json.loads(thermal_path.read_text())
        except Exception:
            pass

    # Load cached reasoning if available
    reasoning = ""
    reasoning_path = DEMO_CACHE_DIR / cache_key / "ai_reasoning.txt"
    if reasoning_path.exists():
        try:
            reasoning = reasoning_path.read_text()
        except Exception:
            pass

    # Simulated SSE event stream (3-second total)
    yield sse({"event": "validating", "job_id": job_id})
    await asyncio.sleep(0.3)

    yield sse({
        "event": "constraints_computed", "job_id": job_id,
        "enclosure": {"note": "from demo cache"},
    })
    await asyncio.sleep(0.2)

    yield sse({"event": "dfm_result", "job_id": job_id, "passed": True, "warnings": []})
    await asyncio.sleep(0.2)

    yield sse({"event": "thermal_computed", "job_id": job_id, "thermal": thermal_report})
    await asyncio.sleep(0.3)

    yield sse({"event": "generating", "job_id": job_id, "attempt": 1})
    await asyncio.sleep(0.5)

    # Stream reasoning in chunks
    if reasoning:
        chunk_size = max(len(reasoning) // 5, 50)
        for i in range(0, len(reasoning), chunk_size):
            chunk = reasoning[i:i + chunk_size]
            yield sse({"event": "reasoning_chunk", "data": chunk})
            await asyncio.sleep(0.15)

    yield sse({"event": "rendering", "job_id": job_id, "attempt": 1})
    await asyncio.sleep(0.5)

    # Copy cached files to output
    copy_cached_output(cache_key, job_id, output_dir)

    yield sse({
        "event": "complete",
        "job_id": job_id,
        "attempts": 1,
        "render_time_ms": 1200,
        "reasoning": reasoning,
        "thermal": thermal_report,
        "stl_path": str(Path(output_dir) / job_id / "enclosure.stl"),
        "scad_path": str(Path(output_dir) / job_id / "enclosure.scad"),
    })


def init_demo_cache():
    """
    Create demo cache directory structure.
    Called once to set up directories for manual population.
    """
    for key in PRESET_CACHE_MAP.values():
        cache_dir = DEMO_CACHE_DIR / key
        cache_dir.mkdir(parents=True, exist_ok=True)
        readme = cache_dir / "README.txt"
        if not readme.exists():
            readme.write_text(
                f"Place pre-generated files here for the {key} preset demo cache.\n"
                "Expected files: enclosure.scad, enclosure.stl, thermal_report.json, "
                "bom.csv, ai_reasoning.txt\n"
            )
    logger.info(f"Demo cache initialized at {DEMO_CACHE_DIR}")
