import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.services import model_service

router = APIRouter()


@router.post("/api/inspect")
async def inspect(
    file: UploadFile = File(...),
    activation_threshold: float = Query(0.5, ge=0.1, le=0.95),
):
    content = await file.read()
    try:
        result = model_service.inspect(content, activation_threshold=activation_threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["part_id"] = f"P-{uuid.uuid4().hex[:12]}"
    result["data_provenance"] = "ORGANIZER_DATASET"
    return result
