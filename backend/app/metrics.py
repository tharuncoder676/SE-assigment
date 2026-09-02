"""Prometheus-compatible metric registry (counters and a latency histogram).

Kept dependency-free so the container image stays small; the exposition format
is the standard one, so a real Prometheus server can scrape /metrics without
any adapter.
"""
import threading
from collections import defaultdict
from typing import Dict, List, Tuple

BUCKETS: Tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class MetricRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self.latency_buckets: Dict[float, int] = defaultdict(int)
        self.latency_sum = 0.0
        self.latency_count = 0
        self.errors = 0

    def observe(self, method: str, path: str, status: int, seconds: float) -> None:
        with self._lock:
            self.requests[(method, path, status)] += 1
            self.latency_sum += seconds
            self.latency_count += 1
            if status >= 500:
                self.errors += 1
            for bucket in BUCKETS:
                if seconds <= bucket:
                    self.latency_buckets[bucket] += 1

    def render(self) -> str:
        lines: List[str] = []
        with self._lock:
            lines.append("# HELP smartcare_http_requests_total Total HTTP requests.")
            lines.append("# TYPE smartcare_http_requests_total counter")
            for (method, path, status), count in sorted(self.requests.items()):
                lines.append(
                    'smartcare_http_requests_total{method="%s",path="%s",status="%d"} %d'
                    % (method, path, status, count)
                )
            lines.append("# HELP smartcare_http_request_duration_seconds Request latency.")
            lines.append("# TYPE smartcare_http_request_duration_seconds histogram")
            for bucket in BUCKETS:
                lines.append(
                    'smartcare_http_request_duration_seconds_bucket{le="%s"} %d'
                    % (bucket, self.latency_buckets[bucket])
                )
            lines.append(
                'smartcare_http_request_duration_seconds_bucket{le="+Inf"} %d'
                % self.latency_count
            )
            lines.append("smartcare_http_request_duration_seconds_sum %.6f" % self.latency_sum)
            lines.append("smartcare_http_request_duration_seconds_count %d" % self.latency_count)
            lines.append("# HELP smartcare_http_errors_total Responses with status >= 500.")
            lines.append("# TYPE smartcare_http_errors_total counter")
            lines.append("smartcare_http_errors_total %d" % self.errors)
        return "\n".join(lines) + "\n"


metrics = MetricRegistry()
