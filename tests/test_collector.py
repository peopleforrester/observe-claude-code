# ABOUTME: Verifies the OTel Collector is live, healthy, and accepting OTLP on the ingress ports.
# ABOUTME: The round-trip (OTLP in -> backends) is covered by test_roundtrip.
import socket

import pytest

from conftest import (
    COLLECTOR_HEALTH_PORT,
    COLLECTOR_HEALTH_URL,
    COLLECTOR_OTLP_HTTP,
    OTLP_GRPC_PORT,
    OTLP_HTTP_PORT,
    wait_until,
)

pytestmark = pytest.mark.integration


def _port_open(host, port):
    with socket.socket() as sock:
        sock.settimeout(2)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def test_collector_health_extension_ok(http):
    def healthy():
        return http.get(COLLECTOR_HEALTH_URL).status_code == 200

    assert wait_until(healthy, what=f"Collector health_check :{COLLECTOR_HEALTH_PORT}")


def test_collector_otlp_grpc_port_open():
    assert wait_until(lambda: _port_open("localhost", OTLP_GRPC_PORT),
                      what=f"Collector OTLP gRPC :{OTLP_GRPC_PORT}")


def test_collector_otlp_http_accepts_traces(http):
    wait_until(lambda: _port_open("localhost", OTLP_HTTP_PORT),
               what=f"Collector OTLP HTTP :{OTLP_HTTP_PORT}")
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/traces", json={"resourceSpans": []})
    assert r.status_code == 200, f"Collector did not accept OTLP traces: {r.status_code} {r.text}"
