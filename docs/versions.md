# Pinned Versions and Verified Gotchas (as of 2026-06-15)

ABOUTME: Current GA versions and breaking-change gotchas for the observe-claude-code stack.
ABOUTME: Every version verified against official release pages on 2026-06-15. Re-verify the week of the event (Oct 2026).

All version numbers below were confirmed against official GitHub release pages and
vendor docs on 2026-06-15, not from training data. The schema and CNCF stack are
both moving; **re-verify the week of Oct 22, 2026** before the recording goes final.

## Version matrix

| Component | Pin | Released | Source |
|---|---|---|---|
| OTel Collector (Contrib) | `v0.154.0` | 2026-06-09 | github.com/open-telemetry/opentelemetry-collector-contrib/releases |
| OTel Collector (Core) | `v1.60.0` / `v0.154.0` | 2026-06-08 | github.com/open-telemetry/opentelemetry-collector/releases |
| Prometheus | `v3.12.0` | 2026-05-28 | github.com/prometheus/prometheus/releases |
| Grafana Loki | `v3.7.2` | 2026-05-13 | github.com/grafana/loki/releases |
| Jaeger (v2) | `v2.19.0` | 2026-06-03 | github.com/jaegertracing/jaeger/releases |
| Grafana | `12.4.x` (chosen) / `13.0.2` latest | 13.0.2 = 2026-06-09 | github.com/grafana/grafana/releases |
| OTel semconv | `v1.42.0` | 2026-06-12 | github.com/open-telemetry/semantic-conventions/releases |
| OTel Weaver | `v0.23.0` (pre-1.0) | 2026-04-22 | github.com/open-telemetry/weaver/releases |

Grafana is the one intentional non-latest pin: `12.4.x` instead of latest `13.0.2`, to avoid the
v13 v2-schema provisioning trap (see correction #3). Everything else is latest GA. Weaver is the
only pre-1.0 component — pin the exact version and rehearse against it (see gotchas-weaver.md).

Use the Contrib collector image (`otel/opentelemetry-collector-contrib:0.154.0`) — the
Datadog exporter and the otlphttp/Loki path both live there.

## Spec corrections (these change the build)

1. **The Loki exporter no longer exists.** It was deprecated in 2024 and **removed from
   Contrib in v0.131.0**. A config with `exporters: [loki]` will fail to start. The spec's
   `exporter: otlp/loki (or loki exporter)` (architecture diagram + section 7) must become
   **`otlphttp` pointed at Loki's native OTLP endpoint**:
   ```yaml
   exporters:
     otlphttp/loki:
       endpoint: http://loki:3100/otlp   # collector appends /v1/logs itself
   ```

2. **`gen_ai.system` is being replaced by `gen_ai.provider.name`.** `gen_ai.system` is now
   marked deprecated in the registry. **Claude Code still emits `gen_ai.system=anthropic`**
   (confirmed against the live doc), so the demo data is fine — but the "open standard the
   ecosystem can target" slide should name BOTH and note the rename in flight, or it will
   look out of date to a semconv-aware audience.

3. **Grafana 13 breaks file-provisioned dashboards authored in the new v2 schema.** GUI
   "Export" in Grafana 13 emits v2-schema JSON, which **cannot be loaded by file provisioning**
   (Grafana errors and the folder shows empty). Two safe paths:
   - **Chosen for the demo: pin Grafana `12.4.x`** — classic v1 dashboards provision cleanly,
     no v2 trap. Lowest stage risk.
   - If we want 13.0.2: author dashboards in **classic v1 schema** by hand and never round-trip
     them through the 13.x GUI export button.
   Either way: **reference every datasource by `uid`, not numeric `id`** — numeric datasource
   IDs are disabled by default in Grafana 13.

## Backend config requirements (will block startup if missed)

- **Prometheus v3.12**: OTLP write endpoint `/api/v1/otlp/v1/metrics` is **off by default** —
  start with `--web.enable-otlp-receiver`. Because we set `*_TEMPORALITY_PREFERENCE=cumulative`
  on the Claude Code side, we do **not** need the delta-to-cumulative feature flag. Set
  `storage.tsdb.out_of_order_time_window: 30m` to tolerate late samples.
- **Loki v3.7**: OTLP logs land on `/otlp`. Requires `limits_config.allow_structured_metadata: true`
  (default on in 3.x) **and** an active schema using **`tsdb` index + `v13`** — Loki refuses to
  start if structured metadata is on with an older schema. Max 15 labels/series; OTel resource
  attributes ride as structured metadata, not labels.
- **Jaeger v2.19**: use the unified `jaegertracing/jaeger:2.19.0` image. The old
  `jaegertracing/all-in-one` image is **no longer published** (v1 EOL was 2025-12-31). A
  defaults-only run needs **no config file**: OTLP in on 4317/4318, in-memory store, UI on 16686.
  Custom config is now a Collector-style YAML (`--config`), not v1 flags/env vars.

## Claude Code schema — verified, no changes needed

Every metric, event, span, and env var in `spec.md` sections 5–6 and 10 was confirmed
verbatim against `code.claude.com/docs/en/monitoring-usage` on 2026-06-15. Notes worth
keeping:

- Temporality default is **`delta`**; setting `cumulative` for Prometheus is correct.
- `OTEL_LOG_TOOL_DETAILS=1` gates more than file paths — also skill names, subagent types,
  MCP server/tool names, and un-redacts plugin names on `mcp_server_connection`.
- The deeper `claude_code.hook` span needs **`ENABLE_BETA_TRACING_DETAILED=1`** +
  **`BETA_TRACING_ENDPOINT`** + org allowlisting (on top of the beta-trace flag). Spec is
  right not to promise it on stage.
- `OTEL_*` is not inherited by subprocesses, but when tracing is active, Bash/PowerShell
  subprocesses **do** inherit `TRACEPARENT` (W3C context) so their spans parent correctly.
- Cost/token metrics also carry `effort`, `speed`, `plugin.name`, `mcp_tool.name` if a richer
  cost-attribution pane is wanted later.
