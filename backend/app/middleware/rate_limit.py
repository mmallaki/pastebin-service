from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from datetime import datetime, timezone

from app.core.database import redis_client
from app.core import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        client_ip = request.client.host
        now = datetime.now(timezone.utc)

        minute_key = f"rate_limit:{client_ip}:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate_limit:{client_ip}:{now.strftime('%Y%m%d%H')}"

        pipe = redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        results = await pipe.execute()

        minute_count = results[0]
        hour_count = results[2]

        if minute_count > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                }
            )

        if hour_count > settings.RATE_LIMIT_PER_HOUR:
            return JSONResponse(
                status_code=429,
                content={"detail": "Hourly rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": "3600",
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Remaining": "0",
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(
            settings.RATE_LIMIT_PER_MINUTE - minute_count
        )
        return response
