from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.deps import get_cleanup_service, get_file_service
from app.services.file_service import FileService
from app.services.storage_cleanup import StorageCleanupService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    file_service: FileService = Depends(get_file_service),
    cleanup_service: StorageCleanupService = Depends(get_cleanup_service),
) -> dict[str, str | int]:
    settings = get_settings()
    file_service.ensure_storage()
    cleanup_counts = cleanup_service.cleanup_expired_files()
    return {
        "status": "ready",
        "app": settings.app_name,
        "llm_provider": settings.llm_provider,
        "cleanup": sum(cleanup_counts.values()),
    }
