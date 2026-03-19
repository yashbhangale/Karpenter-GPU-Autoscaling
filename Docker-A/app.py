import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Deque

from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response


SERVICE_NAME = "docker-a"

# Core request metrics (useful for dashboards/debugging; HPA can ignore these).
HTTP_REQUESTS_TOTAL = Counter(
    "fastapi_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "fastapi_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "endpoint"],
)
HTTP_REQUESTS_ACTIVE = Gauge(
    "fastapi_http_requests_active",
    "Active HTTP requests",
)

# This is the metric referenced by your HPA.
# It is computed as "number of requests observed in the last 60 seconds".
HTTP_REQUESTS_PER_MINUTE = Gauge(
    "fastapi_http_requests_per_minute",
    "Requests per minute (rolling 60s window)",
)

_request_timestamps_seconds: Deque[float] = deque()


async def _update_requests_per_minute_loop() -> None:
    while True:
        now_seconds = time.time()
        cutoff_seconds = now_seconds - 60.0
        while _request_timestamps_seconds and _request_timestamps_seconds[0] < cutoff_seconds:
            _request_timestamps_seconds.popleft()
        HTTP_REQUESTS_PER_MINUTE.set(len(_request_timestamps_seconds))
        await asyncio.sleep(1)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    updater_task = asyncio.create_task(_update_requests_per_minute_loop())
    try:
        yield
    finally:
        updater_task.cancel()
        try:
            await updater_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Demo Docker A - Status API", lifespan=_lifespan)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):  # type: ignore[override]
    start_seconds = time.time()
    HTTP_REQUESTS_ACTIVE.inc()
    try:
        response = await call_next(request)
        duration_seconds = time.time() - start_seconds

        endpoint = request.url.path
        method = request.method
        status_code = str(getattr(response, "status_code", 500))

        HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            service=SERVICE_NAME,
            method=method,
            endpoint=endpoint,
        ).observe(duration_seconds)

        # Count user traffic for autoscaling; exclude scraping/health noise.
        if endpoint not in {"/metrics", "/health", "/favicon.ico"}:
            _request_timestamps_seconds.append(time.time())

        return response
    finally:
        HTTP_REQUESTS_ACTIVE.dec()


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    return {
        "service": SERVICE_NAME,
        "description": "Demo service A - simple status API.",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    return {
        "service": SERVICE_NAME,
        "status": "running",
        "details": "This is a demo version of service A without any ML models.",
    }

