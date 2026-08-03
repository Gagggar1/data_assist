from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = 30) -> None:
        super().__init__(app)
        self.limit_per_minute = max(limit_per_minute, 1)
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(("/health", "/ready", "/static", "/storage")):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self.hits[client]
        while window and now - window[0] > 60:
            window.popleft()

        if len(window) >= self.limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Слишком много запросов. Попробуйте позже."},
            )

        window.append(now)
        return await call_next(request)
