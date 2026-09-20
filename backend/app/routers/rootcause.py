from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import rootcause_service

router = APIRouter()


class RootCauseRequest(BaseModel):
    defect_class: str
    observation: Optional[Dict[str, float]] = None


@router.post("/api/rootcause")
def rootcause(request: RootCauseRequest):
    from ai.data import CLASSES

    if request.defect_class not in CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown defect_class {request.defect_class!r}; expected one of {CLASSES}",
        )

    engine = rootcause_service.get_engine()
    observation = request.observation or {}
    return engine.attribute(observation, request.defect_class)


@router.get("/api/rootcause/validation")
def rootcause_validation():
    return rootcause_service.get_validation()


@router.get("/api/drift/{batch_id}")
def drift(batch_id: str):
    engine = rootcause_service.get_engine()
    return engine.detect_drift(batch_id)
