from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_analysis_service, get_file_service
from app.core.security import verify_api_key
from app.services.analysis_service import AnalysisService
from app.services.file_service import FileReadError, FileService

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.get("/analyze/{file_id}")
async def analyze_file(
    request: Request,
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> dict:
    verify_api_key(request)
    try:
        stored_file = file_service.get_file(file_id)
        return analysis_service.analyze(stored_file)
    except FileReadError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
