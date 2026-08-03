from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.core.deps import get_chat_service, render_chat_update, render_page
from app.core.security import verify_api_key
from app.services.chat_service import ChatNotFoundError, ChatService

router = APIRouter()


@router.post("/chat/{conversation_id}/message")
async def send_message(
    request: Request,
    conversation_id: str,
    message_text: str = Form(default=""),
    data_file: UploadFile | None = File(default=None),
    chat_service: ChatService = Depends(get_chat_service),
):
    verify_api_key(request)
    try:
        conversation = await chat_service.process_turn(conversation_id, message_text, data_file)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден.") from exc

    context = chat_service.build_page_context(request, conversation)
    if request.headers.get("HX-Request") == "true":
        return render_chat_update(request, context)
    return render_page(request, "chat.html", "partials/chat_shell.html", context)


@router.post("/chat/{conversation_id}/activate/{file_id}")
async def activate_file(
    request: Request,
    conversation_id: str,
    file_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    verify_api_key(request)
    try:
        conversation = chat_service.activate_file(conversation_id, file_id)
    except ChatNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден.") from exc

    context = chat_service.build_page_context(request, conversation)
    if request.headers.get("HX-Request") == "true":
        return render_chat_update(request, context)
    return render_page(request, "chat.html", "partials/chat_shell.html", context)
