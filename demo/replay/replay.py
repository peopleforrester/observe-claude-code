# ABOUTME: Re-emits captured OTLP (JSON-lines) to the Collector with freshened timestamps.
# ABOUTME: The offline stage safety net — dashboards move from canned data with no live agent.
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

# OTLP timestamp fields (nanoseconds since epoch) that must be shifted to "now".
TS_KEYS = {"timeUnixNano", "startTimeUnixNano", "endTimeUnixNano", "observedTimeUnixNano"}

# Top-level OTLP signal key -> the Collector OTLP/HTTP path it posts to.
SIGNAL_PATHS = {
    "resourceMetrics": "/v1/metrics",
    "resourceLogs": "/v1/logs",
    "resourceSpans": "/v1/traces",
}


def iter_timestamps(obj):
    """Yield every OTLP timestamp (as int ns) found anywhere in a decoded JSON object."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in TS_KEYS and value not in (None, "", "0", 0):
                try:
                    yield int(value)
                except (ValueError, TypeError):
                    pass
            else:
                yield from iter_timestamps(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_timestamps(item)


def shift_timestamps(obj, delta_ns):
    """Add delta_ns to every OTLP timestamp in place (kept as strings, OTLP/JSON form)."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in TS_KEYS and value not in (None, "", "0", 0):
                try:
                    obj[key] = str(int(value) + delta_ns)
                except (ValueError, TypeError):
                    pass
            else:
                shift_timestamps(value, delta_ns)
    elif isinstance(obj, list):
        for item in obj:
            shift_timestamps(item, delta_ns)


def post(url, body):
    """POST an OTLP/JSON body; return the HTTP status code."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def load_records(path):
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def replay_once(records, endpoint):
    """Shift one fresh copy of the capture to end at 'now' and re-emit it. Returns per-signal counts."""
    all_ts = [ts for rec in records for ts in iter_timestamps(rec)]
    if not all_ts:
        raise SystemExit("no timestamps found in capture — nothing to replay")
    delta = time.time_ns() - max(all_ts)

    counts = {"metrics": 0, "logs": 0, "traces": 0}
    for rec in records:
        shifted = json.loads(json.dumps(rec))  # deep copy so each loop re-shifts from source
        shift_timestamps(shifted, delta)
        for signal_key, path_suffix in SIGNAL_PATHS.items():
            if signal_key in shifted:
                status = post(endpoint + path_suffix, shifted)
                if status == 200:
                    counts[path_suffix.rsplit("/", 1)[-1]] += 1
                else:
                    print(f"  warning: {path_suffix} returned {status}", file=sys.stderr)
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Re-emit captured OTLP to the Collector with freshened timestamps."
    )
    parser.add_argument("--capture", default="demo/replay/session-sample.jsonl",
                        help="capture file (OTLP JSON-lines)")
    parser.add_argument("--endpoint", default="http://localhost:4318",
                        help="Collector OTLP/HTTP base endpoint")
    parser.add_argument("--loop", action="store_true",
                        help="replay continuously (for a live-looking stage demo)")
    parser.add_argument("--interval", type=float, default=10.0,
                        help="seconds between loops when --loop is set")
    args = parser.parse_args()

    path = Path(args.capture)
    if not path.exists():
        raise SystemExit(f"capture file not found: {path}")
    records = load_records(path)
    if not records:
        raise SystemExit("capture file is empty")
    print(f"Loaded {len(records)} OTLP records from {path}")

    while True:
        counts = replay_once(records, args.endpoint)
        print(f"Replayed: {counts['metrics']} metrics, {counts['logs']} logs, "
              f"{counts['traces']} traces (timestamps shifted to now)")
        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
