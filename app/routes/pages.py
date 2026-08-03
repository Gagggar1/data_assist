from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.deps import (
    get_analysis_service,
    get_chart_service,
    get_chat_service,
    get_file_service,
    render_page,
)
from app.core.security import verify_api_key
from app.services.analysis_service import AnalysisService
from app.services.chart_service import ChartService
from app.services.chat_service import ChatNotFoundError, ChatService
from app.services.file_service import FileService

router = APIRouter()


@router.get("/")
async def index(request: Request, chat_service: ChatService = Depends(get_chat_service)):
    verify_api_key(request)
    conversation = chat_service.create_conversation()
    return RedirectResponse(url=f"/chat/{conversation['conversation_id']}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/chat/{conversation_id}")
async def chat_page(
    request: Request,
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    verify_api_key(request)
    try:
        conversation = chat_service.get_conversation(conversation_id)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден.") from exc

    return render_page(
        request,
        "chat.html",
        "partials/chat_shell.html",
        chat_service.build_page_context(request, conversation),
    )


@router.get("/preview/{file_id}")
async def preview_page(
    request: Request,
    file_id: str,
    file_service: FileService = Depends(get_file_service),
):
    verify_api_key(request)
    stored_file = file_service.get_file(file_id)
    preview_context = file_service.build_preview_context(stored_file)
    artifacts = file_service.get_output_artifacts(file_id)
    return render_page(
        request,
        "preview.html",
        "partials/preview_content.html",
        {
            "request": request,
            "page_title": f"Preview | {stored_file.original_name}",
            "preview": preview_context,
            "artifacts": artifacts,
            "analysis": None,
            "error_message": None,
            "success_message": "Файл загружен. Можно запускать анализ и строить графики.",
        },
    )


@router.get("/results/{file_id}")
async def result_page(
    request: Request,
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    chart_service: ChartService = Depends(get_chart_service),
):
    verify_api_key(request)
    stored_file = file_service.get_file(file_id)
    preview_context = file_service.build_preview_context(stored_file)
    analysis = analysis_service.analyze(stored_file)
    artifacts = file_service.get_output_artifacts(file_id)
    if not artifacts["charts"]:
        chart_service.generate_default_charts(stored_file)
        artifacts = file_service.get_output_artifacts(file_id)

    return render_page(
        request,
        "result.html",
        "partials/result_page_content.html",
        {
            "request": request,
            "page_title": f"Results | {stored_file.original_name}",
            "preview": preview_context,
            "analysis": analysis,
            "artifacts": artifacts,
            "error_message": None,
            "success_message": "Собран актуальный аналитический срез по файлу.",
        },
    )
