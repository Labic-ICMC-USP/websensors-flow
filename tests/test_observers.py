import logging
import sys
import types

from websensors_flow.config import FlowSettings
from websensors_flow.events import PipelineEvent
from websensors_flow.observers.console import ConsoleObserver
from websensors_flow.observers.graylog import GraylogObserver
from websensors_flow.observers.mlflow import MLflowObserver


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeGrayHandler(logging.Handler):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.records = []

    def emit(self, record):
        self.records.append(record)


class FakeRunContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeMLflow:
    def __init__(self):
        self.calls = []

    def set_tracking_uri(self, uri):
        self.calls.append(("set_tracking_uri", uri))

    def set_experiment(self, name):
        self.calls.append(("set_experiment", name))

    def start_run(self, run_name=None, nested=False):
        self.calls.append(("start_run", run_name, nested))
        return FakeRunContext()

    def set_tags(self, tags):
        self.calls.append(("set_tags", tags))

    def set_tag(self, key, value):
        self.calls.append(("set_tag", key, value))

    def log_params(self, params):
        self.calls.append(("log_params", params))

    def log_param(self, key, value):
        self.calls.append(("log_param", key, value))

    def log_metric(self, key, value):
        self.calls.append(("log_metric", key, value))

    def log_artifact(self, local_path, artifact_path=None):
        self.calls.append(("log_artifact", local_path, artifact_path))

    def end_run(self, status=None):
        self.calls.append(("end_run", status))


class FakeMlflowClient:
    def __init__(self, tracking_uri=None):
        self.tracking_uri = tracking_uri

    def search_experiments(self, max_results=1):
        return []


def settings():
    return FlowSettings.model_validate(
        {
            "project": {"name": "test", "version": "1"},
            "environment": {"name": "test"},
            "observability": {
                "mlflow": {"enabled": True, "tracking_uri": "file:./mlruns", "experiment_name": "x"},
                "graylog": {"enabled": True, "host": "127.0.0.1", "port": 12201, "protocol": "tcp"},
            },
        }
    ).resolve_external_values()


def test_graylog_observer_uses_graypy_and_tcp_preflight(monkeypatch):
    fake = types.SimpleNamespace(GELFTCPHandler=FakeGrayHandler)
    monkeypatch.setitem(sys.modules, "graypy", fake)
    monkeypatch.setattr("socket.create_connection", lambda *args, **kwargs: FakeConnection())
    observer = GraylogObserver(settings().observability.graylog)
    observer.validate_ready()
    observer.on_event(
        PipelineEvent(
            event_type="pipeline_started",
            pipeline_name="p",
            run_id="r",
            environment="test",
        )
    )
    observer.close("success")


def test_mlflow_observer_records_events(monkeypatch):
    fake = FakeMLflow()
    tracking_module = types.SimpleNamespace(MlflowClient=FakeMlflowClient)
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.tracking", tracking_module)
    s = settings()
    observer = MLflowObserver(s.observability.mlflow, settings=s)
    observer.validate_ready()
    observer.on_event(PipelineEvent(event_type="pipeline_started", pipeline_name="p", run_id="r", environment="test"))
    observer.on_event(
        PipelineEvent(
            event_type="step_completed",
            pipeline_name="p",
            run_id="r",
            environment="test",
            step_name="s1",
            metrics={"m": 1},
            text="done",
            status="success",
        )
    )
    observer.close("success")
    assert any(call[0] == "start_run" for call in fake.calls)
    assert any(call[0] == "log_metric" for call in fake.calls)
    assert any(call[0] == "end_run" for call in fake.calls)


def test_console_observer_prints_friendly_text(capsys):
    observer = ConsoleObserver(progress=False, show_metrics=True, report_dir="./reports")
    observer.validate_ready()
    observer.on_event(PipelineEvent(event_type="pipeline_started", pipeline_name="p", run_id="r", environment="test", metadata={"steps_total": 1}))
    observer.on_event(
        PipelineEvent(
            event_type="step_completed",
            pipeline_name="p",
            run_id="r",
            environment="test",
            step_name="s1",
            step_index=1,
            duration_seconds=0.1,
            metrics={"accuracy": 0.9},
        )
    )
    output = capsys.readouterr().out
    assert "RUNNING" in output
    assert "pipeline" in output
    assert "Step completed" in output


