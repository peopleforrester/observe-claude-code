# Reference — Versions & Gotchas

Pinned component versions and the traps we already hit, so you don't rediscover them. Re-verify
versions the week of the event — the stack and the schema both move. The repo's `docs/versions.md`
and `docs/gotchas-*.md` are the living source.

## Pinned versions (verified mid-2026)

| Component | Pin |
|---|---|
| OTel Collector (Contrib) | `v0.154.0` |
| Prometheus | `v3.12.0` |
| Grafana Loki | `v3.7.2` |
| Jaeger (v2) | `v2.19.0` |
| Grafana | `12.4.4` (deliberately not 13.x) |
| OTel semconv | `v1.42.0` |
| OTel Weaver | `v0.23.0` |
| FastMCP | `3.4.x` |

## Gotchas that will bite

- **OTLP is all-native.** The Collector exports OTLP to every backend (Prometheus `/api/v1/otlp`,
  Loki `/otlp`, Jaeger OTLP). Prometheus needs `--web.enable-otlp-receiver`; Loki needs tsdb + v13
  schema and structured metadata on or it won't start.
- **Loki stores the bare `event_name`** (e.g. `tool_decision`), not `claude_code.tool_decision` —
  query without the prefix.
- **Resource attributes become labels only if promoted** (`promote_resource_attributes`), and dots
  escape to underscores (`team.id` → `team_id`).
- **Grafana 13 breaks file-provisioned v2-schema dashboards** — we pin 12.4.x and use classic v1 JSON.
- **The cost metric carries a `_USD` suffix** (`claude_code_cost_usage_USD_total`) because USD isn't
  a known Prometheus unit.
- **MCP tool denial:** a permission `deny` rule *withholds* the tool (no event); to get a visible
  `tool_decision = reject`, allow the tool and deny it with a PreToolUse hook.
- **Weaver feeder:** needs `start_at: beginning` (else it ignores existing capture) and
  `compression: none` (weaver's OTLP receiver rejects gzip).
- **Telemetry events ride the logs exporter** — `OTEL_LOGS_EXPORTER` must be set or tool_decision /
  mcp_server_connection never export.

## For the Datadog work

The Collector config has a marked `# --- Datadog (Nick) ---` spot. Add the Datadog exporter and
attach it as a second exporter per pipeline (see doc 5). The key goes in `~/secrets`, never the repo.
