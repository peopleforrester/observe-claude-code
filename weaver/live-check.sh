#!/usr/bin/env bash
# ABOUTME: Runs OTel Weaver live-check against the agent telemetry and prints the validation report.
# ABOUTME: Offline + deterministic — a one-shot feeder Collector streams a captured sample to weaver.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."  # repo root

WEAVER_IMAGE="otel/weaver:v0.23.0"
COLLECTOR_IMAGE="otel/opentelemetry-collector-contrib:0.154.0"
NET="${OCC_NETWORK:-observe-claude-code_observe}"
REGISTRY="weaver/registry"
SAMPLE="${1:-weaver/sample-telemetry.jsonl}"

command -v docker >/dev/null 2>&1 || { echo "docker not available in this shell" >&2; exit 1; }
[ -f "${SAMPLE}" ] || { echo "sample not found: ${SAMPLE}" >&2; exit 1; }

mkdir -p weaver/out
rm -f weaver/out/* 2>/dev/null || true
docker rm -f occ-weaver >/dev/null 2>&1 || true

echo "==> Starting weaver live-check (listening OTLP gRPC on the ${NET} network)..."
docker run -d --name occ-weaver --network "${NET}" \
    -v "${PWD}/${REGISTRY}":/registry:ro \
    -v "${PWD}/weaver/out":/out \
    "${WEAVER_IMAGE}" registry live-check -r /registry --future \
    --input-source otlp --otlp-grpc-address 0.0.0.0 --otlp-grpc-port 4317 \
    --inactivity-timeout 12 --format json -o /out >/dev/null
sleep 2

echo "==> Feeding the captured sample to weaver via a one-shot Collector..."
docker run --rm --network "${NET}" \
    -v "${PWD}/weaver/feeder.yaml":/etc/otelcol/config.yaml:ro \
    -v "${PWD}/${SAMPLE}":/capture.jsonl:ro \
    "${COLLECTOR_IMAGE}" --config /etc/otelcol/config.yaml >/dev/null 2>&1 &
feeder_pid=$!

# weaver exits on its inactivity timeout once the sample has streamed.
docker wait occ-weaver >/dev/null
kill "${feeder_pid}" 2>/dev/null || true

echo "==> Weaver live-check report:"
if [ -f weaver/out/live_check.json ]; then
    cat weaver/out/live_check.json
else
    ls weaver/out/ 2>/dev/null && cat weaver/out/* 2>/dev/null || docker logs occ-weaver 2>&1 | tail -30
fi
docker rm -f occ-weaver >/dev/null 2>&1 || true
