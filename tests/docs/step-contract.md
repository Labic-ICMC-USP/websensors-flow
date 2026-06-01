# Step contract

A step extends `PipelineStep` and implements `execute`.

```python
from websensors_flow import PipelineStep, StepResult

class MyStep(PipelineStep):
    name = "my_step"

    def execute(self, input, context):
        context.log.info("Starting my step.", metrics={"items": 10})
        return StepResult(
            output=input,
            has_output=True,
            text="My step completed.",
            metrics={"items": 10},
        )
```

## Context

The context exposes:

- `context.config`: full flow configuration;
- `context.step_config`: YAML configuration of the current step;
- `context.step_configs`: YAML configuration of all steps by name;
- `context.log`: logger used by the step;
- `context.run_id`: current run id;
- `context.pipeline_name`: current pipeline name.

## Observability

A step can return or log:

- `metrics`: numeric values;
- `params`: configuration values used by the step;
- `metadata`: text or structured details;
- `artifacts`: local file paths;
- `metric_records`: repeated records for datasets, models, classes, candidates, or tool calls.

The step does not need to know whether the data goes to the terminal, Graylog, MLflow, or a report.
