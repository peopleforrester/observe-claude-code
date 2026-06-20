# ABOUTME: Verifies the Collector captures OTLP to a file and the replayer re-emits it freshly.
# ABOUTME: Underpins the offline replay — the stage safety net when the box is offline.
import time

import httpx

from conftest import COLLECTOR_OTLP_HTTP, REPO_ROOT, wait_until

CAPTURE_FILE = REPO_ROOT / "demo" / "replay" / "raw" / "otlp-capture.jsonl"


def test_collector_captures_otlp_to_file(http):
    now = time.time_ns()
    probe = "occ-capture-probe"
    payload = {
        "resourceSpans": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": probe}}]},
            "scopeSpans": [{
                "spans": [{
                    "traceId": "11111111111111111111111111111111",
                    "spanId": "2222222222222222",
                    "name": "capture-probe",
                    "kind": 1,
                    "startTimeUnixNano": str(now),
                    "endTimeUnixNano": str(now + 1_000_000),
                }],
            }],
        }],
    }
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/traces", json=payload)
    assert r.status_code == 200, f"collector rejected probe: {r.status_code} {r.text}"

    def captured():
        return CAPTURE_FILE.exists() and probe in CAPTURE_FILE.read_text()

    assert wait_until(captured, what="capture file contains the probe span")


def test_replayer_reemits_sample_with_fresh_timestamps(http):
    import subprocess

    # The sample carries 2020 timestamps; after replay the data must appear in a "now" window,
    # which only happens if the replayer shifted the timestamps.
    result = subprocess.run(
        ["python3", "demo/replay/replay.py", "--capture", "demo/replay/session-sample.jsonl"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"replayer failed: {result.stderr}"

    # Metric -> Prometheus (instant query only finds it if the timestamp is recent).
    def metric_fresh():
        q = http.get("http://localhost:9090/api/v1/query", params={"query": "occ_replay_probe"})
        return q.status_code == 200 and bool(q.json()["data"]["result"])

    assert wait_until(metric_fresh, what="replayed metric is fresh in Prometheus")

    # Trace -> Jaeger, recent.
    def trace_present():
        q = http.get("http://localhost:16686/api/traces",
                     params={"service": "occ-replay-sample", "lookback": "1h", "limit": 5})
        return q.status_code == 200 and bool(q.json().get("data"))

    assert wait_until(trace_present, what="replayed trace in Jaeger")
