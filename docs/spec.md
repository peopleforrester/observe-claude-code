# observe-claude-code — Talk and Demo Build Spec (rev1)

**Talk:** What Does a Good Agent Look Like? Observing Claude Code in Production With OpenTelemetry
**Event:** AGNTCon + MCPCon NA 2026 (San Jose, Oct 22 to 23). 25-minute Session. Co-speaker Nick Isaacs (Datadog).
**Repo:** github.com/peopleforrester/observe-claude-code
**Spec date:** 2026-06-07
**Telemetry surface verified against:** code.claude.com/docs/en/monitoring-usage (fetched 2026-06-07). Confirm again before the event, since the schema is still moving (traces are beta).

Purpose of this file: define the demo so it can be built against by Claude Code on the netcup VPS, and anchor the 25-minute talk. The demo is the deliverable. Everything below serves the side-by-side telemetry moment on stage.

---

## 1. Thesis and what stays off the slides

Thesis: feeling faster is not being faster, and the telemetry an agent already emits is enough to tell the difference if you collect the right signals and stop collecting the rest. The reframe at the close (the line about probabilistic agents and deterministic requirements) is the payoff and stays out of the abstract.

Three questions the demo must answer on screen, not in narration:
1. Productivity: is the agent moving real work, or just generating activity.
2. Cost: where the spend goes and where it stops earning.
3. Security: what the agent touched, which tool calls and MCP servers ran, and which were allowed or denied.

---

## 2. 25-minute plan

- Minutes 0 to 4. Setup. Two orgs, what each collects on its own engineers and acts on. Framing only.
- Minutes 4 to 18. The live demo. One Claude Code session, the same telemetry landing in the open CNCF stack and in the commercial backend, side by side on one screen. Walk productivity, then cost, then security, switching panes.
- Minutes 18 to 23. Build versus buy read. What the open stack gives you for free, what you pay a commercial backend to avoid building, where each one stalls.
- Minutes 23 to 25. Close on the diminishing-returns line and the reframe.

Cut rule if the clock runs short: drop the cost pane narration first, keep productivity and security, since security is the AGNTCon center of gravity.

---

## 3. Demo objective and success criteria

A single Claude Code session emits metrics, events, and beta traces over OTLP to one OpenTelemetry Collector. The Collector fans out the same stream to two destinations:

- Open CNCF stack: Prometheus (metrics), Loki (events as logs), Jaeger (traces), Grafana (single dashboard across all three).
- Commercial backend: one OTLP-native vendor (Datadog for this build, since Nick is co-presenting; Honeycomb or SigNoz are drop-in alternates). Kept generic as "a commercial backend" in the abstract and on the public slides.

Done when:
1. One env file turns telemetry on and points Claude Code at the Collector.
2. A scripted Claude Code session produces visible movement in both destinations within the export interval.
3. Grafana shows productivity, cost, and security panes sourced from Prometheus, Loki, and Jaeger.
4. The commercial backend shows the same three views from the same OTLP stream.
5. A canned replay reproduces the whole thing offline, so the talk does not depend on conference wifi.

---

## 4. Architecture

```
Claude Code (CLI on the VPS)
   | OTLP (grpc, 4317)  metrics + logs/events + traces(beta)
   v
OpenTelemetry Collector (gateway)
   |-- exporter: prometheus / prometheusremotewrite  --> Prometheus --> Grafana
   |-- exporter: otlp/loki (or loki exporter)         --> Loki       --> Grafana
   |-- exporter: otlp                                 --> Jaeger     --> Grafana
   |-- exporter: otlp (vendor)                         --> commercial backend
```

One Collector, multiple exporters, three pipelines (metrics, logs, traces). The fan-out is the whole point: identical data, two homes, audience decides.

---

## 5. Claude Code telemetry configuration (verified)

Set on the VPS before launching `claude`. Source: monitoring-usage docs, 2026-06-07.

