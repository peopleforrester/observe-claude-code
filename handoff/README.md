# Handoff docs (source of truth)

ABOUTME: Repo-controlled source for the guided Google Drive handoff set shared with the co-speaker.
ABOUTME: Edit here, then `make publish-handoff` — docs update IN PLACE (stable links), never recreated.

These are the source files for the guided walkthrough in the shared Drive folder
(`Claude_Value_with_Observability`). The repo is the source of truth; the Drive Google Docs are
generated from these, so the two can't silently drift. A reader (the co-speaker) follows the
numbered path 1 → 6 and dips into the reference shelf as needed.

## The set (source → Drive doc)

| Drive doc | Source file |
|---|---|
| `1 - START HERE` | `handoff/1-start-here.md` |
| `2 - Abstract` | `handoff/2-abstract.md` |
| `3 - How It Works` | `handoff/3-how-it-works.md` |
| `4 - Run of Show` | `docs/run-of-show.md` (canonical) |
| `5 - Your Part (Datadog)` | `handoff/5-your-part-datadog.md` |
| `6 - Try It Yourself` | `handoff/6-try-it-yourself.md` |
| `Reference - Build Spec` | `docs/spec.md` (canonical) |
| `Reference - Versions & Gotchas` | `handoff/reference-versions-and-gotchas.md` |

The Drive doc ID for each is pinned in `handoff/drive-manifest.txt`.

## Workflow

1. Edit the source file(s) above.
2. Run `make publish-handoff` (or `bash scripts/publish-handoff.sh`).
3. Each doc is updated **in place** (`gog docs write --markdown --replace`) keyed off its stable ID.

## Rules (do not break)

- **Update in place. Never delete, trash, recreate, or renumber** a doc on publish — the links must
  stay stable (the co-speaker bookmarks/follows specific docs). Version control handles versioning;
  **no version numbers in doc names.**
- To add a new doc: create it once (`gog docs create ... --parent <folder>`), then add its id to
  `drive-manifest.txt`. To rename: only with explicit OK (it's a Drive mutation).

Folder (share THIS with the co-speaker):
https://drive.google.com/drive/folders/1390BXLxO-c-TzchvzmQUaAqjJfdyQJ73

Override the account with the `HANDOFF_ACCOUNT` env var.
