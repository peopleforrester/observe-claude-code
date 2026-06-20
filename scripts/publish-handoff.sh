#!/usr/bin/env bash
# ABOUTME: Publishes the 5 numbered handoff docs from the repo to the shared Google Drive folder.
# ABOUTME: The repo is the source of truth; Drive is a build artifact. Run after editing a source.
set -euo pipefail

# The shared folder is stable (share THIS with Nick). Individual doc IDs change on each republish,
# so link people to the folder, not to a specific doc.
FOLDER_ID="${HANDOFF_FOLDER_ID:-1390BXLxO-c-TzchvzmQUaAqjJfdyQJ73}"
ACCOUNT="${HANDOFF_ACCOUNT:-michaelrishiforrester@gmail.com}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

command -v gog >/dev/null 2>&1 || { echo "gog CLI not found on PATH" >&2; exit 1; }

# Drive title | repo source file. Order is the numbered reading sequence.
# 3 and 4 are sourced from the canonical docs/ files (no in-repo duplication).
read -r -d '' MAPPING <<'MAP' || true
1 - START HERE|handoff/1-start-here.md
2 - Abstract|handoff/2-abstract.md
3 - Build Spec|docs/spec.md
4 - Run of Show|docs/run-of-show.md
5 - Your Part (Datadog)|handoff/5-your-part-datadog.md
MAP

echo "Publishing handoff docs to Drive folder ${FOLDER_ID} (account: ${ACCOUNT})..."
while IFS='|' read -r title src; do
    [ -z "${title}" ] && continue
    [ -f "${src}" ] || { echo "  MISSING source: ${src}" >&2; exit 1; }

    # Trash any existing doc(s) with this exact title, then recreate from the repo source.
    existing=$(gog drive ls --parent "${FOLDER_ID}" --account "${ACCOUNT}" --plain --no-input --max 100 2>/dev/null \
        | awk -F'\t' -v t="${title}" 'NR>1 && $2==t {print $1}')
    for id in ${existing}; do
        gog drive delete "${id}" --force --account "${ACCOUNT}" --no-input >/dev/null 2>&1 || true
    done

    gog docs create "${title}" --file="${src}" --parent "${FOLDER_ID}" \
        --account "${ACCOUNT}" --no-input --plain >/dev/null
    printf '  published: %-26s <- %s\n' "${title}" "${src}"
done <<< "${MAPPING}"

echo "Done. Folder: https://drive.google.com/drive/folders/${FOLDER_ID}"
