from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.deps import get_cleanup_service
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.db.database import init_db
from app.routes.actions import router as actions_router
from app.routes.api import router as api_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.pages import router as pages_router
from app.routes.upload import router as upload_router
from app.services.file_service import FileService

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_db(settings)
    FileService(settings).ensure_storage()
    get_cleanup_service().cleanup_expired_files()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
app.add_middleware(RequestContextMiddleware)

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(actions_router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
