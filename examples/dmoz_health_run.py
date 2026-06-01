"""Run the DMOZ Health flow from a YAML configuration file."""

from __future__ import annotations

from websensors_flow import load_settings, run_configured_flow


CONFIG_PATH = "flows/example_dmoz/flow.yaml"


if __name__ == "__main__":
    settings = load_settings(CONFIG_PATH)
    result = run_configured_flow(settings)
    print(f"status={result.report.status}")
    print(f"run_id={result.report.run_id}")
    print(f"reports={settings.runtime.report_dir}/{result.report.run_id}/")
    if result.failure is not None:
        print(result.failure.text)
