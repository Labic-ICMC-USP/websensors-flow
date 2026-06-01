# Configuration

A WebSensors Flow project is configured with a main YAML file and optional YAML files for each step.

## Main flow YAML

```yaml
project:
  name: dmoz_health_text_classification
  version: "0.3.0"

environment:
  name: local

runtime:
  report_dir: ./outputs/dmoz_health/reports
  fail_fast: true
  include_traceback: true
  raise_on_failure: false
  console:
    enabled: true
    progress: true
    show_metrics: true

pipeline:
  params:
    random_state: 42
    test_size: 0.25
    cv_folds: 3
```

The validated configuration is available inside every step as `context.config`.

## Step YAML files

Each step can reference an external YAML file:

```yaml
steps:
  - name: ingest_data
    class_path: projects.example_dmoz.ingest_data.IngestDataStep
    config_path: steps/01_ingest_data.yaml
```

The content of that file is available inside the current step as `context.step_config`.

## Observability

Graylog and MLflow are optional:

```yaml
observability:
  mlflow:
    enabled: false
  graylog:
    enabled: false
```

When a backend is enabled, its preflight check runs before the first step. The terminal prints each preflight operation with `RUNNING`, `OK`, or `FAILED`. The check validates the backend and sends a real preflight probe. For Graylog, the probe is a GELF message. For MLflow, the probe is a short run with tags, parameters, and metrics. If the backend is not ready or the probe cannot be written, the pipeline stops before executing user code.

Timeouts are configured in the same YAML block:

```yaml
observability:
  mlflow:
    http_request_timeout: 3
    connect_timeout_seconds: 3
  graylog:
    connect_timeout_seconds: 3
```

## Authentication

Authentication can use direct values or environment variables:

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: http://127.0.0.1:5000
    experiment_name: websensors-flow
    auth:
      enabled: true
      username_env: MLFLOW_TRACKING_USERNAME
      password_env: MLFLOW_TRACKING_PASSWORD
```

For token-based deployments:

```yaml
auth:
  enabled: true
  token_env: MLFLOW_TRACKING_TOKEN
```
