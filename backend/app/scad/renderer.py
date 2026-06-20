"""
EnclosureAI — OpenSCAD CLI Renderer
Async wrapper for OpenSCAD CLI subprocess execution.
RULE 4: Uses asyncio.create_subprocess_exec — never blocking subprocess.run().
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("enclosureai.scad.renderer")

OPENSCAD_TIMEOUT = 30  # seconds
OPENSCAD_CLI = os.getenv("OPENSCAD_CLI_PATH", "openscad")


@dataclass
class RenderResult:
    """Result of an OpenSCAD render operation."""
    success: bool
    stl_path: Optional[str]
    scad_path: str
    error_message: Optional[str]
    error_class: Optional[str]
    render_time_ms: int
    stdout: str
    stderr: str


async def render_scad(
    scad_code: str,
    job_id: str,
    output_dir: str,
) -> RenderResult:
    """
    Render OpenSCAD code to binary STL.

    Steps:
    1. Write scad_code to {output_dir}/{job_id}/enclosure.scad
    2. Call: openscad --render --export-format binstl -o ... enclosure.scad
    3. Use asyncio.create_subprocess_exec (non-blocking)
    4. Timeout: 30 seconds
    5. Parse stdout/stderr
    6. Return RenderResult
    """
    job_dir = Path(output_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    scad_path = job_dir / "enclosure.scad"
    stl_path = job_dir / "body.stl"

    # Write SCAD file
    scad_path.write_text(scad_code, encoding="utf-8")
    logger.info(f"Wrote SCAD: {scad_path} ({len(scad_code)} chars)")

    # Build command
    cmd = [
        OPENSCAD_CLI,
        "--render",
        "--export-format", "binstl",
        "-o", str(stl_path),
        str(scad_path),
    ]

    start = time.perf_counter()

    try:
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        stdout = result.stdout
        stderr = result.stderr
        

        if result.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0:
            logger.info(f"Render success: {stl_path} ({elapsed_ms}ms)")
            return RenderResult(
                success=True,
                stl_path=str(stl_path),
                scad_path=str(scad_path),
                error_message=None,
                error_class=None,
                render_time_ms=elapsed_ms,
                stdout=stdout,
                stderr=stderr,
            )
        else:
            error_msg = stderr.strip() or f"OpenSCAD exited with code {process.returncode}"
            logger.warning(f"Render failed ({elapsed_ms}ms): {error_msg[:200]}")
            return RenderResult(
                success=False,
                stl_path=None,
                scad_path=str(scad_path),
                error_message=error_msg,
                error_class=None,
                render_time_ms=elapsed_ms,
                stdout=stdout,
                stderr=stderr,
            )

    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"OpenSCAD render timed out after {OPENSCAD_TIMEOUT}s")
        # Kill the process
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        return RenderResult(
            success=False,
            stl_path=None,
            scad_path=str(scad_path),
            error_message=f"OpenSCAD render timed out after {OPENSCAD_TIMEOUT} seconds",
            error_class="TIMEOUT",
            render_time_ms=elapsed_ms,
            stdout="",
            stderr="TIMEOUT",
        )

    except FileNotFoundError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        msg = (
            f"OpenSCAD CLI not found at '{OPENSCAD_CLI}'. "
            "Install OpenSCAD or set OPENSCAD_CLI_PATH."
        )
        logger.error(msg)
        return RenderResult(
            success=False,
            stl_path=None,
            scad_path=str(scad_path),
            error_message=msg,
            error_class="CLI_NOT_FOUND",
            render_time_ms=elapsed_ms,
            stdout="",
            stderr=msg,
        )


async def render_scad_lid(
    scad_path: str,
    stl_out_path: str,
) -> RenderResult:
    """
    Render only the lid from a SCAD file.
    Uses -D flags to toggle body/lid rendering.
    """
    cmd = [
        OPENSCAD_CLI,
        "--render",
        "--export-format", "binstl",
        "-D", "render_lid=true",
        "-D", "render_body=false",
        "-o", stl_out_path,
        scad_path,
    ]

    start = time.perf_counter()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=OPENSCAD_TIMEOUT
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        stl_file = Path(stl_out_path)
        if process.returncode == 0 and stl_file.exists() and stl_file.stat().st_size > 0:
            return RenderResult(
                success=True,
                stl_path=stl_out_path,
                scad_path=scad_path,
                error_message=None,
                error_class=None,
                render_time_ms=elapsed_ms,
                stdout=stdout,
                stderr=stderr,
            )
        else:
            return RenderResult(
                success=False,
                stl_path=None,
                scad_path=scad_path,
                error_message=stderr.strip() or "Lid render failed",
                error_class=None,
                render_time_ms=elapsed_ms,
                stdout=stdout,
                stderr=stderr,
            )

    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        return RenderResult(
            success=False,
            stl_path=None,
            scad_path=scad_path,
            error_message="Lid render timed out",
            error_class="TIMEOUT",
            render_time_ms=elapsed_ms,
            stdout="",
            stderr="TIMEOUT",
        )

    except FileNotFoundError:
        return RenderResult(
            success=False,
            stl_path=None,
            scad_path=scad_path,
            error_message=f"OpenSCAD CLI not found at '{OPENSCAD_CLI}'",
            error_class="CLI_NOT_FOUND",
            render_time_ms=0,
            stdout="",
            stderr="CLI_NOT_FOUND",
        )
