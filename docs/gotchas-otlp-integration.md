# Gotchas: OTLP-Native Pipeline Integration (verified 2026-06-15)

ABOUTME: Exact behavior of the all-OTLP collector→Prometheus/Loki/Jaeger hops, for query design.
ABOUTME: Verified against official docs 2026-06-15. These shape the dashboard PromQL/LogQL — read before Phase 2/4.

Collector Contrib v0.154.0 → Prometheus v3.12 (native OTLP) / Loki v3.7 (native OTLP) /
Jaeger v2.19, fronted by Grafana 12.4. Everything below changes how the dashboards query data.

## 1. Collector otlphttp → Prometheus OTLP receiver

**Endpoint** — otlphttp appends `/v1/metrics`, so set the base to `/api/v1/otlp`:
```yaml
exporters:
  otlphttp/prometheus:
    endpoint: http://prometheus:9090/api/v1/otlp   # full path becomes /api/v1/otlp/v1/metrics
    tls:
      insecure: true
```
The OTLP receiver is **off by default** — start Prometheus with `--web.enable-otlp-receiver`
or the endpoint silently returns nothing.

**Metric name translation** (default strategy `UnderscoreEscapingWithSuffixes`): dots→underscores,
unit appended as a name token, `_total` on monotonic counters. `USD` is not a recognized
Prometheus unit, so it survives into the name:

| Instrument | Final Prometheus name |
|---|---|
| Gauge / non-monotonic | `claude_code_cost_usage_USD` |
| Monotonic counter | `claude_code_cost_usage_USD_total` |

To drop the `_USD`, emit the instrument with no unit. Strategy alternatives (set under `otlp:`):
`UnderscoreEscapingWithoutSuffixes` (no unit/suffix), `NoUTF8EscapingWithSuffixes` (keeps dots,
query with `{"claude_code.cost.usage"}`), `NoTranslation` (experimental, risks silent collisions —
avoid).

**Resource attributes → labels**: by default resource attrs are NOT series labels — they land on
a synthetic `target_info` metric. **To make an attribute a queryable label, list it in
`promote_resource_attributes`.** Label names are also dot-escaped, so **`team.id` → `team_id`**.

```yaml
# prometheus.yml
otlp:
  translation_strategy: UnderscoreEscapingWithSuffixes
  promote_resource_attributes:
    - role
    - team.id            # queryable as label team_id
    - cost_center
  keep_identifying_resource_attributes: true
```
Start: `prometheus --config.file=... --web.enable-otlp-receiver`.

## 2. Collector otlphttp → Loki native OTLP

**Endpoint** — exporter appends `/v1/logs`:
```yaml
exporters:
  otlphttp/loki:
    endpoint: http://loki:3100/otlp        # real path /otlp/v1/logs
```
With `auth_enabled: false`, no `X-Scope-OrgID` header needed (tenant `fake`).

**Attribute mapping — the load-bearing constraint**:
- A fixed set of ~17 **resource** attributes become index/stream labels; **all log-record and
  scope attributes become structured metadata**. Dots→underscores (`service.name` → `service_name`).
- **`index_label` is allowed ONLY for resource attributes.** Log-record attributes can only be
  `structured_metadata` or `drop` — Loki can never promote them to a stream label.
- Claude Code emits `decision` and `mcp_server_name` as **log-record attributes**, so:
  - **To query them: do nothing** — they're in structured metadata by default:
    `{service_name="claude-code"} | decision="reject" | mcp_server_name="prod-api"` (no parser).
  - **To make them real stream labels: impossible in Loki config.** Rewrite them to *resource*
    attributes upstream in the collector (transform/resource processor), then index that.

```yaml
# loki config
limits_config:
  allow_structured_metadata: true          # required for OTLP; default true in 3.x
  otlp_config:
    resource_attributes:
      ignore_defaults: false
      attributes_config:
        - action: index_label              # resource attrs only
          attributes: [service.name, service.namespace, deployment.environment.name]
    log_attributes:
      - action: structured_metadata
        attributes: [decision, mcp_server_name]
```

**Hard startup gate** (from versions.md): structured metadata requires `tsdb` index + `v13`
schema or Loki refuses to start. Max 15 labels/series.

**event.name** (`claude_code.tool_decision`): preserved as structured metadata, normalized to
**`event_name`**: `{service_name="claude-code"} | event_name="claude_code.tool_decision"`.
**FLAG — verify live.** No official page names `event.name` mapping; depending on SDK/collector
version it may land on the top-level `EventName` LogRecord field instead. Before the demo, ingest
one event and run `{...} | event_name=~".+"` (and check Grafana detected-fields) to confirm the key.

## 3. Jaeger v2.19 OTLP traces

```yaml
exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true        # demo only; gRPC otlp exporter wants TLS by default
```
- OTLP on by default: gRPC 4317, HTTP 4318; UI/query 16686.
- **Bind-host trap — NOT observed on v2.19 (verified 2026-06-16).** The default
  `jaegertracing/jaeger:2.19.0` image binds its OTLP receivers so published ports work from the
  host and the compose network with no override. Phase 1 tests confirm UI + OTLP gRPC/HTTP reachable
  out of the box. If a future version regresses, override to `0.0.0.0`
  (`--set=receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317` or `JAEGER_LISTEN_HOST=0.0.0.0`).
- **Service name** comes from the **resource** `service.name`. If only a span attribute, the UI
  shows `OTLPResourceNoServiceName`.
- All-in-one default storage is in-memory, ~100k-trace ring buffer, **lost on restart**. Fine for
  a demo; just don't restart mid-rehearsal and expect history.
- Don't double-bind 4317/4318 between the collector's own receiver and Jaeger on the same host port.

## 4. Grafana 12.4 provisioning + trace-to-logs

```yaml
# grafana/provisioning/datasources/datasources.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    url: http://prometheus:9090
    isDefault: true
    jsonData: { httpMethod: POST }
  - name: Loki
    type: loki
    uid: loki
    url: http://loki:3100
  - name: Jaeger
    type: jaeger
    uid: jaeger
    url: http://jaeger:16686
    jsonData:
      tracesToLogsV2:
        datasourceUid: 'loki'              # MUST equal the Loki uid
        spanStartTimeShift: '-1h'
        spanEndTimeShift: '1h'
        customQuery: true
        query: '{service_name="$${__span.tags["service.name"]}"} | trace_id="$${__trace.traceId}"'
```
- `tracesToLogsV2` IS supported on the Jaeger datasource (not Tempo-only). V1 `tracesToLogs` is
  deprecated.
- Correct trace-id variable is **`${__trace.traceId}`**, NOT `${__span.traceId}`. In provisioning
  YAML **double the `$`** (`$${__trace.traceId}`) or the loader treats it as an env var.
- Loki must carry `trace_id` as **structured metadata** (high cardinality — never a label). The
  log pipeline must attach `trace_id` for the correlation filter to match.
- Reference every datasource by **uid** (numeric ids are disabled in Grafana 13, and we keep the
  habit in 12.4 so a later bump is painless).

## Five flags that silently break ingestion or queries

1. Prometheus needs `--web.enable-otlp-receiver` (else no metrics).
2. Jaeger needs `0.0.0.0` bind (else no traces from other containers).
3. `team.id` is queried as `team_id` in PromQL; `service.name` as `service_name` in LogQL.
4. `decision` / `mcp_server_name` are LogQL structured-metadata filters (`|`), not labels (`{}`).
5. `_USD` rides on the cost metric name unless the unit is dropped.
6. `event.name` → `event_name` is inferred — verify empirically before going live.
