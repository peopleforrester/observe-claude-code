# Handoff docs (source of truth)

ABOUTME: Repo-controlled source for the numbered Google Drive handoff set shared with the co-speaker.
ABOUTME: Edit here, then `make publish-handoff` — Drive is a build artifact, never hand-maintained.

These are the source files for the numbered onboarding sequence in the shared Drive folder
(`Claude_Value_with_Observability`). The repo is the source of truth; the Drive Google Docs are
generated from these by the publish script, so the two can't silently drift.

## Mapping (source → Drive doc)

| Drive doc | Source file |
|---|---|
| `1 - START HERE` | `handoff/1-start-here.md` |
| `2 - Abstract` | `handoff/2-abstract.md` |
| `3 - Build Spec` | `docs/spec.md` (canonical — not duplicated here) |
| `4 - Run of Show` | `docs/run-of-show.md` (canonical — not duplicated here) |
| `5 - Your Part (Datadog)` | `handoff/5-your-part-datadog.md` |

## Workflow

1. Edit the source file(s) above.
2. Run `make publish-handoff` (or `bash scripts/publish-handoff.sh`).
3. The script trashes the matching docs in the folder and recreates them from the current sources.

## Caveat

Republishing **changes individual doc IDs** (the script recreates them). The **folder link is
stable** — share the folder with the co-speaker, not deep links to individual docs:
https://drive.google.com/drive/folders/1390BXLxO-c-TzchvzmQUaAqjJfdyQJ73

Override the target folder/account with `HANDOFF_FOLDER_ID` / `HANDOFF_ACCOUNT` env vars.
