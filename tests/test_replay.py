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
