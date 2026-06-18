# ABOUTME: Verifies the Grafana dashboard is v1-schema, covers the three panes, and provisions.
# ABOUTME: v1 schema is required — Grafana 13 cannot file-provision v2-schema dashboards.
import json

from conftest import GRAFANA_URL, REPO_ROOT, wait_until

AUTH = ("admin", "admin")
DASHBOARD_PATH = REPO_ROOT / "grafana" / "dashboards" / "observe-claude-code.json"
UID = "observe-claude-code"
VALID_DS_UIDS = {"prometheus", "loki", "jaeger"}


def _dashboard():
    return json.loads(DASHBOARD_PATH.read_text())


def test_dashboard_is_v1_schema():
    d = _dashboard()
    assert isinstance(d.get("panels"), list) and d["panels"], "no panels"
    assert isinstance(d.get("schemaVersion"), int), "missing schemaVersion (v1 marker)"
    # v2-schema markers must be absent — they break file provisioning in Grafana 13.
    assert "elements" not in d, "v2 'elements' key present"
    assert d.get("apiVersion") != "dashboard.grafana.app/v2"


def test_dashboard_covers_three_panes():
    titles = " ".join(p.get("title", "") for p in _dashboard()["panels"]).lower()
    for pane in ("productivity", "cost", "security"):
        assert pane in titles, f"dashboard missing the {pane} section"


def test_dashboard_panels_reference_known_datasources():
    for p in _dashboard()["panels"]:
        if p.get("type") == "row":
            continue
        ds = p.get("datasource") or {}
        assert ds.get("uid") in VALID_DS_UIDS, f"panel {p.get('title')!r} bad datasource {ds!r}"
        for t in p.get("targets", []):
            tds = t.get("datasource") or {}
            assert tds.get("uid") in VALID_DS_UIDS, f"target in {p.get('title')!r} bad datasource"


def test_loki_panels_use_real_event_name_values():
    # The real Loki event_name values have no "claude_code." prefix (verified against live data).
    exprs = [
        t.get("expr", "")
        for p in _dashboard()["panels"]
        for t in p.get("targets", [])
    ]
    loki_exprs = [e for e in exprs if "event_name" in e]
    assert loki_exprs, "no Loki event_name panels found"
    for expr in loki_exprs:
        assert "claude_code." not in expr, f"stale prefixed event_name in: {expr}"
    joined = " ".join(loki_exprs)
    assert "tool_decision" in joined and "mcp_server_connection" in joined


def test_dashboard_is_provisioned_in_grafana(http):
    def loaded():
        r = http.get(f"{GRAFANA_URL}/api/dashboards/uid/{UID}", auth=AUTH)
        return r.status_code == 200

    assert wait_until(loaded, what="dashboard provisioned in Grafana")
