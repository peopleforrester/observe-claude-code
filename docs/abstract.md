# AGNTCon + MCPCon NA 2026 — Claude Code + OTel Session Submission (rev3)

**Ordered to match the live Sessionize form top to bottom. Paste straight down. Reference is below the divider, not submitted.**

**Event:** AGNTCon + MCPCon North America 2026 (AAIF), San Jose McEnery Convention Center, Oct 22–23.
**Submit via:** sessionize.com/agntcon-mcpcon-na-2026
**CFP closes:** Sun Jun 7, 11:59 PM PDT = **Mon Jun 8, 1:59 AM Austin**. Notifications Jul 17. Schedule Jul 21.
**Speakers:** Michael Forrester (Accenture) + Nick Isaacs (Datadog), co-speaker (confirmed). Session, not a Panel.

**rev3 changes:** verified prior-talk recording + demo repo links appended to Benefits (field now 1,179 chars, under 1,200). rev2 set the agent-forward title and the live-demo Description.

---

## READ THIS FIRST

1. **25-minute plan.** The slot is a 25-min Session. The shape: open with the two-org framing as setup (what each org collects on its own engineers and acts on), then the live demo of the same agent telemetry through the open CNCF stack and a commercial backend side by side is the body, close on the diminishing-returns line. The demo carries the talk. The fuller two-org narrative treatment is the KubeCon NA main 35-min version.

2. **Closed-source / vendor-pitch is the rejection risk.** The CFP states talks featuring closed-source tech or reading as sales pitches usually get cut. OpenTelemetry, the OTel GenAI semantic conventions, and the open CNCF stack are the spine; Claude Code is "an agent that emits telemetry"; the commercial backend stays generic. Keep the slides and Nick's half the same way.

3. **Topic fit is real.** "Building Reliable Agent Systems" names observability, debugging, resilience, and performance.

---

## SESSION (paste order)

**Session Title:**
> What Does a Good Agent Look Like? Observing Claude Code in Production With OpenTelemetry

*(alt: "What Is the Agent Actually Doing? Reading Claude Code Through OpenTelemetry" — "OpenTelemetry" vs "OTEL" is your call)*

**Description** *(1,136 chars; limit 1,200):*
> You feel faster with a coding agent. Feeling faster and being faster are not the same thing, and most teams cannot tell which one they are running. An agentic coding tool plans, calls tools and MCP servers, and edits your systems, and it emits all of it over OpenTelemetry. The production question is what that telemetry should tell you. Are your engineers more productive or just busier? Where does the spend go, and where does the agent stop earning it? What does good agent behavior look like for a given role, and what is the agent touching when no one is watching? This session works those questions through real agent telemetry: what an agent like Claude Code exposes over the OTel GenAI semantic conventions, which signals matter for productivity, cost, and security, and how much to keep before you are paying to store noise. Two organizations share what they collect on their own engineers and what they act on, then a live demo runs the same agent telemetry through an open CNCF stack, OpenTelemetry into Prometheus, Loki, Jaeger, and Grafana, and a commercial backend side by side, so you can decide what to operate yourself.

**Topic:** Building Reliable Agent Systems *(secondary if asked: Open Infrastructure and Tooling — tracing)*

**Session Format:** Session Presentation (25 minutes)

**Audience Level:** Intermediate

**Benefits to the Ecosystem** *(answers "How will your proposed talk positively impact MCP and the broader agent landscape ecosystem?" — prose + links, 1,179 chars):*
> Agentic coding tools now run inside most engineering organizations, and every one of them sits on top of the same open plumbing: agents emit over OpenTelemetry, and the OTel GenAI semantic conventions are becoming the shared way to describe what an agent and its MCP tool calls actually do. This talk helps the ecosystem treat that telemetry as a first-class signal rather than an afterthought. Attendees learn which signals are worth keeping for productivity, cost, and security, how to define what good agent behavior looks like by role, and how to watch the boundary where an agent meets sensitive systems through its MCP servers, which is exactly where the security questions live. Because the same agent telemetry runs through an open CNCF stack and a commercial backend side by side, attendees leave able to make a vendor-neutral build versus buy decision on an open OTLP substrate that any MCP-speaking agent can adopt. The point is shared, open observability practice for agents and MCP while the standards are still forming. Prior KubeCon EU 2026 talk: https://www.youtube.com/watch?v=FdBkGi08SI4. Demo repo (in progress): github.com/peopleforrester/observe-claude-code.

