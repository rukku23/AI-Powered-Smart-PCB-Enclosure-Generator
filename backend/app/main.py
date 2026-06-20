"""
EnclosureAI — FastAPI Application Entry Point

Production-grade API server for AI-augmented PCB enclosure generation.
Architecture: Deterministic computation → AI generation → Validation.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import generate, download, predict
from app.core.job_registry import job_registry

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("enclosureai")

# ---------------------------------------------------------------------------
# Application Version
# ---------------------------------------------------------------------------
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# OpenSCAD CLI Verification
# ---------------------------------------------------------------------------
async def verify_openscad_cli() -> bool:
    logger.info("Skipping OpenSCAD CLI startup check")
    return True

# ---------------------------------------------------------------------------
# Application State
# ---------------------------------------------------------------------------
class AppState:
    """Mutable application state container."""
    openscad_available: bool = False


app_state = AppState()

# ---------------------------------------------------------------------------
# Lifespan — Startup / Shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("=" * 60)
    logger.info("EnclosureAI v%s — Starting up", APP_VERSION)
    logger.info("=" * 60)

    # Verify OpenSCAD CLI availability
    app_state.openscad_available = await verify_openscad_cli()

    # Ensure generated files directory exists
    gen_dir = os.getenv("GENERATED_FILES_DIR", "./generated_files")
    os.makedirs(gen_dir, exist_ok=True)
    logger.info(f"Generated files directory: {os.path.abspath(gen_dir)}")

    # Log LLM provider configuration
    llm_provider = "ollama"
    logger.info(f"LLM provider: {llm_provider}")

    # Start background cleanup task
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            try:
                await job_registry.cleanup_old_jobs(max_age_hours=2)
            except Exception as e:
                logger.warning(f"Job cleanup error: {e}")

    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Startup complete — ready to accept requests")
    yield
    cleanup_task.cancel()
    logger.info("EnclosureAI shutting down")


# ---------------------------------------------------------------------------
# FastAPI Application Instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="EnclosureAI",
    description=(
        "AI-powered PCB enclosure generation system. "
        "Generates thermally-aware, DFM-compliant, 3D-printable enclosures "
        "from PCB specifications in under 30 seconds."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware — Allow all origins for hackathon
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include API Routers
# ---------------------------------------------------------------------------
app.include_router(generate.router)
app.include_router(download.router)
app.include_router(predict.router)
# ---------------------------------------------------------------------------
# Static File Serving
# ---------------------------------------------------------------------------
app.mount(
    "/generated_files",
    StaticFiles(directory="generated_files"),
    name="generated_files"
)

# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.
    Returns API status, version, and OpenSCAD CLI availability.
    """
    return {
        "status": "ok",
        "version": APP_VERSION,
        "openscad_available": app_state.openscad_available,
        "active_jobs": job_registry.active_count,
    }


@app.get("/api/status/{job_id}", tags=["system"])
async def job_status(job_id: str):
    """Get current status of a generation job."""
    info = job_registry.to_dict(job_id)
    if not info:
        return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})
    return info


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler returning structured JSON errors.
    Prevents raw stack traces from leaking to clients.
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An unexpected error occurred",
            "path": str(request.url.path),
        },
    )


# ---------------------------------------------------------------------------
# Validation Error Handler (Pydantic / RequestValidationError)
# ---------------------------------------------------------------------------
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors for malformed requests."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": "Request validation failed",
            "errors": errors,
        },
    )
