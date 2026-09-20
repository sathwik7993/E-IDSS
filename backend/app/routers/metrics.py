from fastapi import APIRouter

from app.services import model_service

router = APIRouter()


@router.get("/api/metrics")
def metrics():
    return model_service.metrics()
