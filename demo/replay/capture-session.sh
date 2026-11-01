#!/usr/bin/env bash
# ABOUTME: Capture one real scripted session's OTLP and its transcript as a pair for offline replay.
# ABOUTME: Snapshots are gitignored. Real captures carry account identifiers and prompt text; never commit them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../.."  # repo root

COMPOSE="docker compose --project-directory . -f compose/docker-compose.yml"
RAW="demo/replay/raw/otlp-capture.jsonl"
STAMP="$(date +%Y%m%d-%H%M%S)"
SNAP="demo/replay/raw/session-${STAMP}.jsonl"
TRANSCRIPT="demo/replay/raw/session-${STAMP}.transcript.jsonl"
SESSION_LOG="demo/replay/raw/session-${STAMP}.log"
# Claude Code writes each session to <config dir>/projects/<project>/<session-id>.jsonl.
PROJECTS_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}/projects"
SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

command -v docker >/dev/null 2>&1 || { echo "docker not available in this shell" >&2; exit 1; }

echo "==> Clearing the capture file and restarting the Collector for a clean capture..."
mkdir -p "$(dirname "${RAW}")"
rm -f "${RAW}"
${COMPOSE} restart collector >/dev/null
sleep 5

echo "==> Running the scripted session ${SESSION_ID} (deploy will be denied)..."
# A session that fails (e.g. "Not logged in") still exports OTLP and writes a transcript, just no
# tool spans, so stop here with its output instead of failing later at the join.
if ! OCC_SESSION_ID="${SESSION_ID}" bash demo/run-session.sh >"${SESSION_LOG}" 2>&1; then
  echo "the scripted session failed; its output (${SESSION_LOG}) ends:" >&2
  tail -n 20 "${SESSION_LOG}" >&2
  exit 1
fi

echo "==> Waiting for the export intervals to flush..."
sleep 12

[[ -s "${RAW}" ]] || { echo "no OTLP captured at ${RAW}. Is the Collector up?" >&2; exit 1; }
cp "${RAW}" "${SNAP}"
echo "==> Captured $(wc -l < "${SNAP}") OTLP records -> ${SNAP}"

SOURCE_TRANSCRIPT="$(find "${PROJECTS_DIR}" -name "${SESSION_ID}.jsonl" -print -quit 2>/dev/null || true)"
if [[ -z "${SOURCE_TRANSCRIPT}" ]]; then
  echo "no transcript for session ${SESSION_ID} under ${PROJECTS_DIR}. Did the session run?" >&2
  exit 1
fi
cp "${SOURCE_TRANSCRIPT}" "${TRANSCRIPT}"
echo "==> Captured $(wc -l < "${TRANSCRIPT}") transcript entries -> ${TRANSCRIPT}"

echo "==> Checking every captured tool span joins back to its prompt..."
python3 demo/replay/join.py --capture "${SNAP}"

echo
echo "Replay it offline (loops for a live-looking stage demo):"
echo "  python3 demo/replay/replay.py --capture ${SNAP} --loop"
echo "Join a trace from Jaeger back to its prompt:"
echo "  python3 demo/replay/join.py --capture ${SNAP} --trace <trace-id>"
echo
echo "NOTE: this pair contains account identifiers and prompt text. It is gitignored. Do NOT commit it."
