"""FastAPI application factory for running a configured flow."""

import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, create_model

from websensors_flow.config import FlowSettings
from websensors_flow.runner import run_configured_flow


_TYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict[str, Any],
    "array": list[Any],
}


class GenericRunRequest(BaseModel):
    """Request body used when the YAML file does not define API fields."""

    input: Any = Field(default=None, description="Object passed to the first step.")
    params: dict[str, Any] = Field(default_factory=dict, description="Optional pipeline parameter overrides.")


class JobStore:
    """In-memory store for asynchronous API executions."""

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}

    def create(self, run_id: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.jobs[run_id] = {
            "run_id": run_id,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "payload": payload,
            "report": None,
            "failure": None,
            "output": None,
        }

    def update(self, run_id: str, **values: Any) -> None:
        if run_id in self.jobs:
            self.jobs[run_id].update(values)
            self.jobs[run_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self.jobs.get(run_id)


def _request_model_from_settings(settings: FlowSettings) -> type[BaseModel]:
    """Build the request model declared in the YAML API section."""

    if not settings.api.input_fields:
        return GenericRunRequest

    fields: dict[str, tuple[Any, Any]] = {}
    for name, field_config in settings.api.input_fields.items():
        python_type = _TYPE_MAP[field_config.type]
        default = ... if field_config.required and field_config.default is None else field_config.default
        fields[name] = (
            python_type,
            Field(default=default, description=field_config.description),
        )
    fields["params"] = (
        dict[str, Any],
        Field(default_factory=dict, description="Optional pipeline parameter overrides."),
    )
    model = create_model("FlowRunRequest", __module__=__name__, **fields)
    model.model_rebuild(force=True)
    return model


def _safe_output(output: Any) -> Any:
    """Convert the final output to a JSON-friendly value."""

    if output is None or isinstance(output, (str, int, float, bool)):
        return output
    if isinstance(output, list):
        return [_safe_output(value) for value in output]
    if isinstance(output, dict):
        return {str(key): _safe_output(value) for key, value in output.items()}
    return repr(output)


def create_app(settings: FlowSettings):
    """Create the FastAPI application for a flow."""

    try:
        from fastapi import Body, FastAPI, HTTPException
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("FastAPI is required for API mode. Install websensors-flow with the 'api' extra.") from exc

    app = FastAPI(
        title=settings.api.title,
        description=settings.api.description or settings.project.description,
        version=settings.api.version or settings.project.version,
    )
    executor = ThreadPoolExecutor(max_workers=settings.api.workers)
    store = JobStore()
    RequestModel = _request_model_from_settings(settings)

    def execute_job(run_id: str, input_payload: Any, params: dict[str, Any]) -> None:
        store.update(run_id, status="running")
        try:
            result = run_configured_flow(settings, input=input_payload, params=params, run_id=run_id)
            update: dict[str, Any] = {
                "status": result.report.status,
                "report": result.report.model_dump(mode="json"),
            }
            if result.failure is not None:
                update["failure"] = result.failure.model_dump(mode="json")
            if settings.api.return_output:
                update["output"] = _safe_output(result.output)
            store.update(run_id, **update)
        except Exception as exc:
            store.update(
                run_id,
                status="failed",
                failure={"error_type": type(exc).__name__, "error_message": str(exc)},
            )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "project": settings.project.name,
            "environment": settings.environment.name,
        }

    @app.post(settings.api.endpoint, status_code=202)
    def start_run(request: RequestModel = Body(...)) -> dict[str, Any]:
        payload = request.model_dump()
        params = payload.pop("params", {}) or {}
        input_payload = payload.get("input") if set(payload.keys()) == {"input"} else payload
        run_id = uuid.uuid4().hex
        store.create(run_id, payload={"input": input_payload, "params": params})
        future: Future[None] = executor.submit(execute_job, run_id, input_payload, params)
        store.update(run_id, future_state=str(future))
        return {"run_id": run_id, "status": "queued", "status_url": f"/status/{run_id}"}

    @app.get("/status/{run_id}")
    def get_status(run_id: str) -> dict[str, Any]:
        job = store.get(run_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Run token not found.")
        return {key: value for key, value in job.items() if key != "future_state"}

    return app
