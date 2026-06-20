#!/usr/bin/env bash
# ABOUTME: Capture one real scripted session's OTLP into a snapshot for offline stage replay.
# ABOUTME: Snapshots are gitignored — real captures carry account/user identifiers; never commit them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../.."  # repo root

COMPOSE="docker compose --project-directory . -f compose/docker-compose.yml"
RAW="demo/replay/raw/otlp-capture.jsonl"
STAMP="$(date +%Y%m%d-%H%M%S)"
SNAP="demo/replay/raw/session-${STAMP}.jsonl"

command -v docker >/dev/null 2>&1 || { echo "docker not available in this shell" >&2; exit 1; }

echo "==> Clearing the capture file and restarting the Collector for a clean capture..."
rm -f "${RAW}"
${COMPOSE} restart collector >/dev/null
sleep 5

echo "==> Running the scripted session (deploy will be denied)..."
bash demo/run-session.sh >/dev/null 2>&1 || true

echo "==> Waiting for the export intervals to flush..."
sleep 12

cp "${RAW}" "${SNAP}"
echo "==> Captured $(wc -l < "${SNAP}") OTLP records -> ${SNAP}"
echo
echo "Replay it offline (loops for a live-looking stage demo):"
echo "  python3 demo/replay/replay.py --capture ${SNAP} --loop"
echo
echo "NOTE: this snapshot contains account/user identifiers. It is gitignored. Do NOT commit it."
