# Design Analysis and Build Plan (rev1, 2026-06-15)

ABOUTME: Architecture decisions and phased task breakdown for the observe-claude-code demo.
ABOUTME: Derived from spec.md, corrected by versions.md. Source of truth for build sequencing.

This sits between `spec.md` (the talk-anchored intent) and the build. It records the
design decisions, the open questions that need Michael's call, and the phased task list.
Read `versions.md` alongside it — several spec details are now stale.

## 1. Target shape

One netcup VPS. Docker Compose, not Kubernetes. The abstract mentions EKS/Helm, but that
is the aspirational KubeCon framing; the **stage demo runs on Compose** for determinism and
because the VPS has no cluster. A single Claude Code session emits OTLP to one Collector,
which fans the identical stream to (a) the open CNCF stack and (b) one commercial backend.

```
Claude Code (CLI, env from env/claude-code.env)
   | OTLP grpc :4317   metrics + logs/events + traces(beta)
   v
OTel Collector Contrib v0.154.0  (one config, 3 pipelines, 2 destinations each)
   metrics ─┬─ prometheusremotewrite ─► Prometheus v3.12 ─┐
            └─ otlp (datadog) ──────────────────────────► Datadog
   logs ────┬─ otlphttp/loki ─────────► Loki v3.7 ────────┤
            └─ datadog ─────────────────────────────────► Datadog
   traces ──┬─ otlp ──────────────────► Jaeger v2.19 ─────┘
            └─ datadog                                     Grafana 12.4 reads Prom/Loki/Jaeger
```

## 2. Design decisions (made, with rationale)

- **Compose on the VPS** for the stage; EKS stays a talking point only.
- **Collector Contrib image**, one `config.yaml`, three pipelines — the fan-out has to be
  legible on one screen, so no second collector.
- **Loki via `otlphttp`** (the loki exporter is gone — see versions.md #1).
- **Grafana 12.4.x** to dodge the v13 v2-schema provisioning trap; revisit only if a 13-only
  feature is needed.
- **Cumulative temporality set at the Claude Code source**, so Prometheus needs only
  `--web.enable-otlp-receiver`, no delta feature flags.
- **Privacy gates stay off** (`OTEL_LOG_USER_PROMPTS`, `_TOOL_CONTENT`, `_RAW_API_BODIES`);
  `OTEL_LOG_TOOL_DETAILS=1` stays on. This is itself a "what good looks like" slide.

## 3. Open questions (need Michael's call before/while building)

1. **Metrics path to Prometheus**: `prometheusremotewrite` (push, shown above) vs pushing to
   Prometheus's native OTLP receiver via `otlphttp`. Remote write is the battle-tested path and
   reads cleanly on stage; native OTLP keeps the "it's all OTLP" story purer. Leaning remote write.
2. **Replay mechanism** — the highest-risk task. How do we make the offline replay deterministic?
   Options in section 5, Phase 6. Need a direction before building that phase.
3. **Commercial backend = Datadog** confirmed (Nick co-presents) — but is a DD API key /
   intake available on the VPS for the build, or do we develop against Honeycomb/SigNoz and
   swap the exporter for the final rehearsal?
4. **Which MCP server** does the scripted session feature? It needs an obvious "sensitive
   boundary" so the security pane and the denied-tool trace land. (A filesystem MCP scoped to a
   sandbox dir, or a custom one hitting a fake "prod" API, are the candidates.)

## 4. Repo layout (from spec §9, adjusted)

```
observe-claude-code/
  README.md
  docs/{spec,abstract,versions,design}.md
  env/claude-code.env
  collector/config.yaml
  compose/docker-compose.yml
  prometheus/prometheus.yml
  loki/loki-config.yaml
  grafana/provisioning/datasources/datasources.yaml
  grafana/provisioning/dashboards/dashboards.yaml
  grafana/dashboards/observe-claude-code.json   # single dashboard, 3 sections
  demo/session.md
  demo/target/                                   # throwaway repo the agent edits
  demo/replay/                                   # canned telemetry + replay script
  slides/
```

## 5. Phased task breakdown

Build order gates on the done-criteria in spec §3. Each phase ends green before the next starts.

### Phase 0 — Scaffold
- Create the directory tree and a README skeleton (what it is, how to run, env explained).
- `.gitignore` (compose volumes, captured replay artifacts if large, any `*.local` env).
- Decide secret handling for `DD_API_KEY` (env-file symlink into `~/secrets`, never committed).

### Phase 1 — Compose stack stands up (pinned versions)
- `compose/docker-compose.yml` with the five services at the versions in versions.md.
- `prometheus/prometheus.yml` + `--web.enable-otlp-receiver`, `out_of_order_time_window: 30m`.
- `loki/loki-config.yaml` with tsdb + v13 schema, `allow_structured_metadata: true`.
- Jaeger defaults (no config file), ports 4317/4318/16686.
- Grafana provisioning: datasources by **uid** (prometheus/loki/jaeger), `tracesToLogsV2`.
- **Done when** all five containers are healthy and Grafana shows three connected datasources.

### Phase 2 — Collector config
- `collector/config.yaml`: otlp receiver (4317/4318), batch processor, three pipelines, each
  with an open exporter + the datadog exporter.
- **Done when** a `telemetrygen`-style or hand-rolled OTLP probe lands metrics in Prometheus,
  a log line in Loki, and a span in Jaeger — and the same in Datadog.

### Phase 3 — Claude Code env file
- `env/claude-code.env` = verified block from spec §5 (schema confirmed in versions.md).
- **Done when** `source`-ing it and running a trivial `claude` session produces movement in
  both destinations within the export interval.

### Phase 4 — Dashboard
- One Grafana dashboard, classic v1 schema, three sections: productivity (Prom), cost (Prom),
  security (Loki events + Jaeger trace link).
- **Done when** all three panes render real data from a live session and the trace waterfall
  is reachable from the security section.

### Phase 5 — Scripted session
- `demo/session.md`: fixed prompt sequence — edits files in `demo/target/`, runs Bash, calls
  one MCP server, and hits one **denied** tool decision.
- Throwaway `demo/target/` repo + the chosen MCP server wired into the session.
- **Done when** the sequence reliably produces the productivity/cost/security story end to end.

### Phase 6 — Offline replay (highest risk)
- Capture: add a `file` exporter to the collector (or a parallel capture collector) to record
  the real session's OTLP as JSON into `demo/replay/`.
- Replay: a script that reads the captured signals and re-emits them over OTLP to the collector
  with freshened timestamps, so dashboards move without network or a live agent.
- **Done when** the whole side-by-side reproduces from the canned data with the VPS offline.

### Phase 7 — Vendor parity + rehearsal
- Confirm Datadog shows the same productivity/cost/security views from the same stream.
- Full dry run on the VPS via tmux, split screen; record the screen-capture fallback.
- **Done when** spec §3 criteria 1–5 all pass and a narrated screen capture exists as backup.

## 6. Risk register (build-facing)

- **Replay determinism** (Phase 6) is the thing most likely to eat time. If it slips, the
  pre-recorded screen capture (Phase 7) is the floor — never go on stage depending on wifi.
- **Schema drift before October**: traces are beta; re-run the four verification passes the
  week of the event.
- **Datadog turning into a product tour**: keep the vendor pane to the same three views, no more.
- **Loki schema/startup**: the tsdb+v13 requirement is a hard startup gate — get Phase 1 green
  before anything else.
