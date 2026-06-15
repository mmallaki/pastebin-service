"""Prometheus metrics middleware — tracks request count and latency."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

from app.core import settings

if settings.PROMETHEUS_ENABLED:
    from prometheus_client import Counter, Histogram

    REQUEST_COUNT = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code']
    )

    REQUEST_LATENCY = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency',
        ['method', 'endpoint']
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects request count and latency for Prometheus monitoring."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        if settings.PROMETHEUS_ENABLED:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)

        return response
