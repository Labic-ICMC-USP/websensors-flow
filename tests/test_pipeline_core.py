import pytest

from websensors_flow import PipelineExecutionError, PipelineStep, StepResult
from websensors_flow.config import FlowSettings
from websensors_flow.observers.base import PipelineObserver
from websensors_flow.pipeline import WebSensorsPipeline


class MemoryObserver(PipelineObserver):
    name = "memory"

    def __init__(self):
        self.events = []

    def validate_ready(self):
        self.events.append("ready")

    def on_event(self, event):
        self.events.append(event.event_type)


class AddOneStep(PipelineStep):
    name = "add_one"

    def execute(self, input, context):
        context.log.info("Adding one.", metrics={"input": input})
        return StepResult(
            output=input + 1,
            has_output=True,
            text="Added one.",
            metrics={"value": input + 1},
        )


class ConfigAwareStep(PipelineStep):
    name = "configured"

    def execute(self, input, context):
        increment = int(context.step_config["increment"])
        return StepResult(
            output=input + increment,
            has_output=True,
            text="Used step configuration.",
            metrics={"increment": increment},
        )


class FailingStep(PipelineStep):
    name = "failing"

    def execute(self, input, context):
        raise RuntimeError("boom")


class ShouldNotRunStep(PipelineStep):
    name = "should_not_run"

    def execute(self, input, context):
        raise AssertionError("This step should not run")


def settings():
    return FlowSettings.model_validate(
        {
            "project": {"name": "test"},
            "environment": {"name": "test"},
            "steps": [
                {"name": "configured", "config": {"increment": 5}},
            ],
        }
    )


def test_pipeline_success_passes_output_between_steps():
    memory = MemoryObserver()
    pipeline = WebSensorsPipeline(settings=settings(), observers=[memory])
    pipeline.add(AddOneStep()).add(AddOneStep())
    result = pipeline.run(input=1)
    assert result.output == 3
    assert result.report.status == "success"
    assert "pipeline_completed" in memory.events
    assert "user_log" in memory.events


def test_pipeline_exposes_step_config_in_context():
    pipeline = WebSensorsPipeline(settings=settings(), observers=[MemoryObserver()])
    pipeline.add(ConfigAwareStep())
    result = pipeline.run(input=1)
    assert result.output == 6
    assert result.report.steps[0].metrics["increment"] == 5


def test_pipeline_stops_on_first_failure_without_raising_by_default():
    memory = MemoryObserver()
    pipeline = WebSensorsPipeline(settings=settings(), observers=[memory])
    pipeline.add(AddOneStep()).add(FailingStep()).add(ShouldNotRunStep())
    result = pipeline.run(input=1)
    assert result.report.status == "failed"
    assert result.failure is not None
    assert pipeline.report.status == "failed"
    assert [step.step_name for step in pipeline.report.steps] == ["add_one", "failing"]
    assert "step_failed" in memory.events
    assert "pipeline_failed" in memory.events


def test_pipeline_can_run_without_graylog_and_mlflow_observers():
    pipeline = WebSensorsPipeline(settings=settings(), observers=[MemoryObserver()])
    pipeline.add(AddOneStep())
    result = pipeline.run(input=1)
    assert result.report.status == "success"
    assert result.output == 2


def test_pipeline_can_raise_on_failure_when_configured():
    s = settings()
    s.runtime.raise_on_failure = True
    pipeline = WebSensorsPipeline(settings=s, observers=[MemoryObserver()])
    pipeline.add(AddOneStep()).add(FailingStep())
    with pytest.raises(PipelineExecutionError):
        pipeline.run(input=1)
