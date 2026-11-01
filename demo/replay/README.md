# Offline replay (the stage safety net)

ABOUTME: How the demo replays canned telemetry offline so the dashboards move without a live agent.
ABOUTME: Real captures and their transcripts carry PII and stay local (gitignored); only synthetic samples are committed.

The Collector captures every signal to `demo/replay/raw/otlp-capture.jsonl` (a `file/capture`
exporter on all three pipelines). The replayer re-emits a capture with **freshened timestamps**, so
the same telemetry lands in the backends "now", and the dashboards move with no live agent and no
dependence on conference wifi.

## Capture a real session (on the demo box)

```bash
demo/replay/capture-session.sh
```

This clears the capture, runs the scripted session (the denied-deploy security moment included)
under a pinned session ID, and snapshots a pair:

- `demo/replay/raw/session-<timestamp>.jsonl`: the OTLP the Collector captured.
- `demo/replay/raw/session-<timestamp>.transcript.jsonl`: that session's Claude Code transcript,
  copied from `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/*/<session-id>.jsonl`.

The session's own output goes to `demo/replay/raw/session-<timestamp>.log`. If the session fails
(a logged-out `claude -p` still exports OTLP and writes a transcript, but no tool spans), the
script stops there and prints the end of that log.

It ends by running the join below over the pair and fails loudly if no transcript was written or if
the OTLP and the transcript come from different sessions.

## Replay it offline

```bash
# one pass:
python3 demo/replay/replay.py --capture demo/replay/raw/session-<timestamp>.jsonl
# or loop for a live-looking stage demo:
python3 demo/replay/replay.py --capture demo/replay/raw/session-<timestamp>.jsonl --loop
```

The replayer shifts every OTLP timestamp so the capture ends at "now" (internal timing preserved),
then posts to the Collector's OTLP/HTTP endpoint, which fans it to all backends exactly like a live
run (and to the commercial backend once that's wired in).

If the Collector rejects a record (4xx/5xx), the replayer warns and moves on to the next record. If
it cannot reach the Collector at all (refused connection, DNS failure, timeout), a single pass exits
non-zero with a clear message; `--loop` warns, skips the rest of that pass, and tries again after
`--interval`, so a Collector restart on stage does not end the loop.

## Join a trace back to its prompt

The replay keeps every trace and span ID, so a trace picked in Jaeger after a replay is the same
trace as in the capture. `join.py` walks it back to the prompt that caused it using the paired
transcript, with no prompt text in any backend:

```bash
python3 demo/replay/join.py --capture demo/replay/raw/session-<timestamp>.jsonl --trace <trace-id>
```

The path: trace ID → its `claude_code.tool` spans → each span's `tool_use_id` → the transcript's
`tool_use` block with that id → up `parentUuid` past tool results → the typed user prompt. The
span's `session.id` must equal the transcript's `sessionId`. The transcript is found by name
(`<capture>.transcript.jsonl`); pass `--transcript` to point elsewhere. With no arguments it joins
the committed sample pair. Claude Code calls the transcript format internal, so the join is
version-specific: re-run a capture after a Claude Code upgrade before relying on it on stage.

## PRIVACY: do not commit real captures

Real captures include account/user identifiers (`user_email`, `user_account_uuid`,
`organization_id`, `user_id`), and the transcript beside each one holds the full prompt and tool
text. The whole `demo/replay/raw/` directory is **gitignored** for this reason. The only committed
pair is **`demo/replay/session-sample.jsonl`** with **`session-sample.transcript.jsonl`**, synthetic
and PII-free, built so the sample trace's tool spans join to the sample prompt, and used for tests
and illustration. A guard test fails the suite if any PII field appears in either file.

## On stage

Canned replay is **primary** (deterministic, offline). A live run is the backup if the room network
holds. A pre-recorded screen capture is the floor. See `docs/run-of-show.md`.
