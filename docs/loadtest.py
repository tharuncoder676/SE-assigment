"""Closed-loop load generator used to produce the performance figures in the
project report.

For each scenario a pool of worker threads issues requests continuously for a
fixed duration. The latency of every individual request is recorded so that
percentiles - not merely averages - can be reported, because the tail is what
a patient actually experiences.

Two measurement details matter and were both learned the hard way:

* The target is addressed as 127.0.0.1, never "localhost". On Windows
  "localhost" resolves to ::1 first; because uvicorn binds IPv4 only, every
  connection wasted ~2 s on a failed IPv6 attempt and the first version of
  this harness reported 2 050 ms for every scenario.
* Connections are pooled and reused (HTTP keep-alive), which is how a real
  browser or gateway behaves. Opening a fresh TCP connection per request
  measures the operating system, not the application.

Usage:  python docs/loadtest.py [http://127.0.0.1:8010]
"""
import json
import statistics
import sys
import threading
import time
from collections import Counter

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
DURATION = 8            # seconds per scenario
LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=100)


def scenario(name, method, path, workers, token=None, body=None):
    latencies, codes = [], Counter()
    lock = threading.Lock()
    stop_at = time.time() + DURATION
    headers = {"Authorization": "Bearer " + token} if token else {}

    def worker():
        local, local_codes = [], Counter()
        with httpx.Client(base_url=BASE, limits=LIMITS, timeout=15) as client:
            client.get("/health")                      # warm the connection
            while time.time() < stop_at:
                started = time.perf_counter()
                try:
                    response = client.request(method, path, json=body, headers=headers)
                    status = response.status_code
                except Exception:
                    status = 0
                local.append(time.perf_counter() - started)
                local_codes[status] += 1
        with lock:
            latencies.extend(local)
            codes.update(local_codes)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    started = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - started

    latencies.sort()

    def pct(p):
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))] * 1000

    result = {
        "scenario": name,
        "concurrency": workers,
        "requests": len(latencies),
        "throughput_rps": round(len(latencies) / wall, 1),
        "mean_ms": round(statistics.mean(latencies) * 1000, 2),
        "p50_ms": round(pct(0.50), 2),
        "p95_ms": round(pct(0.95), 2),
        "p99_ms": round(pct(0.99), 2),
        "max_ms": round(latencies[-1] * 1000, 2),
        "success_rate": round(100 * sum(v for k, v in codes.items()
                                        if 200 <= k < 400) / len(latencies), 2),
        "status_codes": dict(sorted(codes.items())),
    }
    print(json.dumps(result))
    return result


def register(tag):
    with httpx.Client(base_url=BASE, timeout=15) as client:
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Load Tester %s" % tag,
            "email": "loadtest.%s.%d@smartcare.local" % (tag, time.time_ns()),
            "password": "LoadTest@12345",
        })
        return response.json()["access_token"]


def crypto_benchmark():
    """Cost of the two deliberately expensive security primitives."""
    sys.path.insert(0, "backend")
    from app.security import (create_access_token, decode_access_token,
                              hash_password, verify_password)

    def timed(fn, repeat):
        started = time.perf_counter()
        for _ in range(repeat):
            fn()
        return round((time.perf_counter() - started) / repeat * 1000, 3)

    stored = hash_password("Benchmark@12345")
    token = create_access_token("bench@smartcare.local", "patient")
    return {
        "pbkdf2_hash_600k_ms": timed(lambda: hash_password("Benchmark@12345"), 5),
        "pbkdf2_verify_600k_ms": timed(lambda: verify_password("Benchmark@12345", stored), 5),
        "jwt_sign_ms": timed(lambda: create_access_token("b@x.io", "patient"), 2000),
        "jwt_verify_ms": timed(lambda: decode_access_token(token), 2000),
    }


if __name__ == "__main__":
    print("SmartCare load test against %s (%ds per scenario)\n" % (BASE, DURATION))
    token = register("read")
    results = []

    for workers in (1, 5, 10, 25, 50):
        results.append(scenario("GET /api/v1/doctors", "GET",
                                "/api/v1/doctors", workers))
    results.append(scenario("GET /health (liveness probe)", "GET", "/health", 25))
    results.append(scenario("GET /api/v1/doctors/1/slots", "GET",
                            "/api/v1/doctors/1/slots", 25))
    results.append(scenario("GET /api/v1/appointments (JWT verified)", "GET",
                            "/api/v1/appointments", 25, token=token))
    results.append(scenario("GET /metrics (Prometheus scrape)", "GET", "/metrics", 10))

    crypto = crypto_benchmark()
    print("\ncrypto:", json.dumps(crypto))

    with open("docs/loadtest-results.json", "w") as fh:
        json.dump({"scenarios": results, "crypto": crypto,
                   "duration_s": DURATION, "target": BASE}, fh, indent=2)
    print("\nWritten to docs/loadtest-results.json")
