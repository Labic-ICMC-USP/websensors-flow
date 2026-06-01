"""Pipeline context passed to every user-defined step."""

from __future__ import annotations

from typing import Any

from websensors_flow.config import FlowSettings
from websensors_flow.logger import PipelineLogger


class PipelineContext:
    """Execution context available to user steps.

    The context exposes the full flow configuration, the current step
    configuration, a backend-agnostic logger, and a small in-memory state
    dictionary. Heavy data should move through step input and output objects.
    """

    def __init__(
        self,
        *,
        settings: FlowSettings,
        run_id: str,
        pipeline_name: str,
        logger: PipelineLogger | None = None,
    ):
        self.settings = settings
        self.config = settings
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.environment = settings.environment.name
        self.current_step_name: str | None = None
        self.current_step_index: int | None = None
        self.step_config: dict[str, Any] = {}
        self.step_configs: dict[str, dict[str, Any]] = settings.step_configs
        self.state: dict[str, Any] = {}
        self.logger = logger or PipelineLogger(
            pipeline_name=pipeline_name,
            run_id=run_id,
            environment=settings.environment.name,
        )
        self.log = self.logger

    def set_current_step(self, step_name: str, step_index: int) -> None:
        """Update current-step metadata before a step starts."""

        self.current_step_name = step_name
        self.current_step_index = step_index
        self.step_config = self.settings.get_step_config(step_name)
        self.logger.bind_step(step_name=step_name, step_index=step_index)

    def clear_current_step(self) -> None:
        """Clear current-step metadata after the pipeline finishes."""

        self.current_step_name = None
        self.current_step_index = None
        self.step_config = {}
        self.logger.bind_step(step_name=None, step_index=None)

    def get_step_config(self, step_name: str | None = None) -> dict[str, Any]:
        """Return a step configuration by name or the current step configuration."""

        if step_name is None:
            return dict(self.step_config)
        return self.settings.get_step_config(step_name)
