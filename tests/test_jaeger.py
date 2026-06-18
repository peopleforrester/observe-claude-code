# ABOUTME: Verifies Jaeger v2 serves its UI. OTLP ingress is owned by the Collector (see test_collector).
# ABOUTME: Trace delivery into Jaeger is covered end-to-end by the Collector round-trip test.
from conftest import JAEGER_UI_URL, wait_until


def test_jaeger_ui_is_up(http):
    def ok():
        return http.get(f"{JAEGER_UI_URL}/").status_code == 200

    assert wait_until(ok, what="Jaeger UI")
