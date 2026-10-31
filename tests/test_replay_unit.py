# ABOUTME: Offline unit tests for the OTLP replayer — timestamp shifting, signal routing, CLI errors.
# ABOUTME: The HTTP post is stubbed, so these run without the Collector or any live backend.
import http.server
import importlib.util
import json
import sys
import threading
import time

import pytest

from conftest import REPO_ROOT

REPLAY_PATH = REPO_ROOT / "demo" / "replay" / "replay.py"
SAMPLE_FILE = REPO_ROOT / "demo" / "replay" / "session-sample.jsonl"
ENDPOINT = "http://collector.test:4318"
OLD_NS = 1577836800000000000  # 2020-01-01T00:00:00Z


@pytest.fixture
def replay():
    spec = importlib.util.spec_from_file_location("replay_unit", REPLAY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def posted(replay, monkeypatch):
    """Stub replay.post; record each (url, body) and answer 200."""
    calls = []

    def fake_post(url, body):
        calls.append((url, body))
        return 200

    monkeypatch.setattr(replay, "post", fake_post)
    return calls


def _metric_record(ts):
    return {"resourceMetrics": [{"scopeMetrics": [{"metrics": [{
        "name": "m", "gauge": {"dataPoints": [{"asDouble": 1, "timeUnixNano": str(ts)}]},
    }]}]}]}


def _log_record(ts):
    return {"resourceLogs": [{"scopeLogs": [{"logRecords": [{
        "timeUnixNano": str(ts), "observedTimeUnixNano": str(ts),
    }]}]}]}


def _span_record(ts):
    return {"resourceSpans": [{"scopeSpans": [{"spans": [{
        "startTimeUnixNano": str(ts), "endTimeUnixNano": str(ts + 1_000_000),
    }]}]}]}


def test_iter_timestamps_ignores_unset_and_malformed_values(replay):
    record = {"a": [
        {"timeUnixNano": "0"},
        {"timeUnixNano": ""},
        {"timeUnixNano": None},
        {"timeUnixNano": "not-a-number"},
        {"startTimeUnixNano": 5},
        {"nested": {"endTimeUnixNano": "7"}},
    ]}
    assert sorted(replay.iter_timestamps(record)) == [5, 7]


def test_shift_timestamps_keeps_unset_values_and_writes_strings(replay):
    record = {"spans": [{"startTimeUnixNano": 10, "endTimeUnixNano": "0", "other": "x"}]}
    replay.shift_timestamps(record, 5)
    span = record["spans"][0]
    assert span["startTimeUnixNano"] == "15"
    assert span["endTimeUnixNano"] == "0", "an unset (zero) timestamp must stay unset"
    assert span["other"] == "x"


def test_load_records_skips_blank_lines(replay, tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text(f"{json.dumps(_metric_record(1))}\n\n   \n{json.dumps(_log_record(2))}\n")
    records = replay.load_records(capture)
    assert [next(iter(r)) for r in records] == ["resourceMetrics", "resourceLogs"]


def test_replay_once_routes_each_signal_to_its_otlp_path(replay, posted):
    records = [_metric_record(OLD_NS), _log_record(OLD_NS), _span_record(OLD_NS)]
    counts = replay.replay_once(records, ENDPOINT)
    assert counts == {"metrics": 1, "logs": 1, "traces": 1}
    assert [url for url, _ in posted] == [
        f"{ENDPOINT}/v1/metrics", f"{ENDPOINT}/v1/logs", f"{ENDPOINT}/v1/traces",
    ]


def test_replay_once_shifts_latest_timestamp_to_now_without_mutating_source(replay, posted):
    records = [_span_record(OLD_NS)]
    source = json.dumps(records)
    before = time.time_ns()
    replay.replay_once(records, ENDPOINT)
    after = time.time_ns()

    assert json.dumps(records) == source, "replay_once must not mutate the loaded capture"
    span = posted[0][1]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    end, start = int(span["endTimeUnixNano"]), int(span["startTimeUnixNano"])
    assert before <= end <= after, "latest timestamp should land at 'now'"
    assert end - start == 1_000_000, "relative spacing between timestamps must be preserved"


def test_replay_once_does_not_count_rejected_posts(replay, monkeypatch, capsys):
    monkeypatch.setattr(replay, "post", lambda url, body: 400)
    counts = replay.replay_once([_metric_record(OLD_NS)], ENDPOINT)
    assert counts == {"metrics": 0, "logs": 0, "traces": 0}
    assert "/v1/metrics returned 400" in capsys.readouterr().err


def test_replay_once_refuses_a_capture_without_timestamps(replay, posted):
    with pytest.raises(SystemExit, match="no timestamps"):
        replay.replay_once([{"resourceSpans": []}], ENDPOINT)
    assert posted == []


def test_committed_sample_replays_every_record(replay, posted):
    records = replay.load_records(SAMPLE_FILE)
    assert records, "committed sample is empty"
    counts = replay.replay_once(records, ENDPOINT)
    assert sum(counts.values()) == len(records), "every sample record should map to one signal"
    assert all(counts.values()), f"sample should exercise all three signals, got {counts}"


def test_main_replays_capture_once_against_given_endpoint(replay, posted, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "replay.py", "--capture", str(SAMPLE_FILE), "--endpoint", ENDPOINT,
    ])
    replay.main()
    out = capsys.readouterr().out
    assert "Loaded" in out and "Replayed:" in out
    assert posted and all(url.startswith(ENDPOINT) for url, _ in posted)


def test_main_loop_replays_again_after_each_interval(replay, posted, monkeypatch):
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise KeyboardInterrupt  # end the otherwise endless --loop

    monkeypatch.setattr(replay.time, "sleep", fake_sleep)
    monkeypatch.setattr(sys, "argv", [
        "replay.py", "--capture", str(SAMPLE_FILE), "--endpoint", ENDPOINT,
        "--loop", "--interval", "0.5",
    ])
    with pytest.raises(KeyboardInterrupt):
        replay.main()
    per_pass = len(replay.load_records(SAMPLE_FILE))
    assert sleeps == [0.5, 0.5]
    assert len(posted) == 2 * per_pass, "each loop should re-emit the whole capture"


def test_post_sends_otlp_json_and_returns_the_status(replay):
    """Exercise the real urllib POST against a loopback server standing in for the Collector."""
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            received.append((self.path, self.headers["Content-Type"], self.rfile.read(length)))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = _log_record(OLD_NS)
        status = replay.post(f"http://127.0.0.1:{server.server_port}/v1/logs", body)
    finally:
        server.shutdown()
        server.server_close()

    assert status == 200
    path, content_type, raw = received[0]
    assert path == "/v1/logs"
    assert content_type == "application/json"
    assert json.loads(raw) == body


def test_main_exits_on_missing_capture(replay, posted, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["replay.py", "--capture", str(tmp_path / "nope.jsonl")])
    with pytest.raises(SystemExit, match="capture file not found"):
        replay.main()
    assert posted == []


def test_main_exits_on_empty_capture(replay, posted, monkeypatch, tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n")
    monkeypatch.setattr(sys, "argv", ["replay.py", "--capture", str(empty)])
    with pytest.raises(SystemExit, match="capture file is empty"):
        replay.main()
    assert posted == []
