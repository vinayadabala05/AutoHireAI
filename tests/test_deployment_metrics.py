"""Unit tests for `deployment.metrics`."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from deployment.metrics import (
    MetricsMiddleware,
    MetricsRegistry,
    build_metrics_router,
    render_prometheus_text,
)


def test_registry_records_request_counts_and_paths() -> None:
    registry = MetricsRegistry()
    registry.record_request("/foo", 200, 0.1)
    registry.record_request("/foo", 200, 0.2)
    registry.record_request("/bar", 500, 0.05)

    snapshot = registry.snapshot()
    assert snapshot.requests_total == 3
    assert snapshot.requests_by_path == {"/foo": 2, "/bar": 1}
    assert snapshot.errors_total == 1


def test_snapshot_average_latency() -> None:
    registry = MetricsRegistry()
    registry.record_request("/foo", 200, 0.1)
    registry.record_request("/foo", 200, 0.3)

    assert registry.snapshot().average_latency_seconds == 0.2


def test_snapshot_average_latency_is_zero_with_no_requests() -> None:
    assert MetricsRegistry().snapshot().average_latency_seconds == 0.0


def test_render_prometheus_text_includes_all_metrics() -> None:
    registry = MetricsRegistry()
    registry.record_request("/foo", 200, 0.1)
    text = render_prometheus_text(registry.snapshot())

    assert "autohire_requests_total 1" in text
    assert "autohire_errors_total 0" in text
    assert 'autohire_requests_by_path_total{path="/foo"} 1' in text
    assert "autohire_uptime_seconds" in text


def test_metrics_middleware_and_router_end_to_end() -> None:
    registry = MetricsRegistry()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware, registry=registry)
    app.include_router(build_metrics_router(registry))

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "true"}

    with TestClient(app) as client:
        client.get("/ping")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "autohire_requests_by_path_total" in response.text
    assert 'path="/ping"' in response.text
