# ABOUTME: Verifies Loki is ready, exposes the native OTLP logs endpoint, and has structured metadata on.
# ABOUTME: Guards the events/logs backend of the Phase 1 stack.
from conftest import LOKI_URL, wait_until


def test_loki_is_ready(http):
    def ready():
        return http.get(f"{LOKI_URL}/ready").status_code == 200

    assert wait_until(ready, what="Loki /ready")


def test_loki_otlp_endpoint_is_mounted(http):
    wait_until(lambda: http.get(f"{LOKI_URL}/ready").status_code == 200, what="Loki ready")
    # POST-only endpoint; a GET must not 404 if the OTLP logs path is mounted.
    r = http.get(f"{LOKI_URL}/otlp/v1/logs")
    assert r.status_code != 404, f"Loki OTLP logs endpoint not mounted (got {r.status_code})"


def test_loki_structured_metadata_and_schema(http):
    wait_until(lambda: http.get(f"{LOKI_URL}/ready").status_code == 200, what="Loki ready")
    cfg = http.get(f"{LOKI_URL}/config")
    cfg.raise_for_status()
    text = cfg.text
    assert "allow_structured_metadata: true" in text, "structured metadata not enabled"
    assert "schema: v13" in text, "schema is not v13 (required for structured metadata)"
    assert "store: tsdb" in text, "index store is not tsdb"
