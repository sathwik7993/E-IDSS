from typing import Dict

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import telemetry_service

router = APIRouter()


class AttributionRequest(BaseModel):
    telemetry: Dict[str, float]


@router.get("/api/telemetry/specs")
def telemetry_specs():
    from ai.telemetry import (
        DEFECT_TELEMETRY_PROFILES,
        FEATURE_COLS,
        NOMINAL_TELEMETRY,
        PRESET_UNITS,
        TELEMETRY_SPECS,
    )

    bundle = telemetry_service.get_bundle()
    return {
        "feature_cols": FEATURE_COLS,
        "specs": TELEMETRY_SPECS,
        "nominal": NOMINAL_TELEMETRY,
        "presets": PRESET_UNITS,
        "defect_profiles": DEFECT_TELEMETRY_PROFILES,
        "model_test_accuracy": bundle["test_accuracy"],
        "n_training_rows": bundle["n_training_rows"],
        "data_provenance": "SYNTHETIC_DEMONSTRATION",
    }


@router.post("/api/telemetry/attribution")
def telemetry_attribution(request: AttributionRequest):
    from ai.telemetry import explain_unit

    return explain_unit(request.telemetry, bundle=telemetry_service.get_bundle())


@router.get("/api/line/health")
def line_health():
    from ai.telemetry import line_health as build_line_health

    return build_line_health()


@router.get("/api/line/financial")
def line_financial(
    daily_units: int = Query(2400, ge=1),
    defect_rate_pct: float = Query(3.8, ge=0.0, le=100.0),
    scrap_cost_per_unit: float = Query(92.40, ge=0.0),
):
    from ai.telemetry import financial_impact

    return financial_impact(daily_units, defect_rate_pct, scrap_cost_per_unit)
