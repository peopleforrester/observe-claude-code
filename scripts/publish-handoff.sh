#!/usr/bin/env bash
# ABOUTME: Publishes the handoff docs to Drive by UPDATING EACH DOC IN PLACE — links stay stable.
# ABOUTME: Keyed off stable doc IDs in handoff/drive-manifest.txt. Never deletes, trashes, or recreates.
set -euo pipefail

ACCOUNT="${HANDOFF_ACCOUNT:-michaelrishiforrester@gmail.com}"
FOLDER_ID="${HANDOFF_FOLDER_ID:-1390BXLxO-c-TzchvzmQUaAqjJfdyQJ73}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
MANIFEST="handoff/drive-manifest.txt"

command -v gog >/dev/null 2>&1 || { echo "gog CLI not found on PATH" >&2; exit 1; }
[ -f "${MANIFEST}" ] || { echo "manifest not found: ${MANIFEST}" >&2; exit 1; }

echo "Updating handoff docs in place (stable links)..."
while IFS='|' read -r id title src; do
    case "${id}" in ''|\#*) continue ;; esac
    [ -f "${src}" ] || { echo "  MISSING source: ${src}" >&2; exit 1; }
    # In-place content replacement — the doc ID/link is preserved.
    gog docs write "${id}" --file "${src}" --markdown --replace \
        --account "${ACCOUNT}" --no-input >/dev/null
    printf '  updated: %-32s <- %s\n' "${title}" "${src}"
done < "${MANIFEST}"

echo "Done. Folder: https://drive.google.com/drive/folders/${FOLDER_ID}"
