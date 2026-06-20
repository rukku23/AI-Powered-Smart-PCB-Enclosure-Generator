"""
EnclosureAI — Strategy Prediction Endpoint (Phase 8)
GET /api/predict-strategy — lightweight strategy prediction without generation.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.core.design_context import (
    DesignContext,
    UseCase,
    AccessFrequency,
    MountingStyle,
    Environment,
)
from app.core.strategy_selector import DesignStrategySelector

logger = logging.getLogger("enclosureai.routers.predict")
router = APIRouter(prefix="/api", tags=["prediction"])

_selector = DesignStrategySelector()


@router.get("/predict-strategy")
async def predict_strategy(
    use_case: str = Query("BENCH_PROTOTYPE"),
    access_frequency: str = Query("RARELY"),
    mounting: str = Query("DESKTOP"),
    environment: str = Query("INDOOR"),
    total_wattage: float = Query(0.0),
):
    """
    Predict which strategy would be selected for the given design context.
    Lightweight — no LLM call, no constraint computation for override checks.
    Used by frontend for real-time strategy preview.
    """
    try:
        ctx = DesignContext(
            use_case=UseCase(use_case),
            access_frequency=AccessFrequency(access_frequency),
            mounting=MountingStyle(mounting),
            environment=Environment(environment),
        )
    except ValueError:
        ctx = DesignContext()

    # Create a minimal mock constraints object for wattage check
    class _MinimalConstraints:
        def __init__(self, wattage):
            self.total_wattage = wattage

    constraints = _MinimalConstraints(total_wattage) if total_wattage > 0 else None
    result = _selector.select(ctx, constraints)

    return {
        "strategy": result.strategy.topology_name,
        "display_name": result.strategy.display_name,
        "score": round(result.score, 1),
        "reason": result.reason,
        "closure_mechanism": result.strategy.closure_mechanism,
        "vent_architecture": result.strategy.vent_architecture,
        "piece_count": result.strategy.piece_count,
    }
