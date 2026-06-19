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

**OTLP-native everywhere.** Every hop from the collector to a backend uses `otlp`/`otlphttp`
— no `prometheusremotewrite`, no vendor-specific exporters in the open path. The commercial
backend is deferred (see decisions). OTel Weaver validates the live stream against a semconv
registry as an auxiliary "open standard" beat.

```
Claude Code (CLI, env from env/claude-code.env)
   | OTLP grpc :4317   metrics + logs/events + traces(beta)
   v
OTel Collector Contrib v0.154.0  (one config, 3 pipelines, all-OTLP exporters)
   metrics ── otlphttp ──► Prometheus v3.12  (/api/v1/otlp, native OTLP receiver)
   logs ───── otlphttp ──► Loki v3.7         (/otlp)
   traces ─── otlp ──────► Jaeger v2.19      (:4317)
                              │
                              └──► Grafana 12.4 reads Prom / Loki / Jaeger by uid

   (auxiliary) OTel Weaver live-check ── validates emitted claude_code.* + gen_ai.*
                                          attributes against a semconv registry
   (deferred)  commercial backend (Datadog) — add a second OTLP exporter per pipeline later
```

## 2. Design decisions (locked 2026-06-15)

- **Compose on the VPS** for the stage; EKS stays a talking point only.
- **Collector Contrib image**, one `config.yaml`, three pipelines — the fan-out has to be
  legible on one screen, so no second collector.
