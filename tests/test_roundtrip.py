# ABOUTME: End-to-end fan-out proof — OTLP pushed to the Collector lands in all three backends.
# ABOUTME: A metric reaches Prometheus, a log reaches Loki, and a trace reaches Jaeger.
import time

from conftest import (
    COLLECTOR_OTLP_HTTP,
    JAEGER_UI_URL,
    LOKI_URL,
    PROMETHEUS_URL,
    wait_until,
)

SERVICE_NAME = "occ-roundtrip"
METRIC_NAME = "occ_roundtrip_probe"


def _resource():
    return {"attributes": [{"key": "service.name", "value": {"stringValue": SERVICE_NAME}}]}


def test_metric_reaches_prometheus(http):
    now_ns = str(time.time_ns())
    payload = {
        "resourceMetrics": [{
            "resource": _resource(),
            "scopeMetrics": [{
                "metrics": [{
                    "name": METRIC_NAME,
                    "gauge": {"dataPoints": [{"asDouble": 1, "timeUnixNano": now_ns}]},
                }],
            }],
        }],
    }
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/metrics", json=payload)
    assert r.status_code == 200, f"collector rejected metric: {r.status_code} {r.text}"

    def present():
        q = http.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": METRIC_NAME})
        return q.status_code == 200 and bool(q.json()["data"]["result"])

    assert wait_until(present, what=f"metric {METRIC_NAME} in Prometheus")


def test_log_reaches_loki(http):
    now_ns = time.time_ns()
    payload = {
        "resourceLogs": [{
            "resource": _resource(),
            "scopeLogs": [{
                "logRecords": [{
                    "timeUnixNano": str(now_ns),
                    "body": {"stringValue": "occ roundtrip log probe"},
                }],
            }],
        }],
    }
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/logs", json=payload)
    assert r.status_code == 200, f"collector rejected log: {r.status_code} {r.text}"

    start = str(now_ns - 5 * 60 * 1_000_000_000)
    end = str(now_ns + 60 * 1_000_000_000)

    def present():
        q = http.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={"query": f'{{service_name="{SERVICE_NAME}"}}', "start": start, "end": end},
        )
        return q.status_code == 200 and bool(q.json()["data"]["result"])

    assert wait_until(present, what=f"log stream {SERVICE_NAME} in Loki")


def test_trace_reaches_jaeger(http):
    now_ns = time.time_ns()
    payload = {
        "resourceSpans": [{
            "resource": _resource(),
            "scopeSpans": [{
                "spans": [{
                    "traceId": "0af7651916cd43dd8448eb211c80319c",
                    "spanId": "b7ad6b7169203331",
                    "name": "occ-roundtrip-span",
                    "kind": 1,
                    "startTimeUnixNano": str(now_ns),
                    "endTimeUnixNano": str(now_ns + 1_000_000),
                }],
            }],
        }],
    }
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/traces", json=payload)
    assert r.status_code == 200, f"collector rejected trace: {r.status_code} {r.text}"

    def present():
        q = http.get(
            f"{JAEGER_UI_URL}/api/traces",
            params={"service": SERVICE_NAME, "lookback": "1h", "limit": 10},
        )
        return q.status_code == 200 and bool(q.json().get("data"))

    assert wait_until(present, what=f"trace for {SERVICE_NAME} in Jaeger")
