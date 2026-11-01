# ABOUTME: Verifies the Collector captures OTLP to a file and the replayer re-emits it freshly.
# ABOUTME: Underpins the offline replay — the stage safety net when the box is offline.
import importlib.util
import sys
import time

import httpx
import pytest

from conftest import COLLECTOR_OTLP_HTTP, JAEGER_UI_URL, PROMETHEUS_URL, REPO_ROOT, wait_until

CAPTURE_FILE = REPO_ROOT / "demo" / "replay" / "raw" / "otlp-capture.jsonl"
SAMPLE_FILE = REPO_ROOT / "demo" / "replay" / "session-sample.jsonl"
SAMPLE_TRANSCRIPT = REPO_ROOT / "demo" / "replay" / "session-sample.transcript.jsonl"
# Identifiers that must never reach the public repo via a committed capture.
PII_FIELDS = ["user_email", "user_account_uuid", "user_account_id", "user_id", "organization_id"]


def _load_replayer():
    path = REPO_ROOT / "demo" / "replay" / "replay.py"
    spec = importlib.util.spec_from_file_location("replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("sample", [SAMPLE_FILE, SAMPLE_TRANSCRIPT], ids=lambda p: p.name)
def test_committed_sample_has_no_pii(sample):
    text = sample.read_text()
    leaked = [f for f in PII_FIELDS if f in text]
    assert not leaked, f"committed replay sample {sample.name} contains PII fields: {leaked}"


def test_replayer_shifts_all_timestamps():
    replay = _load_replayer()
    record = {"resourceSpans": [{"scopeSpans": [{"spans": [
        {"startTimeUnixNano": "1577836800000000000", "endTimeUnixNano": "1577836800001000000"}
    ]}]}]}
    assert max(replay.iter_timestamps(record)) == 1577836800001000000
    delta = 1_000_000_000_000  # +1000s
    replay.shift_timestamps(record, delta)
    span = record["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert int(span["startTimeUnixNano"]) == 1577836800000000000 + delta
    assert int(span["endTimeUnixNano"]) == 1577836800001000000 + delta


@pytest.mark.integration
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


@pytest.mark.integration
def test_replayer_reemits_sample_with_fresh_timestamps(http):
    import subprocess

    # The sample carries 2020 timestamps; after replay the data must appear in a "now" window,
    # which only happens if the replayer shifted the timestamps.
    result = subprocess.run(
        ["python3", "demo/replay/replay.py", "--capture", "demo/replay/session-sample.jsonl",
         "--endpoint", COLLECTOR_OTLP_HTTP],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"replayer failed: {result.stderr}"

    # Metric -> Prometheus (instant query only finds it if the timestamp is recent).
    def metric_fresh():
        q = http.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "occ_replay_probe"})
        return q.status_code == 200 and bool(q.json()["data"]["result"])

    assert wait_until(metric_fresh, what="replayed metric is fresh in Prometheus")

    # Trace -> Jaeger, recent.
    def trace_present():
        q = http.get(f"{JAEGER_UI_URL}/api/traces",
                     params={"service": "occ-replay-sample", "lookback": "1h", "limit": 5})
        return q.status_code == 200 and bool(q.json().get("data"))

    assert wait_until(trace_present, what="replayed trace in Jaeger")


def _jaeger_trace_as_otlp(trace):
    """Recast one Jaeger /api/traces trace as OTLP/JSON spans so join.py can read it."""
    spans = [{
        "traceId": span["traceID"],
        "spanId": span["spanID"],
        "name": span["operationName"],
        "attributes": [{"key": t["key"], "value": {"stringValue": str(t["value"])}}
                       for t in span.get("tags", [])],
    } for span in trace["spans"]]
    return [{"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}]


@pytest.mark.integration
def test_replayed_sample_trace_joins_back_to_its_prompt(http):
    """The stage fallback: a trace read back out of Jaeger joins to the paired transcript's prompt."""
    import subprocess

    spec = importlib.util.spec_from_file_location("join", REPO_ROOT / "demo" / "replay" / "join.py")
    join = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = join  # dataclasses resolve their module here
    spec.loader.exec_module(join)

    result = subprocess.run(
        ["python3", "demo/replay/replay.py", "--capture", "demo/replay/session-sample.jsonl",
         "--endpoint", COLLECTOR_OTLP_HTTP],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"replayer failed: {result.stderr}"

    trace_id = next(join.tool_spans(join.load_jsonl(SAMPLE_FILE))).trace_id

    def trace_with_tool_spans():
        q = http.get(f"{JAEGER_UI_URL}/api/traces/{trace_id}")
        if q.status_code != 200 or not q.json().get("data"):
            return None
        records = _jaeger_trace_as_otlp(q.json()["data"][0])
        return records if list(join.tool_spans(records)) else None

    records = wait_until(trace_with_tool_spans, what="replayed sample trace with tool spans in Jaeger")
    joins = join.join(records, join.load_jsonl(SAMPLE_TRANSCRIPT), trace_id=trace_id)
    assert {j.span.tool_name for j in joins} >= {"Edit", "mcp__prod-api__deploy"}
    assert all("deploy" in j.prompt for j in joins), "every tool span should reach the sample prompt"
