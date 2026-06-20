# 2 — Abstract

The submitted talk abstract — the source of truth for what we promised the conference. Keep the
demo and the slides faithful to this.

**Event:** AGNTCon + MCPCon North America 2026 (AAIF), San Jose, Oct 22–23.
**Format:** Session Presentation (25 minutes). **Audience level:** Intermediate.
**Topic:** Building Reliable Agent Systems.
**Speakers:** Michael Forrester (Accenture) + Nick Isaacs (Datadog).

## Session title

> What Does a Good Agent Look Like? Observing Claude Code in Production With OpenTelemetry

## Description

> You feel faster with a coding agent. Feeling faster and being faster are not the same thing, and
> most teams cannot tell which one they are running. An agentic coding tool plans, calls tools and
> MCP servers, and edits your systems, and it emits all of it over OpenTelemetry. The production
> question is what that telemetry should tell you. Are your engineers more productive or just
> busier? Where does the spend go, and where does the agent stop earning it? What does good agent
> behavior look like for a given role, and what is the agent touching when no one is watching? This
> session works those questions through real agent telemetry: what an agent like Claude Code exposes
> over the OTel GenAI semantic conventions, which signals matter for productivity, cost, and
> security, and how much to keep before you are paying to store noise. Two organizations share what
> they collect on their own engineers and what they act on, then a live demo runs the same agent
> telemetry through an open CNCF stack, OpenTelemetry into Prometheus, Loki, Jaeger, and Grafana,
> and a commercial backend side by side, so you can decide what to operate yourself.

## Benefits to the ecosystem

> Agentic coding tools now run inside most engineering organizations, and every one of them sits on
> top of the same open plumbing: agents emit over OpenTelemetry, and the OTel GenAI semantic
> conventions are becoming the shared way to describe what an agent and its MCP tool calls actually
> do. This talk helps the ecosystem treat that telemetry as a first-class signal rather than an
> afterthought. Attendees learn which signals are worth keeping for productivity, cost, and
> security, how to define what good agent behavior looks like by role, and how to watch the boundary
> where an agent meets sensitive systems through its MCP servers. Because the same agent telemetry
> runs through an open CNCF stack and a commercial backend side by side, attendees leave able to make
> a vendor-neutral build-versus-buy decision on an open OTLP substrate that any MCP-speaking agent
> can adopt.

## Framing guardrail (both speakers)

The CFP cuts talks featuring closed-source tech or reading as sales pitches. OpenTelemetry, the OTel
GenAI semantic conventions, and the open CNCF stack are the spine; Claude Code is "an agent that
emits telemetry"; the commercial backend stays generic on slides.
