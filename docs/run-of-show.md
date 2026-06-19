# Run of Show — AGNTCon + MCPCon NA 2026

ABOUTME: The 25-minute stage sequence, what's shown each segment, who drives, and the fallbacks.
ABOUTME: Datadog is primary on stage; the CNCF stack is the fallback. Vendor stays generic in slides.

**Session:** 25-minute Session. Michael Forrester (primary) + Nick Isaacs (Datadog, co-speaker).
**Telemetry source:** one Claude Code session emitting OTLP to one Collector, fanned to a commercial
backend (Datadog) and the open CNCF stack side by side.

## Reliability posture (decide once, hold all talk)

- **Canned replay is primary** — a recorded session re-emitted so telemetry is deterministic
  regardless of network (Phase 6, Michael).
- **Live run is the backup** if the room network holds.
- **Pre-recorded screen capture is the floor** — narrate over it if everything network-dependent
  fails.
- **The CNCF dashboards are the fallback surface** if the Datadog path isn't ready or misbehaves.

## Segments

| Time | Segment | On screen | Drives | Notes / fallback |
|---|---|---|---|---|
| 0–4 | Setup / framing | Slides: two orgs, what each collects on its own engineers and acts on | Michael | Framing only, no live tool |
| 4–18 | **Live demo** (the body) | One session's telemetry in the commercial backend **and** the CNCF stack, side by side. Walk **productivity → cost → security**, switching panes | Michael (open stack), Nick (Datadog view) | Canned replay primary; if cost runs long, cut cost narration first (see cut rule) |
| — | Security close of the demo | The trace waterfall + the **denied deploy** (`tool_decision=reject`) at the MCP boundary | Michael | This is the AGNTCon center of gravity — do not cut |
| 18–23 | Build vs buy | What the open stack gives free, what a commercial backend buys you, where each stalls | Michael + Nick | Keep vendor generic — no product tour |
| 23–25 | Close | The diminishing-returns line + the reframe (probabilistic agents, deterministic requirements) | Michael | The reframe stays off the abstract; it's the payoff |

## Cut rule (if the clock runs short)

Drop the **cost** pane narration first; keep **productivity** and **security**, since security is the
AGNTCon center of gravity.

## Who drives what

- **Michael:** the whole open spine on stage — the session, the Collector fan-out story, the Grafana
  panes, the security moment (denied deploy at the MCP boundary), the framing and the close.
- **Nick:** the commercial-backend (Datadog) view of the same stream during the body and the
  build-vs-buy segment — kept generic, framed as "what an org collects," not a product tour.

## Vendor-neutrality discipline (CFP requirement)

The CFP cuts talks that read as sales pitches. OpenTelemetry, the OTel GenAI semantic conventions,
and the CNCF stack are the spine; the agent is "an agent that emits telemetry"; the commercial
backend stays generic on slides. This holds for both speakers' halves.

## Open dependencies

- Datadog integration + views are **parked until approval (expected July 2026)** — Nick's scope
  (see `docs/ownership.md`). The run of show is authored so the CNCF stack alone can carry the
  entire demo if Datadog isn't ready.
- Re-verify the telemetry schema (traces are beta) the week of the event.
