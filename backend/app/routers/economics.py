from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CounterfactualRequest(BaseModel):
    defect_rate: float
    throughput: float
    speed_delta_pct: float
    defect_rate_delta_pct: float


@router.get("/api/economics")
def economics(defect_rate: float, throughput: float):
    from ai.synthetic import unit_economics

    return unit_economics(defect_rate, throughput)


@router.post("/api/economics/counterfactual")
def economics_counterfactual(request: CounterfactualRequest):
    from ai.synthetic import counterfactual

    return counterfactual(
        request.defect_rate,
        request.throughput,
        request.speed_delta_pct,
        request.defect_rate_delta_pct,
    )


@router.get("/api/economics/recommendation")
def economics_recommendation(defect_rate: float, throughput: float):
    from ai.synthetic import best_counterfactual

    return best_counterfactual(defect_rate, throughput)
