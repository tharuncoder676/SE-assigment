"""TC-20 .. TC-25 - operational endpoints, security headers and rate limiting."""
from app.ratelimit import SlidingWindowLimiter


def test_tc20_health_probe(client):
    body = client.get("/health").json()
    assert body["status"] == "UP"
    assert body["version"] == "1.0.0"


def test_tc21_readiness_probe_checks_the_database(client):
    body = client.get("/ready").json()
    assert body["status"] == "READY"
    assert body["checks"]["database"] == "UP"


def test_tc22_metrics_are_exposed_in_prometheus_format(client):
    client.get("/health")
    text = client.get("/metrics").text
    assert "# TYPE smartcare_http_requests_total counter" in text
    assert "smartcare_http_request_duration_seconds_count" in text


def test_tc23_security_headers_are_present(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Request-ID"]


def test_tc24_rate_limiter_blocks_beyond_the_threshold():
    limiter = SlidingWindowLimiter(max_events=3, window_seconds=60)
    assert [limiter.allow("k") for _ in range(5)] == [True, True, True, False, False]
    assert limiter.allow("other-key") is True      # limits are per key


def test_tc25_openapi_document_is_published(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"].startswith("SmartCare")
    for path in ("/api/v1/auth/login", "/api/v1/appointments",
                 "/api/v1/doctors", "/health", "/metrics"):
        assert path in spec["paths"]
