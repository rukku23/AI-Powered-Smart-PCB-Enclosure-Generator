"""
EnclosureAI — Output Schemas
Pydantic models for API responses and generation results.

Implementation: Phase 3-4
"""

from pydantic import BaseModel
from typing import Optional


class GenerationResult(BaseModel):
    """Result of a successful enclosure generation."""
    job_id: str
    scad_code: str = ""
    stl_path: str = ""
    scad_path: str = ""
    reasoning: str = ""
    attempts: int = 1
    render_time_ms: int = 0


class ThermalReport(BaseModel):
    """Thermal analysis results."""
    thermal_health_score: int = 0
    verdict: str = ""
    vent_area_required_cm2: float = 0.0
    vent_area_recommended_cm2: float = 0.0
    airflow_direction: str = "TOP_OUTLET_BOTTOM_INLET"
    passive_cooling_sufficient: bool = True
    hotspot_summary: str = ""
    recommendation: str = ""


class ErrorResponse(BaseModel):
    """Structured error response."""
    error: str
    detail: str = ""
    field: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    openscad_available: bool = False