```bash
# Enable
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# Signals: metrics + events. Traces enabled separately below.
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp

# Send to the local Collector over gRPC
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Faster intervals so the stage demo moves inside a few seconds
export OTEL_METRIC_EXPORT_INTERVAL=10000   # default 60000
export OTEL_LOGS_EXPORT_INTERVAL=2000      # default 5000

# Prometheus wants cumulative; Claude Code defaults to delta
export OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative

# Security pane needs tool + MCP detail (off by default)
export OTEL_LOG_TOOL_DETAILS=1

# Traces (beta): the prompt -> tool -> MCP waterfall
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp

# Attribute the session to a role for the "good by role" framing
export OTEL_RESOURCE_ATTRIBUTES=role=backend,team.id=demo,cost_center=agntcon
```

Privacy gates, decide deliberately and say so on stage:
- `OTEL_LOG_TOOL_DETAILS=1` adds Bash commands, MCP server and tool names, file paths. Needed for the security pane.
- `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_RAW_API_BODIES` stay off. They pull in prompt text, tool output, and full API bodies including conversation history. Leaving them off is itself a "what good looks like" point: collect identity and decisions, not content.

Gotcha to call out: Claude Code does not pass `OTEL_*` to subprocesses it spawns (Bash, hooks, MCP servers, language servers). Anything you run through the Bash tool that should emit its own telemetry needs its own env in that command.

---

## 6. Signals to surface, mapped to the real schema

### Productivity pane
- Metrics: `claude_code.session.count` (`start_type` fresh/resume/continue), `claude_code.lines_of_code.count` (`type` added/removed), `claude_code.commit.count`, `claude_code.pull_request.count`, `claude_code.active_time.total` (`type` user/cli).
- The honest read on stage: lines of code and commits are activity, not outcomes. Active time versus output is the "busier or faster" tell.

### Cost pane
- Metrics: `claude_code.cost.usage` (USD, attributes `model`, `agent.name`, `skill.name`, `mcp_server.name`), `claude_code.token.usage` (`type` input/output/cacheRead/cacheCreation).
- Caveat to state out loud: cost.usage is approximate. Official billing is Console, Bedrock, or Vertex. That caveat is part of the build-versus-buy honesty.

### Security pane
- Events: `claude_code.tool_decision` (`decision` accept/reject, `source` config/hook/user_*), `claude_code.permission_mode_changed` (`from_mode`/`to_mode`/`trigger`, including escalation to `bypassPermissions`), `claude_code.mcp_server_connection` (`status`, `transport_type`, `server_scope`), `claude_code.tool_result` with `tool_parameters` carrying `mcp_server_name`, `mcp_tool_name`, Bash `full_command`.
- Traces (beta): `claude_code.interaction` root, children `claude_code.llm_request`, `claude_code.tool` with `tool.blocked_on_user` and `tool.execution`. This is the prompt-to-tool-to-MCP waterfall, and where the MCP boundary becomes visible.
- GenAI semantic convention attributes present on spans: `gen_ai.system=anthropic`, `gen_ai.request.model`, `gen_ai.response.id`, `gen_ai.tool.call.id`, `gen_ai.response.finish_reasons`. Name-drop these as the open standard the whole ecosystem can target.

---

## 7. Collector and backends

Build the Collector config with three pipelines and a vendor exporter alongside the open exporters. Keep it one file so the fan-out is legible on stage.

- Receivers: `otlp` (grpc 4317, http 4318).
- Processors: `batch`, plus `attributes`/`filter` if a cardinality trim is needed for Prometheus.
- Metrics exporters: `prometheus` or `prometheusremotewrite` to Prometheus, and the vendor OTLP exporter.
- Logs exporters: Loki (via the loki exporter or OTLP to a Loki OTLP endpoint), and the vendor OTLP exporter.
- Traces exporters: `otlp` to Jaeger, and the vendor OTLP exporter.

Backend roles, straight from the docs' own backend guidance: time-series store for metrics (Prometheus), log store for events (Loki), distributed tracing store for spans (Jaeger). The commercial backend collapses all three into one queryable surface, which is the thing buyers are paying for.

