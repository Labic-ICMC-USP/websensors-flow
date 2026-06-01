# MLflow observer

The MLflow observer records the pipeline as a run and records detailed evidence from each step.

It logs:

- run tags and flow configuration;
- pipeline parameters;
- step metrics and step parameters;
- user logs emitted through `context.log`;
- artifacts declared by each step;
- metric records as nested runs;
- dataset inputs when a step emits a `MetricRecord` named `dataset`;
- sklearn models when a step declares a `model_bundle` artifact;
- system metrics when the MLflow installation supports them.

## Configuration

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: http://127.0.0.1:5000
    experiment_name: websensors-flow-dmoz-health
    run_name: dmoz-health-local
    http_request_timeout: 3
    connect_timeout_seconds: 3
```

Credentials can be provided directly or through environment variables.
