from fastapi import APIRouter

from app.services import model_service

router = APIRouter()


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_service.is_loaded(),
        "stub_mode": model_service.is_stub(),
        "device": model_service.device_str(),
    }