*(Links verified Jun 7, 2026: the YouTube URL resolves to your CNCF Cloud Native University recording. Drop the repo link if it is still empty when reviewers look during Jun 8 to Jul 17.)*

**Presented this talk before?:** No

**Co-speakers:** Nick Isaacs (Datadog) — enter his email in the co-speaker field so he gets the invite.

**Are you both the submitter and speaker?:** Yes (Michael primary, Nick co-speaker)

**Code of Conduct / Inclusivity / Content Quality:** ✓ check each

---

## SPEAKER (already in your profile)

Tagline, bio (500), Fediverse @peopleforrester, Company Accenture, Title "AI Workforce Transformation Specialist," Country US, demographics — all set. No change needed.

---
---

## REFERENCE (not form fields)

### Why this fits AGNTCon NA
The event is for builders advancing reliable, scalable, secure agent systems in production, spanning MCP and the broader agent landscape. "Building Reliable Agent Systems" names observability outright. The MCP angle is honest but light: Claude Code calls MCP servers, MCP tool-call telemetry rides the same OTLP path, and the model-to-tool boundary (where MCP lives) is where the security signals are. Lead agent operability and the open telemetry standard; bring MCP in at that boundary. Not an MCP-protocol talk, and the abstract does not pretend to be.

### 25-minute plan
- **Setup (brief):** two orgs, what each collects on its own engineers and acts on. Framing, not a deep tour.
- **Body (the live demo):** the same agent telemetry running through the open CNCF stack and a commercial backend, side by side, on stage. This is where the time goes.
- **Close:** the diminishing-returns line, where an agent session stops being worth its output and how the data shows it before finance does.
- The fuller two-org narrative belongs in the KubeCon NA main 35-min slot.

### Stack (OSS-first, the spine)
OpenTelemetry Collector (gateway on EKS) → fan-out. Prometheus (metrics), Loki (logs/events via OTLP), Jaeger v2 (traces), Grafana (dashboards), Kubernetes + Helm. Commercial backend stays generic in the abstract and on stage.

### Speakers
- Michael Forrester (Accenture, primary): what an enterprise collects across roles, the define-good method, the diminishing-returns line.
- Nick Isaacs (Datadog, co-speaker): what an org collects on its own engineers and acts on. Frame as "what an org collects," not a product tour.

### Evidence base (for the talk, not the abstract; as of May 2026)
- METR RCT (arXiv:2507.09089, Jul 2025): experienced devs 19% slower with AI while feeling 20% faster; Feb 2026 redesign kept the perception gap.
- Stack Overflow 2025 (49k+): adoption 84%, accuracy trust ~29-33%, distrust (46%) > trust (33%); top frustration "almost right" (66%); 45% say debugging AI code takes longer.
- DORA 2024/2025 + Faros (10k+ devs): high adoption merged 98% more PRs, review time +91%, org DORA flat; "AI amplifies what's already there."
- Veracode 2025: ~45% of AI-generated code carried an OWASP Top 10 vuln. GitGuardian Secrets Sprawl 2026: Claude Code-assisted commits leaked secrets ~2x baseline.
- FinOps Foundation FOCUS: multi-agent cost allocation and token attribution named as open problems.
- OSS to point to: OTel GenAI semantic conventions (experimental early 2026), Prometheus, Loki, Jaeger, Grafana, Claude Code native OTel export; OpenCost (no SaaS token visibility); Falco for runtime detection; OPA/Kyverno for deterministic agent policy.
- Honest line: the open stack shows cost, activity, and risky actions today; it cannot prove business outcomes alone. That is the build-vs-buy line.

### Demo build note
The side-by-side is the deliverable. Pre-build the OTel Collector fan-out so the same trace/metric/event stream lands in both Grafana (over Prometheus/Loki/Jaeger) and the commercial backend, switchable on one screen. Have a canned Claude Code session ready to replay so the telemetry is deterministic on stage, with a live run as backup if the room and network cooperate.
