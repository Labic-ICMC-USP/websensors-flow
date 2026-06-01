import pytest
from pydantic import ValidationError

from websensors_flow import MetricRecord, StepResult


def test_step_result_requires_non_empty_text():
    with pytest.raises(ValidationError):
        StepResult(text="   ", metrics={})


def test_step_result_accepts_numeric_metrics():
    result = StepResult(text="ok", metrics={"a": 1, "b": 2.5, "c": True})
    assert result.metrics["a"] == 1


def test_step_result_rejects_non_numeric_metrics():
    with pytest.raises(ValidationError):
        StepResult(text="ok", metrics={"bad": "not numeric"})


def test_step_result_accepts_metric_records():
    result = StepResult(
        text="Compared models.",
        metrics={"models_tested": 2},
        metric_records=[
            {
                "name": "model_candidate",
                "params": {"model_name": "knn"},
                "metrics": {"cv_f1_macro": 0.97, "rank": 1},
            }
        ],
    )
    assert result.metric_records[0].params["model_name"] == "knn"


def test_metric_record_rejects_non_numeric_metrics():
    with pytest.raises(ValidationError):
        MetricRecord(
            name="model_candidate",
            params={"model_name": "knn"},
            metrics={"cv_f1_macro": "bad"},
        )
