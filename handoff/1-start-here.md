# 1 — START HERE

**Talk:** *What Does a Good Agent Look Like? Observing Claude Code in Production With
OpenTelemetry* — AGNTCon + MCPCon NA 2026 (San Jose, Oct 22–23). A 25-minute session.
**Co-speakers:** Michael Forrester (Accenture, primary) + Nick Isaacs (Datadog, co-speaker).

## What this is

A single coding-agent session emits OpenTelemetry, and one Collector fans the **same stream** to a
commercial backend (Datadog) and an open CNCF stack (Prometheus, Loki, Jaeger, Grafana). On screen,
the demo answers three questions: **productivity, cost, security.**

## Where it stands (as of June 2026)

The open CNCF half is **built and validated** — a real session's telemetry flows through the
Collector into all three backends and onto a Grafana dashboard, including a denied "deploy to prod"
security moment. 36 integration tests pass. The build lives in the repo, and its default branch
reflects everything:

**github.com/peopleforrester/observe-claude-code**

## Your part, in one line

**Datadog only.** You add Datadog as a second fan-out destination and build its views. Everything
else is already built. Full detail in **doc 5 — Your Part (Datadog)**.

## Read these in order

1. **START HERE** — this doc
2. **Abstract** — what we promised the conference
3. **Build Spec** — the technical reference for the demo
4. **Run of Show** — the 25-minute stage flow and who drives what
5. **Your Part (Datadog)** — exactly what's yours, what's not, and where it plugs in

## Backend roles (important)

Datadog is the **primary surface on stage**; the open CNCF stack is the **fallback** — always
present, and it carries the entire demo unchanged if the Datadog path isn't ready. On the public
slides the vendor stays **generic** ("a commercial backend") — no product tour, since the CFP cuts
talks that read as sales pitches. The open spine (OpenTelemetry, the CNCF stack, the GenAI semantic
conventions) carries the talk.

## Timeline note

The Datadog integration is the **final phase**, expected to start after approval (~July 2026). It
is self-contained and does not block anything else — the CNCF fallback is complete today.