- **OTLP-native everywhere.** Metrics → Prometheus **native OTLP receiver** via `otlphttp`
  (not remote write); logs → Loki `/otlp` via `otlphttp`; traces → Jaeger via `otlp`. Keeps
  the "everything is OTLP" story pure end to end. (Loki exporter is gone anyway — versions.md #1.)
- **OTel Weaver** as an auxiliary tool: build a semconv registry covering `claude_code.*` and
  `gen_ai.*`, and run Weaver's live-check against the real stream — the "we validate the agent
  against an open standard" beat. New-to-project; **research Weaver before wiring** (Phase 0.5).
- **Grafana 12.4.x** to dodge the v13 v2-schema provisioning trap; revisit only if a 13-only
  feature is needed.
- **Cumulative temporality set at the Claude Code source**, so Prometheus needs only
  `--web.enable-otlp-receiver`, no delta feature flags.
- **Privacy gates stay off** (`OTEL_LOG_USER_PROMPTS`, `_TOOL_CONTENT`, `_RAW_API_BODIES`);
  `OTEL_LOG_TOOL_DETAILS=1` stays on. This is itself a "what good looks like" slide.
- **Offline replay = capture + re-emit OTLP** (Phase 6). The collector captures one real
  session as OTLP JSON; a script re-emits it with fresh timestamps so the panes move live from
  canned data. Keep a screen recording as the floor/fallback (Phase 7).
- **Commercial backend = Datadog, primary on stage, owned by Nick, parked until ~July 2026.**
  The emphasis shifted: Datadog is the primary on-stage surface and the open CNCF stack is the
  **fallback** (always present, carries the demo if the vendor path isn't ready). Datadog is the
  **only co-presenter scope** — Nick adds a second OTLP exporter per pipeline at the marked point
  in `collector/config.yaml`, supplies the key via `~/secrets`, and builds the Datadog views (kept
  generic in slides). Build and harden the CNCF stack first; the Datadog phase is self-contained and
  non-blocking. See `docs/ownership.md` and `docs/run-of-show.md`.
- **Demo MCP = custom "prod API" server.** A small MCP that simulates a sensitive prod-like
  API; the denied call is the "don't touch prod" boundary that makes the security pane land.

## 3. Resolved — see decisions above

All four open questions from rev1 are now decided (replay = capture+re-emit, vendor = deferred,
MCP = custom prod-API, metrics = OTLP-native receiver). The remaining unknown is **OTel Weaver
feasibility** — pending the Phase 0.5 research spike.

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
- Secret handling reserved for the deferred vendor phase (env-file symlink into `~/secrets`,
  never committed) — nothing secret needed for the open stack.

### Phase 0.5 — OTel Weaver research spike
- Research current OTel Weaver (version, `registry check` / live-check workflow, how to define
  a custom semconv registry, what "validate a live stream" actually requires). Verify against
  official docs with the 2026 year, per the new-tech rule. Write `docs/gotchas-weaver.md`.
- **Done when** we know whether Weaver can validate the live `claude_code.*`/`gen_ai.*` stream
  on stage, and at what build cost. If it's heavy, it becomes a slide, not a live step.

### Phase 1 — Compose stack stands up (pinned versions)
- `compose/docker-compose.yml` with the five services at the versions in versions.md.
- `prometheus/prometheus.yml` + `--web.enable-otlp-receiver`, `out_of_order_time_window: 30m`.
- `loki/loki-config.yaml` with tsdb + v13 schema, `allow_structured_metadata: true`.
- Jaeger defaults (no config file), ports 4317/4318/16686.
- Grafana provisioning: datasources by **uid** (prometheus/loki/jaeger), `tracesToLogsV2`.
- **Done when** all five containers are healthy and Grafana shows three connected datasources.

### Phase 2 — Collector config (all-OTLP)
- `collector/config.yaml`: otlp receiver (4317/4318), batch processor, three pipelines, each
  with a single OTLP-native open exporter — `otlphttp` → Prometheus `/api/v1/otlp`, `otlphttp`
  → Loki `/otlp`, `otlp` → Jaeger `:4317`. No remote write, no vendor exporter yet.
- **Done when** a `telemetrygen`-style or hand-rolled OTLP probe lands metrics in Prometheus,
  a log line in Loki, and a span in Jaeger.

### Phase 3 — Claude Code env file
- `env/claude-code.env` = verified block from spec §5 (schema confirmed in versions.md).
- **Done when** `source`-ing it and running a trivial `claude` session produces movement in
  both destinations within the export interval.

### Phase 4 — Dashboard
- One Grafana dashboard, classic v1 schema, three sections: productivity (Prom), cost (Prom),
  security (Loki events + Jaeger trace link).
- **Done when** all three panes render real data from a live session and the trace waterfall
  is reachable from the security section.

### Phase 5 — Scripted session + custom prod-API MCP
- Build the custom "prod API" MCP server: a small server exposing a benign read tool and one
  sensitive write/deploy tool that the session is configured to **deny** — the "don't touch
  prod" boundary.
- `demo/session.md`: fixed prompt sequence — edits files in `demo/target/`, runs Bash, calls
  the prod-API MCP's read tool (allowed), then trips the denied write tool.
- Throwaway `demo/target/` repo wired into the session.
- **Done when** the sequence reliably produces the productivity/cost/security story end to end,
  with the denied MCP write visible as a `tool_decision` reject and in the trace waterfall.

### Phase 6 — Offline replay (highest risk)
- Capture: add a `file` exporter to the collector (or a parallel capture collector) to record
  the real session's OTLP as JSON into `demo/replay/`.
- Replay: a script that reads the captured signals and re-emits them over OTLP to the collector
  with freshened timestamps, so dashboards move without network or a live agent.
- **Done when** the whole side-by-side reproduces from the canned data with the VPS offline.

### Phase 7 (FINAL) — Datadog backend + rehearsal — OWNER: Nick, parked until ~July 2026
- Nick adds the Datadog OTLP exporter as a second exporter on each pipeline at the marked point in
  `collector/config.yaml`, supplies the key via `~/secrets`, and builds the Datadog views (primary
  on-stage surface, generic in slides). Confirms parity: the same productivity/cost/security views
  from the identical OTLP stream the CNCF stack receives.
- Joint: full dry run via tmux, split screen; record the screen-capture fallback (the floor if
  anything network-dependent fails on stage).
- **Done when** Datadog shows the three views from the same stream, the run of show is rehearsed,
  and a narrated screen capture exists as backup. Non-blocking: if not ready by the event, the CNCF
  fallback carries the demo. See `docs/ownership.md`.

## 6. Risk register (build-facing)

- **Replay determinism** (Phase 6) is the thing most likely to eat time. If it slips, the
  pre-recorded screen capture (Phase 7) is the floor — never go on stage depending on wifi.
- **Schema drift before October**: traces are beta; re-run the four verification passes the
  week of the event.
- **Datadog turning into a product tour**: keep the vendor pane to the same three views, no more.
- **Loki schema/startup**: the tsdb+v13 requirement is a hard startup gate — get Phase 1 green
  before anything else.

## 7. Forward-looking close and the sequel project

The talk closes by pointing past observation to enforcement. The security pane already shows
the agent's risky actions — the denied `tool_decision`, the MCP boundary in the trace waterfall.
The natural next question, and the close: *we can **see** the denied tool decision — could an LLM
author the deterministic Falco/Kyverno rule that **enforces** it? That's a whole other talk.*

That other talk is a **separate, adjacent project** (`idea-dynamic-software-blocker`): LLM-authored,
human-gated, deterministic detection rules sourced from agent/GenAI telemetry. Keep it separate —
this is the observe half; that is the enforce half. Cross-linked here only so the close lands and
the two CFPs reference each other.

Two notes carried over from that project's research, reconciled against our own verification:

- **Conformance nuance (already covered).** Claude Code's spans are GenAI-*flavored*, not fully
  semconv-conformant: first-party span names (`claude_code.*`), `gen_ai.system` not yet
  `gen_ai.provider.name`, a partial `gen_ai.*` subset. We already own this — versions.md records
  the rename in flight, and the **Weaver live-check beat is exactly the "validate against the
  evolving standard, watch the advisories" moment.** No extra build needed.
- **Correction to that project's doc.** It claims "no distinct execute-tool/MCP span." Our
  verification (against the live monitoring-usage doc) shows otherwise: there **is** a
  `claude_code.tool.execution` span, the tool span carries `gen_ai.tool.call.id`, and
  `mcp_server_name`/`mcp_tool_name` are present — so **the MCP boundary is visible in the trace**,
  which is the spine of our security pane. Our data is the more precise source; don't let the
  sibling doc's framing weaken the trace story.

We deliberately do NOT pull in that project's OTTL span-normalization layer (Weaver covers the
standard-conformance beat for a 25-min slot) or its adversarial/poisoning research (too deep here;
it belongs to the sequel).
