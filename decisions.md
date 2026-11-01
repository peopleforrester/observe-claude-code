# decisions.md: observe-claude-code

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

**Built from:** this repo is the source; the demo is written here. The Toronto
standby deck, `peopleforrester/reading-agent-mcp-calls-through-otel`, is a separate repo built from
this one (Michael, 2026-10-05: each talk has its own repo; source repos are read, never written).
`tests/test_repo_identity.py` fails if any of these pointers goes missing.

## 2026-11-01 · An unreachable Collector skips the replay pass in --loop and fails a single pass (#23)

**Decision:** when `demo/replay/replay.py` cannot reach the Collector at all (refused connection,
DNS failure, socket timeout: any `OSError` out of `post()`), `--loop` prints a warning, skips the
rest of that pass, and tries again after `--interval`. A single pass (no `--loop`) exits non-zero
with "Collector unreachable at <endpoint>: <reason>" instead of a traceback. A 4xx/5xx rejection
still warns per record and moves on, as #13 decided.

**Why the pass, not the record:** a down Collector fails every record the same way, and with the
10-second `urlopen` timeout, skipping record by record could stall a pass for 10 seconds per record.
Skipping the pass costs at most one timeout per interval, and the next pass re-shifts the whole
capture to the new "now", so nothing is lost by dropping the rest of the failed pass.

**Why a single pass still fails:** a one-shot replay is run by hand or by the integration test,
which checks the exit code; a silent zero exit with nothing sent would hide a dead Collector.
`tests/test_replay_unit.py` drives both paths against a closed loopback port.
