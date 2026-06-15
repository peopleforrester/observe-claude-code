# Gotchas: OTel Weaver (verified 2026-06-15)

ABOUTME: How OTel Weaver is used to validate the agent's live OTLP stream against a custom semconv registry.
ABOUTME: Verified against official Weaver docs/releases on 2026-06-15. Weaver is pre-1.0 — pin the version.

## Version and distribution

- **Latest: v0.23.0 (released 2026-04-22)** — github.com/open-telemetry/weaver/releases.
- **Pre-1.0.** Breaking changes land in minor bumps (e.g. 0.22.1 changed auto-escaping and
  schema format). The version number is the maturity warning. **Pin the exact version on stage
  and rehearse against it — never `latest`.**
- Distribution: prebuilt binaries + installers + MSI on releases; `cargo` from source; Docker
  image `otel/weaver` (e.g. `otel/weaver:v0.23.0`).

## Verdict: live on-stage validation is feasible — make it a live step

`weaver registry live-check` stands up its own OTLP receiver, ingests a real stream, and
validates emitted telemetry against the registry in real time. First-class documented command.

## Commands (exact, confirmed)

- `weaver registry check` — validate a registry against core policies (great static slide).
- `weaver registry generate` — produce docs/code artifacts from a registry.
- `weaver registry live-check` — validate live or sampled telemetry against the registry.
- `weaver registry emit` — send example signals to an OTLP receiver (dry-run helper).
- `weaver registry resolve` — **DEPRECATED**, do not demo it; use `generate`/`package`.
- Also present: `registry diff`, `registry stats`, `registry package`, `registry infer`,
  `registry mcp`, experimental `weaver serve`.

## live-check specifics

- `--input-source` — `otlp` (default), a file path, or `stdin`. Same command does **live OTLP**
  or **replay a captured file** — one flag swap. This dovetails with our Phase 6 replay.
- `--otlp-grpc-address` / `--otlp-grpc-port` — Weaver opens its own gRPC OTLP listener
  (default 4317). The agent/collector exports to it.
- `--inactivity-timeout` — auto-exit after N idle seconds (clean stage stop).
- `--format` — `ansi` (colorized, best for stage), `json`, `yaml`, `jsonl`, templates.
- `--output` — report dir (`live_check.json`) or `none`.
- Output: per-entity advisory report — attributes evaluated, advice level (violation vs
  improvement), deprecated/stability flags, totals you can gate on.

Live command:
```
weaver registry live-check \
  --registry ./weaver/registry \
  --input-source otlp \
  --otlp-grpc-port 4317 \
  --inactivity-timeout 60 \
  --format ansi
```

## Custom registry — build cost LOW (an afternoon of YAML)

Minimum two files (`weaver/registry/`):

1. `manifest.yaml` — name, description, schema_url, and a dependency importing official semconv:
   ```yaml
   name: claude-code
   description: Custom semconv for Claude Code agent telemetry
   schema_url: https://example.com/schemas/1.0.0
   dependencies:
     - name: otel
       registry_path: https://github.com/open-telemetry/semantic-conventions@v1.42.0[model]
   ```
2. One or more group YAML files. `ref:` the `gen_ai.*` attributes from the otel dependency
   (don't redefine them); hand-author only the genuinely custom `claude_code.*` ones:
   ```yaml
   groups:
     - id: span.claude_code.session
       type: span
       stability: development
       brief: Claude Code session span
       span_kind: client
       attributes:
         - id: claude_code.session.id
           type: string
           brief: Session identifier
           requirement_level: required
         - ref: gen_ai.request.model
           requirement_level: required
   ```

Validate with `weaver registry check ./weaver/registry`.

## Collector integration

Weaver does not tap or replace the collector pipeline — it's a sink. Two patterns:
- **Direct**: the agent exports straight to Weaver's `:4317`.
- **Alongside the collector** (preferred for the demo): add an OTLP exporter to the collector
  that fans a copy of the stream to Weaver's port, so the normal backends still receive data and
  Weaver validates the same signals in parallel.

Note this competes for port 4317 with Jaeger and the collector's own receiver — give Weaver a
distinct host port (e.g. expose it on 4319→4317) to avoid the bind clash.

## Demo-specific gotchas

- **Pin the version** (flags move pre-1.0). The OTel blog example pins `v0.15.2`; we're on
  0.23.0 which added `.weaver.toml` config for live-check.
- **`gen_ai.*` is still "Development"** in semconv, so live-check will emit experimental/unstable
  advisories on those attributes. Frame on stage as "advisories against an evolving convention,"
  not failures — this is actually the point.
- **Container networking**: from a container use `host.docker.internal:4317`; locally
  `localhost:4317`. Match Claude Code's `OTEL_EXPORTER_OTLP_PROTOCOL` to the port (grpc 4317).
- **De-risk with a captured file**: pre-record one clean run, keep `--input-source <file>` ready.
  If live OTLP fails on stage, replay the identical validation from the file — same command,
  same report, no network.

## Recommended stage flow

1. `weaver registry check ./weaver/registry` — proves the custom registry is valid (slide/live).
2. `weaver registry live-check --input-source otlp --otlp-grpc-port 4317 --format ansi`, run the
   agent pointed at Weaver, advisories stream live.
3. Fallback: same command with `--input-source ./captured.json`.