def test_console_observer_prints_user_log_as_readable_text(capsys):
    observer = ConsoleObserver(progress=False, show_metrics=True)
    observer.on_event(
        PipelineEvent(
            event_type="user_log",
            pipeline_name="p",
            run_id="r",
            environment="test",
            step_name="s1",
            text="hello",
            metrics={"rows": 3},
        )
    )
    output = capsys.readouterr().out
    assert "INFO" in output
    assert "log" in output
    assert "s1" in output
    assert "hello" in output
    assert "metrics" in output
    assert "rows=3" in output
    assert '"event"' not in output




def test_console_observer_prints_preflight_progress(capsys):
    observer = ConsoleObserver(progress=False)
    observer.on_event(
        PipelineEvent(
            event_type="preflight_observer_status",
            pipeline_name="p",
            run_id="r",
            environment="test",
            status="running",
            metadata={
                "observer": "mlflow",
                "phase": "validate_ready",
                "action": "Checking observer configuration.",
                "target": "http://127.0.0.1:5000",
            },
        )
    )
    observer.on_event(
        PipelineEvent(
            event_type="preflight_observer_status",
            pipeline_name="p",
            run_id="r",
            environment="test",
            status="failed",
            metadata={
                "observer": "mlflow",
                "phase": "validate_ready",
                "action": "Observer configuration failed.",
                "target": "http://127.0.0.1:5000",
                "duration_seconds": 1.2,
                "error": "connection refused",
            },
        )
    )
    output = capsys.readouterr().out
    assert "RUNNING" in output
    assert "FAILED" in output
    assert "mlflow" in output
    assert "connection refused" in output


def test_mlflow_observer_logs_metric_records_as_nested_runs(monkeypatch):
    fake = FakeMLflow()
    tracking_module = types.SimpleNamespace(MlflowClient=FakeMlflowClient)
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.tracking", tracking_module)

    s = settings()
    observer = MLflowObserver(s.observability.mlflow, settings=s)
    observer.validate_ready()
    observer.on_event(PipelineEvent(event_type="pipeline_started", pipeline_name="p", run_id="r", environment="test"))
    observer.on_event(
        PipelineEvent(
            event_type="step_completed",
            pipeline_name="p",
            run_id="r",
            environment="test",
            step_name="compare_models",
            metrics={"models_tested": 2},
            text="done",
            status="success",
            metric_records=[
                {
                    "name": "model_candidate",
                    "params": {"model_name": "knn", "estimator_class": "KNeighborsClassifier"},
                    "metrics": {"cv_f1_macro": 0.97, "rank": 1},
                },
                {
                    "name": "model_candidate",
                    "params": {"model_name": "random_forest", "estimator_class": "RandomForestClassifier"},
                    "metrics": {"cv_f1_macro": 0.95, "rank": 2},
                },
            ],
        )
    )
    observer.close("success")

    nested_runs = [call for call in fake.calls if call[0] == "start_run" and len(call) > 2 and call[2] is True]
    assert len(nested_runs) == 2
    assert any(call == ("log_param", "model_name", "knn") for call in fake.calls)
    assert any(call == ("log_metric", "cv_f1_macro", 0.97) for call in fake.calls)


def test_graylog_observer_sends_preflight_probe(monkeypatch):
    fake = types.SimpleNamespace(GELFTCPHandler=FakeGrayHandler)
    monkeypatch.setitem(sys.modules, "graypy", fake)
    monkeypatch.setattr("socket.create_connection", lambda *args, **kwargs: FakeConnection())

    observer = GraylogObserver(settings().observability.graylog)
    observer.validate_ready()
    observer.preflight_probe(
        PipelineEvent(
            event_type="preflight_probe",
            pipeline_name="p",
            run_id="r",
            environment="test",
            metadata={"steps_total": 2},
            metrics={"preflight_probe": 1},
        )
    )

    assert observer._handler is not None
    messages = [record.getMessage() for record in observer._handler.records]
    assert "websensors_flow_preflight_probe" in messages
    observer.close("success")


def test_mlflow_observer_sends_preflight_probe(monkeypatch):
    fake = FakeMLflow()
    tracking_module = types.SimpleNamespace(MlflowClient=FakeMlflowClient)
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.tracking", tracking_module)

    s = settings()
    observer = MLflowObserver(s.observability.mlflow, settings=s)
    observer.validate_ready()
    observer.preflight_probe(
        PipelineEvent(
            event_type="preflight_probe",
            pipeline_name="p",
            run_id="r",
            environment="test",
            metadata={"steps_total": 2},
            metrics={"preflight_probe": 1},
        )
    )

    assert any(call[0] == "start_run" and "websensors-flow-preflight" in call[1] for call in fake.calls)
    assert ("log_metric", "preflight.probe", 1) in fake.calls
    assert any(call == ("end_run", "FINISHED") for call in fake.calls)
