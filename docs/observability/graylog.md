# Graylog observer

The Graylog observer sends structured events in GELF format.

It receives:

- pipeline start and completion events;
- step start, completion, and failure events;
- logs emitted by user steps through `context.log`;
- metrics, parameters, artifacts, and metadata;
- one event for each `MetricRecord` emitted by a step.

## Configuration

```yaml
observability:
  graylog:
    enabled: true
    host: 127.0.0.1
    port: 12201
    protocol: tcp
    facility: websensors-flow
    level: INFO
    connect_timeout_seconds: 3
```
