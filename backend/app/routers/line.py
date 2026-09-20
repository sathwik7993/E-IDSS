from fastapi import APIRouter

from app.services import plant_service

router = APIRouter()


@router.get("/api/line/state")
def line_state():
    return plant_service.get_plant().line_state()


@router.get("/api/line/recommendation")
def line_recommendation(defect_rate: float = 0.08):
    from ai.synthetic import bottleneck_recommendation

    state = plant_service.get_plant().line_state()
    return bottleneck_recommendation(state, defect_rate=defect_rate)
