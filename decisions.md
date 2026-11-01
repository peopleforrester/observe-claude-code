# decisions.md — observe-claude-code

Append-only. Add each new decision at the end with its date and the issue it came from; never edit
or remove an earlier entry. Decisions taken before 2026-11-01 are in `PROJECT_STATE.md` ("Locked
decisions") and `docs/design.md`; they are not copied here.

## 2026-11-01 · The README says who this repo is and points at the knowledge repos (#10)

**Decision:** README.md gains a "This talk" table that gives the title, the speakers, the argument,
the form, the event, the status, what the repo is built from, where it is registered, and the
sibling repo. AGENTS.md (CLAUDE.md is a symlink to it) names talks-knowledge for the register
entry and abstracts, conference-knowledge for event state, and the sibling repo.

**Why:** talks-knowledge asked on 2026-10-14 that every talk repo say who it is and point at
talks-knowledge, which is the source of truth for the register (`talks/register.md`, row 8 for
this talk) and the abstracts.

**Event state stays a pointer.** The Event row says only that nothing is booked or delivered as
of 2026-11-01, and names conference-knowledge for submissions, dates and bookings. It lists no
submissions, because #7 removed copied conference facts from this repo and a copied list would go
stale.

**Built from:** this repo is a source, not a derivative: the demo is written here. The Toronto
standby deck, `peopleforrester/reading-agent-mcp-calls-through-otel`, is a separate repo built from
this one (Michael, 2026-10-05: each talk has its own repo; source repos are read, never written).
`tests/test_repo_identity.py` fails if any of these pointers goes missing.