Reference to mine for ready-made compose files: github.com/anthropics/claude-code-monitoring-guide (Anthropic's ROI monitoring guide, Prometheus and OTel compose plus report templates). Use it as a starting skeleton, not the talk.

---

## 8. On-stage runbook

1. Pre-stage: Collector, Prometheus, Loki, Jaeger, Grafana, and the vendor agent all up on the VPS via tmux. Grafana dashboard and the vendor view pre-opened, split screen.
2. Canned replay primary: a recorded Claude Code session (a fixed prompt sequence that edits files, runs Bash, calls one MCP server, and hits one denied tool) replayed so the telemetry is deterministic regardless of network.
3. Live run backup: the same prompt sequence run live if the room network holds.
4. Walk the three panes in order: productivity, cost, security. End on the trace waterfall showing the MCP call and the denied tool decision.
5. Flip to the commercial backend showing the same three views, then say the build-versus-buy line.

Fallback if everything network-dependent fails: pre-recorded screen capture of the full side-by-side, narrated live.

---

## 9. Repo layout (observe-claude-code)

```
observe-claude-code/
  README.md                 # what it is, how to run, the env file explained
  env/claude-code.env       # the export block from section 5
  collector/config.yaml     # one Collector, three pipelines, two destinations
  compose/docker-compose.yml# Prometheus, Loki, Jaeger, Grafana, Collector
  grafana/dashboards/*.json # productivity, cost, security panes
  demo/session.md           # the scripted prompt sequence
  demo/replay/              # canned telemetry for offline replay
  slides/                   # exported deck, commercial side kept generic
```

Build order for Claude Code against this spec: compose stack first, Collector config second, env file third, dashboards fourth, scripted session last, then capture the replay. Gate each on the done-criteria in section 3.

---

## 10. Gotchas (verified, will bite on stage)

- Subprocess telemetry: `OTEL_*` is not inherited by Bash, hooks, or MCP servers Claude Code spawns. Section 5.
- Temporality: Prometheus needs `cumulative`; Claude Code defaults to `delta`. Wrong setting shows empty or broken metric panels.
- Security detail is opt-in: without `OTEL_LOG_TOOL_DETAILS=1`, MCP server and tool names and Bash commands are dropped, and the security pane is hollow.
- Traces are beta and double-gated: needs both `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` plus `OTEL_TRACES_EXPORTER`. The deeper `claude_code.hook` span needs an additional detailed-beta flag and allowlisting, so do not promise it on stage.
- Cost is approximate, not billing. Say it before someone in the room says it for you.
- Cardinality: `session.id` and account attributes are on by default and high cardinality. If Prometheus struggles, trim with the `OTEL_METRICS_INCLUDE_*` switches rather than dropping the signal.

---

## 11. Risks and open questions

- Schema drift: traces are beta and attribute names can change before October. Re-verify against the docs the week of the event.
- Vendor neutrality: the commercial backend is Datadog in the build because Nick co-presents. On the public slides and in the abstract it stays "a commercial backend." Do not let the vendor pane become a product tour, since this CFP rejects pitches.
- Closed-source framing: the open spine (OpenTelemetry, the CNCF stack, the GenAI conventions) carries the talk. Claude Code is the agent being observed, not the thing being sold.
- Repo readiness: observe-claude-code is in progress. It needs at least a working compose stack and README before the recording goes in front of reviewers, and before the link in the submission is worth keeping.

---

## 12. Evidence base (for the talk, not the abstract; as of May 2026)

- METR RCT (arXiv:2507.09089, Jul 2025): experienced devs 19% slower with AI while feeling 20% faster; Feb 2026 redesign kept the perception gap.
- Stack Overflow 2025 (49k+): adoption 84%, accuracy trust ~29 to 33%, distrust (46%) above trust (33%); top frustration "almost right" (66%); 45% say debugging AI code takes longer.
- DORA 2024/2025 plus Faros (10k+ devs): high adoption merged 98% more PRs, review time up 91%, org DORA flat; "AI amplifies what is already there."
- Veracode 2025: ~45% of AI-generated code carried an OWASP Top 10 vuln. GitGuardian Secrets Sprawl 2026: Claude Code-assisted commits leaked secrets ~2x baseline.
- FinOps Foundation FOCUS: multi-agent cost allocation and token attribution named as open problems.
- Honest line tying it together: the open stack shows cost, activity, and risky actions today. It cannot prove business outcomes by itself; that needs delivery metrics layered on top. That gap is the build-versus-buy decision.
