# Offline replay (the stage safety net)

ABOUTME: How the demo replays canned telemetry offline so the dashboards move without a live agent.
ABOUTME: Real captures carry PII and stay local (gitignored); only sanitized samples are committed.

The Collector captures every signal to `demo/replay/raw/otlp-capture.jsonl` (a `file/capture`
exporter on all three pipelines). The replayer re-emits a capture with **freshened timestamps**, so
the same telemetry lands in the backends "now" and the dashboards move — with no live agent and no
dependence on conference wifi.

## Capture a real session (on the demo box)

```bash
demo/replay/capture-session.sh
```

This clears the capture, runs the scripted session (the denied-deploy security moment included),
and snapshots the result to `demo/replay/raw/session-<timestamp>.jsonl`.

## Replay it offline

```bash
# one pass:
python3 demo/replay/replay.py --capture demo/replay/raw/session-<timestamp>.jsonl
# or loop for a live-looking stage demo:
python3 demo/replay/replay.py --capture demo/replay/raw/session-<timestamp>.jsonl --loop
```

The replayer shifts every OTLP timestamp so the capture ends at "now" (internal timing preserved),
then posts to the Collector's OTLP/HTTP endpoint — which fans it to all backends exactly like a live
run (and to the commercial backend once that's wired in).

## PRIVACY — do not commit real captures

Real captures include account/user identifiers (`user_email`, `user_account_uuid`,
`organization_id`, `user_id`). The whole `demo/replay/raw/` directory is **gitignored** for this
reason. The only committed capture is **`demo/replay/session-sample.jsonl`** — a synthetic,
PII-free sample used for tests and illustration. A guard test fails the suite if any PII field
appears in the committed sample.

## On stage

Canned replay is **primary** (deterministic, offline). A live run is the backup if the room network
holds. A pre-recorded screen capture is the floor. See `docs/run-of-show.md`.
