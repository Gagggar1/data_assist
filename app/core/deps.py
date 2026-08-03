from __future__ import annotations

from functools import lru_cache

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import Settings, get_settings
from app.core.security import build_download_url
from app.repositories.chat_repository import ChatRepository
from app.services.ai_service import AIService
from app.services.analysis_service import AnalysisService
from app.services.chart_service import ChartService
from app.services.chat_service import ChatService
from app.services.export_service import ExportService
from app.services.file_service import FileService
from app.services.report_service import ReportService
from app.services.storage_cleanup import StorageCleanupService


@lru_cache
def get_settings_cached() -> Settings:
    return get_settings()


def get_templates() -> Jinja2Templates:
    settings = get_settings_cached()
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["download_url_for"] = lambda name: build_download_url(name, settings)
    return templates


def get_file_service() -> FileService:
    return FileService(get_settings_cached())


def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_file_service())


def get_chart_service() -> ChartService:
    return ChartService(get_file_service(), get_settings_cached())


def get_report_service() -> ReportService:
    return ReportService(get_file_service(), get_settings_cached())


def get_export_service() -> ExportService:
    return ExportService(get_settings_cached())


def get_ai_service() -> AIService:
    return AIService(get_settings_cached())


def get_chat_repository() -> ChatRepository:
    return ChatRepository()


def get_chat_service() -> ChatService:
    return ChatService(
        file_service=get_file_service(),
        analysis_service=get_analysis_service(),
        chart_service=get_chart_service(),
        report_service=get_report_service(),
        export_service=get_export_service(),
        ai_service=get_ai_service(),
        chat_repository=get_chat_repository(),
        settings=get_settings_cached(),
    )


def get_cleanup_service() -> StorageCleanupService:
    return StorageCleanupService(get_settings_cached())


def render_page(request: Request, template_name: str, partial_name: str, context: dict):
    templates = get_templates()
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(partial_name, context)
    return templates.TemplateResponse(template_name, context)


def render_chat_update(request: Request, context: dict):
    templates = get_templates()
    return templates.TemplateResponse("partials/chat_update.html", {**context, "request": request})
