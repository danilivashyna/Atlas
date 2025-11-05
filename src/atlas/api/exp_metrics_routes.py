"""
Experimental Metrics API Routes (Phase B.3)

FastAPI endpoint для Prometheus metrics экспорта.
Изолирован от основного API, активируется флагом AURIS_METRICS_EXP=on.

Endpoints:
- GET /metrics/exp - Prometheus metrics (text format)
- GET /metrics/exp/health - Health check

Usage:
    from atlas.api.exp_metrics_routes import router as exp_metrics_router

    app.include_router(exp_metrics_router, prefix="/metrics/exp")
"""

import os
from fastapi import APIRouter, Response, HTTPException
from src.atlas.metrics.exp_prom_exporter import (
    is_enabled,
    get_metrics_text,
    setup_prometheus_metrics,
)

# Feature flag check
METRICS_ENABLED = os.getenv("AURIS_METRICS_EXP", "off").lower() in (
    "on",
    "true",
    "1",
)

# Router
router = APIRouter(
    prefix="",
    tags=["experimental-metrics"],
)


@router.on_event("startup")
async def startup_metrics():
    """Initialize Prometheus metrics on startup"""
    if METRICS_ENABLED:
        setup_prometheus_metrics()


@router.get("/", response_class=Response)
async def get_prometheus_metrics():
    """
    Get Prometheus metrics in text exposition format.

    Returns:
        Response: Prometheus metrics (text/plain)

    Raises:
        HTTPException: 503 if metrics disabled
    """
    if not is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Metrics disabled (set AURIS_METRICS_EXP=on to enable)",
        )

    metrics_text = get_metrics_text()

    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/health")
async def metrics_health():
    """
    Health check for metrics endpoint.

    Returns:
        dict: Status and configuration
    """
    return {
        "status": "enabled" if is_enabled() else "disabled",
        "feature_flag": "AURIS_METRICS_EXP",
        "flag_value": os.getenv("AURIS_METRICS_EXP", "off"),
        "endpoint": "/metrics/exp" if is_enabled() else None,
    }
