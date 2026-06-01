"""Terminal observer for readable pipeline execution output."""

from __future__ import annotations

from typing import Any

from websensors_flow.events import PipelineEvent
from websensors_flow.observers.base import PipelineObserver

try:  # pragma: no cover
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover
    box = None  # type: ignore
    Console = None  # type: ignore
    Panel = None  # type: ignore
    Table = None  # type: ignore


class ConsoleObserver(PipelineObserver):
    """Print pipeline events in a terminal-friendly layout."""

    name = "console"

    def __init__(self, *, enabled: bool = True, progress: bool = True, show_metrics: bool = True, report_dir: str | None = None):
        self.enabled = enabled
        self.progress = progress
        self.show_metrics = show_metrics
        self.report_dir = report_dir
        self._steps_total = 0
        self._steps_done = 0
        self._console = Console(highlight=False, soft_wrap=True, width=180) if Console is not None else None

    def validate_ready(self) -> None:
        """Validate the terminal observer."""

    def preflight_probe(self, event: PipelineEvent) -> None:
        """No external preflight is required for terminal output."""

    def on_event(self, event: PipelineEvent) -> None:
        if not self.enabled:
            return
        handler = getattr(self, f"_on_{event.event_type}", None)
        if handler is not None:
            handler(event)

    def close(self, status: str) -> None:
        """Close the terminal observer."""

    def _on_preflight_configuration(self, event: PipelineEvent) -> None:
        self._print_title("WebSensors Flow")
        self._write(self._configuration_table(event.metadata))
        self._print_section("Preflight")

    def _on_preflight_observer_status(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status=str(event.status or "running"),
                category="preflight",
                name=str(event.metadata.get("observer", "-")),
                message=str(event.metadata.get("action", "")),
                fields={
                    "phase": event.metadata.get("phase", "-"),
                    "target": event.metadata.get("target", "-"),
                    "duration": self._duration(event.metadata.get("duration_seconds")),
                    "error": event.metadata.get("error", ""),
                },
            )
        )

    def _on_pipeline_started(self, event: PipelineEvent) -> None:
        self._steps_total = int(event.metadata.get("steps_total", 0) or 0)
        self._steps_done = 0
        self._print_section("Pipeline")
        self._write(
            self._status_panel(
                status="RUNNING",
                category="pipeline",
                name=event.pipeline_name,
                message="Pipeline execution started.",
                fields={"run_id": event.run_id, "environment": event.environment, "steps": self._steps_total},
            )
        )
        self._print_progress()

    def _on_step_started(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status="RUNNING",
                category="step",
                name=self._step_name(event),
                message="Step execution started.",
                fields=self._compact_fields(event.metadata),
            )
        )

    def _on_user_log(self, event: PipelineEvent) -> None:
        fields: dict[str, Any] = {}
        if event.metrics:
            fields["metrics"] = self._inline_mapping(event.metrics, limit=8)
        if event.params:
            fields["params"] = self._inline_mapping(event.params, limit=5)
        if event.metadata:
            fields["metadata"] = self._inline_mapping(event.metadata, limit=5)
        if event.artifacts:
            fields["artifacts"] = ", ".join(event.artifacts.keys())
        self._write(
            self._status_panel(
                status=self._status_from_level(event.level),
                category="log",
                name=event.step_name or event.pipeline_name,
                message=event.text or "Log event.",
                fields=fields,
            )
        )

    def _on_step_completed(self, event: PipelineEvent) -> None:
        self._steps_done += 1
        fields: dict[str, Any] = {
            "duration": self._duration(event.duration_seconds),
            "metric_records": len(event.metric_records),
            "artifacts": len(event.artifacts),
        }
        if event.metrics:
            fields["metrics"] = self._inline_mapping(event.metrics, limit=10)
        self._write(
            self._status_panel(
                status="OK",
                category="step",
                name=self._step_name(event),
                message=event.text or "Step completed.",
                fields=fields,
            )
        )
        self._write(self._records_table(event))
        self._print_progress()

    def _on_step_failed(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status="FAILED",
                category="step",
                name=self._step_name(event),
                message="Step failed. The pipeline stopped before the next step.",
                fields={"duration": self._duration(event.duration_seconds), "error_type": event.error_type, "error": event.error_message},
            )
        )

    def _on_pipeline_completed(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status="OK",
                category="pipeline",
                name=event.pipeline_name,
                message="Pipeline completed successfully.",
                fields={"duration": self._duration(event.duration_seconds), **self._compact_fields(event.metrics)},
            )
        )
        self._report_hint()

    def _on_pipeline_failed(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status="FAILED",
                category="pipeline",
                name=event.pipeline_name,
                message="Pipeline failed.",
                fields={"duration": self._duration(event.duration_seconds), "error_type": event.error_type, "error": event.error_message},
            )
        )
        self._report_hint()

    def _on_preflight_failed(self, event: PipelineEvent) -> None:
        self._write(
            self._status_panel(
                status="FAILED",
                category="preflight",
                name="pipeline",
                message="No step was executed.",
                fields={"error": event.error_message},
            )
        )
        self._report_hint()

    def _configuration_table(self, metadata: dict[str, Any]) -> Any:
        rows = [
            ("Config", metadata.get("config_file", "-")),
            ("Run ID", metadata.get("run_id", "-")),
            ("Project", f"{metadata.get('project', '-')} {metadata.get('project_version', '-')}",),
            ("Environment", metadata.get("environment", "-")),
            ("Reports", metadata.get("report_dir", "-")),
            ("Graylog", f"{metadata.get('graylog', '-')} {metadata.get('graylog_protocol', '-')}://{metadata.get('graylog_host', '-')}:{metadata.get('graylog_port', '-')}",),
            ("MLflow", f"{metadata.get('mlflow', '-')} {metadata.get('mlflow_tracking_uri', '-')}",),
            ("MLflow experiment", metadata.get("mlflow_experiment", "-")),
            ("API", f"{metadata.get('api', '-')} {metadata.get('api_host', '-')}:{metadata.get('api_port', '-')}{metadata.get('api_endpoint', '-')}",),
            ("Observers", ", ".join(metadata.get("observers", []) or [])),
        ]
        if Table is None:
            return "\n".join(f"{k}: {v}" for k, v in rows)
        table = Table(title="Resolved configuration", box=box.ASCII, show_header=True, header_style="bold")
        table.add_column("Item", no_wrap=True)
        table.add_column("Value")
        for key, value in rows:
            table.add_row(str(key), self._text(value))
        steps = metadata.get("steps", []) or []
        if steps:
            table.add_section()
            table.add_row("Steps", " -> ".join(step.get("name", "-") for step in steps))
        return table

    def _status_panel(self, *, status: str, category: str, name: str, message: str, fields: dict[str, Any]) -> Any:
        clean_fields = {k: v for k, v in fields.items() if v not in (None, "", {}, [])}
        if Table is None or Panel is None:
            lines = [f"[{status.upper()}] {category}: {name}", message]
            lines.extend(f"  {k}: {v}" for k, v in clean_fields.items())
            return "\n".join(lines)
        table = Table.grid(expand=True)
        table.add_column(min_width=14, no_wrap=True)
        table.add_column(min_width=80)
        table.add_row("Status", status.upper())
        table.add_row("Scope", category)
        table.add_row("Name", name)
        table.add_row("Message", message)
        for key, value in clean_fields.items():
            table.add_row(str(key), self._text(value))
        return Panel(table, title=f"{status.upper()} {category}", box=box.ASCII, expand=False)

    def _records_table(self, event: PipelineEvent) -> Any:
        if not self.show_metrics or not event.metric_records or Table is None:
            return ""
        table = Table(title=f"Records emitted by {event.step_name}", box=box.ASCII, show_header=True)
        table.add_column("Type")
        table.add_column("Params")
        table.add_column("Metrics")
        for record in event.metric_records[:12]:
            table.add_row(record.name, self._inline_mapping(record.params, limit=4), self._inline_mapping(record.metrics, limit=6))
        if len(event.metric_records) > 12:
            table.add_row("...", f"{len(event.metric_records) - 12} more records", "")
        return table

    def _print_title(self, title: str) -> None:
        if self._console is not None:
            self._console.rule(title)
        else:
            print(f"\n{title}\n" + "=" * len(title), flush=True)

    def _print_section(self, title: str) -> None:
        if self._console is not None:
            self._console.rule(title)
        else:
            print(f"\n{title}\n" + "-" * len(title), flush=True)

    def _print_progress(self) -> None:
        if not self.progress or not self._steps_total:
            return
        percent = int((self._steps_done / self._steps_total) * 100)
        done = "#" * self._steps_done
        pending = "." * max(self._steps_total - self._steps_done, 0)
        self._write(f"Progress [{done}{pending}] {self._steps_done}/{self._steps_total} ({percent}%)")

    def _write(self, message: Any) -> None:
        if message == "":
            return
        if self._console is not None:
            self._console.print(message)
        else:
            print(message, flush=True)

    def _report_hint(self) -> None:
        if self.report_dir:
            self._write(f"Reports: {self.report_dir}")

    def _step_name(self, event: PipelineEvent) -> str:
        if event.step_index is None:
            return event.step_name or "step"
        return f"{event.step_index}. {event.step_name or 'step'}"

    def _status_from_level(self, level: str) -> str:
        level = (level or "INFO").upper()
        if level in {"ERROR", "CRITICAL"}:
            return "FAILED"
        if level == "WARNING":
            return "WARNING"
        return "INFO"

    def _compact_fields(self, mapping: dict[str, Any], limit: int = 10) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for index, (key, value) in enumerate((mapping or {}).items()):
            if index >= limit:
                result["more"] = f"{len(mapping) - limit} more fields"
                break
            if isinstance(value, (dict, list, tuple, set)):
                result[key] = self._inline_mapping(value if isinstance(value, dict) else {"values": list(value)}, limit=4)
            else:
                result[key] = value
        return result

    def _inline_mapping(self, mapping: dict[str, Any], limit: int = 6) -> str:
        if not mapping:
            return "-"
        parts = []
        items = list(mapping.items())
        for key, value in items[:limit]:
            parts.append(f"{key}={self._text(value, 80)}")
        if len(items) > limit:
            parts.append(f"+{len(items) - limit} more")
        return "; ".join(parts)

    def _text(self, value: Any, limit: int = 140) -> str:
        text = str(value)
        return text if len(text) <= limit else text[: limit - 3] + "..."

    def _duration(self, value: Any) -> str:
        if value is None or value == "":
            return "-"
        try:
            return f"{float(value):.3f}s"
        except Exception:
            return str(value)
