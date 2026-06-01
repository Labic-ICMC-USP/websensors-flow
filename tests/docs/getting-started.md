# Getting started

Install the project with all optional dependencies:

```bash
pip install -e '.[all]'
```

Run the tutorial flow:

```bash
python examples/dmoz_health_run.py
```

or run it directly from the YAML file:

```bash
websensors-flow-run --config flows/example_dmoz/flow.yaml
```

Reports are written to the configured report directory:

```text
outputs/dmoz_health/reports/<run_id>/
```

Graylog and MLflow are controlled only by the main YAML block. The DMOZ tutorial enables MLflow and keeps Graylog disabled:

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: http://127.0.0.1:5000
    experiment_name: websensors-flow-dmoz-health
  graylog:
    enabled: false
    host: 127.0.0.1
    port: 12201
    protocol: tcp
```

Before the first step starts, the terminal shows the resolved configuration and sends one real probe event to each enabled observer.

The FastAPI runner is available for deployments that need asynchronous API execution, but it is not part of the DMOZ tutorial.
