# All-or-nothing execution

WebSensors Flow uses fail-fast execution.

If one step fails:

1. the exception is captured by the framework;
2. the failed step is recorded in the local report;
3. active observers receive `step_failed` and `pipeline_failed` events;
4. later steps are not executed;
5. the pipeline returns a `PipelineRunResult` with `failure` filled, unless `runtime.raise_on_failure` is true.

This policy avoids passing partial or invalid outputs to later steps.
