
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "endpoint"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        start_time = time.perf_counter()

        method = request.method
        endpoint = request.scope.get("route")

        endpoint = (
            endpoint.path
            if endpoint is not None
            else "unmatched"
        )

        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        finally:
            duration = time.perf_counter() - start_time

            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()


def setup_metrics(app: FastAPI):

    app.add_middleware(PrometheusMiddleware)

    @app.get("/TrhBVe_m5gg2005_E5VVqS", include_in_schema=False)
    def metrics():

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
