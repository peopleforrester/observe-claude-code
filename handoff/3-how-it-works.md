# 3 — How It Works

The demo in plain terms, so you can grok it without reading the full build spec (that's on the
reference shelf if you want the detail).

## One idea

A coding agent (Claude Code) emits OpenTelemetry. **One Collector** receives it and fans the
**same stream** to two places at once: an open CNCF stack and a commercial backend (Datadog). The
audience sees identical telemetry in both, side by side, and decides what they'd operate themselves.

```
Claude Code session
   │  OTLP (metrics + events + beta traces)
   ▼
OpenTelemetry Collector ──► Prometheus (metrics) ┐
   │                    ──► Loki (events)         ├─► Grafana dashboard  ◄─ open CNCF stack
   │                    ──► Jaeger (traces)       ┘
   └────────────────────►  Datadog (same OTLP)    ◄─ commercial backend (your part)
```

## What's on screen — three questions

The dashboard answers three things with real telemetry, not narration:

- **Productivity** — sessions, lines changed, commits, active time. The honest read: activity isn't
  outcomes. Is the agent moving real work or just busy?
- **Cost** — spend by model, tokens by type. Where the money goes and where it stops earning.
- **Security** — which tools and MCP servers ran, and which were **allowed or denied**.

## The security moment

The scripted session calls a custom "prod-api" MCP server. A benign `get_status` read is **allowed**;
a sensitive `deploy` is **denied** by a policy hook, which shows up as a `tool_decision = reject`
event — the agent tried to touch prod and the guardrail stopped it, visible in the telemetry.

## The open-standard beat (Weaver)

We codified the agent's telemetry as an OpenTelemetry **semantic-convention registry** and validate
the live stream against it with OTel Weaver — showing which attributes conform and where the GenAI
conventions are still moving (`gen_ai.system` → `gen_ai.provider.name`).

## The safety net

The whole thing can run **offline**: the Collector captures a real session, and a replayer re-emits
it with fresh timestamps so the dashboards move with no live agent and no conference wifi.

## Why it matters for the talk

Everything rides one open substrate — OpenTelemetry and the OTel GenAI semantic conventions — that
any MCP-speaking agent can adopt. The CNCF stack vs. Datadog comparison is a real build-versus-buy
decision on that substrate, not a product pitch.
