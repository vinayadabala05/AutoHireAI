"""Basic application metrics — request counts, latency, uptime, error rate.

No new dependency: a small in-process registry plus a hand-written
Prometheus text-exposition writer, since a handful of counters/gauges
doesn't justify pulling in `prometheus-client`. `MetricsMiddleware`
records every request; `render_prometheus_text()` formats the current
snapshot for a `/metrics` scrape.
"""

import time
from dataclasses import dataclass
from threading import Lock

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


@dataclass
class MetricsSnapshot:
    started_at: float
    requests_total: int
    requests_by_path: dict[str, int]
    errors_total: int
    total_latency_seconds: float

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def average_latency_seconds(self) -> float:
        return self.total_latency_seconds / self.requests_total if self.requests_total else 0.0


class MetricsRegistry:
    """Thread-safe counters, incremented by `MetricsMiddleware` on every request."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.monotonic()
        self._requests_total = 0
        self._requests_by_path: dict[str, int] = {}
        self._errors_total = 0
        self._total_latency_seconds = 0.0

    def record_request(self, path: str, status_code: int, latency_seconds: float) -> None:
        with self._lock:
            self._requests_total += 1
            self._requests_by_path[path] = self._requests_by_path.get(path, 0) + 1
            self._total_latency_seconds += latency_seconds
            if status_code >= 500:
                self._errors_total += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                started_at=self._started_at,
                requests_total=self._requests_total,
                requests_by_path=dict(self._requests_by_path),
                errors_total=self._errors_total,
                total_latency_seconds=self._total_latency_seconds,
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, registry: MetricsRegistry) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._registry = registry

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.monotonic()
        response = await call_next(request)
        self._registry.record_request(
            request.url.path, response.status_code, time.monotonic() - started
        )
        return response


def render_prometheus_text(snapshot: MetricsSnapshot) -> str:
    """Render `snapshot` in Prometheus text-exposition format."""
    lines = [
        "# HELP autohire_uptime_seconds Process uptime in seconds.",
        "# TYPE autohire_uptime_seconds gauge",
        f"autohire_uptime_seconds {snapshot.uptime_seconds:.3f}",
        "# HELP autohire_requests_total Total HTTP requests handled.",
        "# TYPE autohire_requests_total counter",
        f"autohire_requests_total {snapshot.requests_total}",
        "# HELP autohire_errors_total Total HTTP requests that returned a 5xx status.",
        "# TYPE autohire_errors_total counter",
        f"autohire_errors_total {snapshot.errors_total}",
        "# HELP autohire_request_latency_seconds_avg Average request latency in seconds.",
        "# TYPE autohire_request_latency_seconds_avg gauge",
        f"autohire_request_latency_seconds_avg {snapshot.average_latency_seconds:.6f}",
        "# HELP autohire_requests_by_path_total Total requests handled per path.",
        "# TYPE autohire_requests_by_path_total counter",
    ]
    for path, count in sorted(snapshot.requests_by_path.items()):
        lines.append(f'autohire_requests_by_path_total{{path="{path}"}} {count}')
    return "\n".join(lines) + "\n"


def build_metrics_router(registry: MetricsRegistry) -> APIRouter:
    """Build a fresh `/metrics` `APIRouter` bound to `registry` (see `health.build_readiness_router`
    for why each call returns a new router rather than mutating a shared one)."""
    router = APIRouter(tags=["metrics"])

    @router.get("/metrics")
    async def metrics() -> Response:
        body = render_prometheus_text(registry.snapshot())
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return router
