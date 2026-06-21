# OTel Weaver beat — validate the agent against an open standard

ABOUTME: A custom semconv registry for the agent's telemetry, validated statically and live.
ABOUTME: registry/ is checked in CI; live-check.sh streams a capture through weaver for the stage beat.

This is the "validate the agent's telemetry against an open semantic-convention registry" moment.
`weaver/registry/` codifies the agent's telemetry as semantic conventions; Weaver checks a registry
statically and validates a live (or captured) stream against it.

## Static check (committed, tested)

```bash
docker run --rm -v "$PWD/weaver/registry":/registry otel/weaver:v0.23.0 \
  registry check -r /registry --future
```

Exits 0 when the registry is valid. Covered by `tests/test_weaver.py`.

## Live-check (the stage beat)

```bash
weaver/live-check.sh                       # uses weaver/sample-telemetry.jsonl
weaver/live-check.sh demo/replay/raw/session-<ts>.jsonl   # or a real capture
```

It starts `weaver registry live-check` listening on OTLP gRPC (on the compose network), streams a
captured OTLP-JSON sample to it via a one-shot feeder Collector, and prints the JSON report. Example
report highlights from the synthetic sample:

- `registry_coverage: 0.8` — the `claude_code.*` attributes are recognized.
- `gen_ai.system` / `gen_ai.request.model` → "does not exist in the registry" (they come from the
  OTel GenAI standard, not this custom registry — point live-check at the OTel semconv registry to
  validate those, which surfaces the `gen_ai.system` → `gen_ai.provider.name` deprecation).
- `claude_code.*` → "not stable; development" (expected — these are new conventions).

## Gotchas (verified 2026-06-21)

- **Weaver's `--input-source file` JSON is NOT OTLP ExportRequest JSON** — it wants weaver's own
  sample shape. To replay a real OTLP capture, feed it over `--input-source otlp` (gRPC), which is
  what `live-check.sh` does via the feeder Collector.
- **The feeder must set `start_at: beginning`** on the `otlpjsonfile` receiver — it defaults to the
  end of the file and would ignore existing capture content.
- **The feeder must set `compression: none`** on its OTLP exporter — weaver's OTLP receiver returns
  `Unimplemented: gzip ... isn't supported` otherwise.
- live-check listens **gRPC only** (`--otlp-grpc-port`, default 4317) with an `--inactivity-timeout`;
  it is a one-shot command that exits after the stream goes quiet, then writes the report.
