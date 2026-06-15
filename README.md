# observe-claude-code

Observing an agentic coding tool (Claude Code) in production with OpenTelemetry.

The same agent telemetry — metrics, events, and beta traces — flows over OTLP to a single
OpenTelemetry Collector, which fans the identical stream to an open CNCF stack (Prometheus,
Loki, Jaeger, Grafana) and, later, to a commercial backend, side by side. Built for the
AGNTCon + MCPCon NA 2026 session *"What Does a Good Agent Look Like? Observing Claude Code in
Production With OpenTelemetry."*

The demo answers three questions on screen, not in narration:

1. **Productivity** — is the agent moving real work, or just generating activity?
2. **Cost** — where does the spend go, and where does it stop earning?
3. **Security** — what did the agent touch, which tool calls and MCP servers ran, and which
   were allowed or denied?

## Status

Early build. Docs are complete; the stack is being built phase by phase per
[`docs/design.md`](docs/design.md). Nothing under the component directories runs yet.

## Architecture

```
Claude Code (CLI)
   | OTLP grpc :4317   metrics + logs/events + traces(beta)
   v
OpenTelemetry Collector (one config, three pipelines, all-OTLP exporters)
   metrics ── otlphttp ──► Prometheus  (/api/v1/otlp native receiver)
   logs ───── otlphttp ──► Loki        (/otlp)
   traces ─── otlp ──────► Jaeger      (:4317)        ─► Grafana reads all three by uid
   (aux) OTel Weaver live-check validates the stream against a custom semconv registry
```

## Repository layout

| Path | What |
|---|---|
| `docs/` | Spec, abstract, pinned versions, design + build plan, gotchas |
| `env/` | `claude-code.env` — the telemetry env block |
| `collector/` | One Collector config, three pipelines |
| `compose/` | `docker-compose.yml` for the full stack |
| `prometheus/`, `loki/` | Backend configs |
| `grafana/` | Provisioned datasources, dashboard provisioning, dashboard JSON |
| `weaver/registry/` | Custom semconv registry for `claude_code.*` + `gen_ai.*` |
| `demo/` | Scripted session, throwaway target repo, offline replay |
| `slides/` | Exported deck (commercial side kept generic) |

## How to run

Not yet runnable — the Compose stack is Phase 1. Once built, the flow will be:

```bash
# 1. Bring up the open stack (Collector, Prometheus, Loki, Jaeger, Grafana)
docker compose -f compose/docker-compose.yml up -d

# 2. Point Claude Code at the Collector and launch a session
source env/claude-code.env
claude

# 3. Watch the panes move in Grafana, and validate the stream with Weaver
```

This section gets filled in with verified commands as each phase lands.

## Documentation

- [`docs/spec.md`](docs/spec.md) — talk and demo build spec (intent)
- [`docs/abstract.md`](docs/abstract.md) — AGNTCon submission
- [`docs/versions.md`](docs/versions.md) — pinned GA versions + spec corrections (verified 2026-06-15)
- [`docs/design.md`](docs/design.md) — architecture decisions and phased build plan
- [`docs/gotchas-weaver.md`](docs/gotchas-weaver.md) — OTel Weaver usage and gotchas
- [`docs/gotchas-otlp-integration.md`](docs/gotchas-otlp-integration.md) — OTLP-native pipeline gotchas
