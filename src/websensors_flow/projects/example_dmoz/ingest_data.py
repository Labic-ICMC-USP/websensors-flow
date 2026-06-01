"""Data ingestion step for the DMOZ Health classification flow.

The step reads a CSV collection, validates the expected schema, creates a small
profile of the dataset, and returns a dataframe for the next step. The same
method also emits metrics, artifacts, and repeated records so that the active
observers can publish the dataset information to the console, reports, MLflow,
and Graylog.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from projects.example_dmoz.utils import output_dir_from_config, text_length_summary, write_dataframe, write_json
from websensors_flow import MetricRecord, PipelineStep, StepResult


class IngestDataStep(PipelineStep):
    """Load and profile the input CSV collection."""

    name = "ingest_data"

    def execute(self, input: Any, context) -> StepResult:
        """Read the configured CSV file and prepare the raw dataset.

        The input object is optional in this step. When the flow is executed by
        an API caller, the request payload may override the default ``data_url``.
        During a regular command-line run, the value comes from the step YAML.
        """

        config = context.step_config
        input_payload = input if isinstance(input, dict) else {}

        # The dataset location is part of the experiment definition. It is kept
        # as a parameter because changing the input collection changes the run.
        data_url = input_payload.get("data_url") or config["data_url"]
        text_column = config.get("text_column", "text")
        label_column = config.get("label_column", "class")
        id_column = config.get("id_column", "file_name")
        output_dir = output_dir_from_config(config, "outputs/dmoz_health/ingest_data")

        context.log.info("Reading CSV data.", params={"data_url": data_url})
        df = pd.read_csv(data_url)

        # A step should fail early when the input contract is broken. The
        # pipeline catches the exception, logs it, and stops the run before the
        # next step starts.
        required_columns = {id_column, text_column, label_column}
        missing_columns = sorted(required_columns - set(df.columns))
        if missing_columns:
            raise ValueError(f"The input CSV is missing columns: {missing_columns}")

        # Keep only the columns used by the flow and remove rows that cannot be
        # used by a supervised text classifier.
        raw_rows = int(len(df))
        df = df[[id_column, text_column, label_column]].dropna().copy()
        df[text_column] = df[text_column].astype(str)
        df[label_column] = df[label_column].astype(str)

        # Basic dataset profiling is useful for both reports and MLflow's
        # dataset view. The artifacts are small and easy to inspect after a run.
        class_counts = df[label_column].value_counts().sort_index()
        length_metrics = text_length_summary(df[text_column])
        class_distribution = class_counts.rename_axis("class_name").reset_index(name="documents")
        class_distribution["percentage"] = class_distribution["documents"] / len(df)

        dataset_sample_path = write_dataframe(output_dir / "dataset_sample.csv", df.head(200))
        class_distribution_path = write_dataframe(output_dir / "class_distribution.csv", class_distribution)
        dataset_profile_path = write_json(
            output_dir / "dataset_profile.json",
            {
                "data_url": data_url,
                "raw_rows": raw_rows,
                "rows_after_dropna": int(len(df)),
                "columns": list(df.columns),
                "classes": int(df[label_column].nunique()),
                "text_length": length_metrics,
            },
        )

        # The dataset record is interpreted by the MLflow observer as a dataset
        # input. It allows MLflow to display a dataset entry for the run.
        metric_records = [
            MetricRecord(
                name="dataset",
                params={
                    "dataset_name": "Dmoz-Health",
                    "source": data_url,
                    "rows": int(len(df)),
                    "target_column": label_column,
                },
                metrics={
                    "rows": int(len(df)),
                    "classes": int(df[label_column].nunique()),
                    "raw_rows": raw_rows,
                },
                metadata={"context": "raw_ingestion", "text_column": text_column, "id_column": id_column},
                artifacts={"dataset_sample": dataset_sample_path, "dataset_profile": dataset_profile_path},
            )
        ]

        # One record per class makes the class distribution searchable and
        # comparable in observability backends.
        for _, row in class_distribution.iterrows():
            metric_records.append(
                MetricRecord(
                    name="class_distribution",
                    params={"class_name": str(row["class_name"])},
                    metrics={"documents": int(row["documents"]), "percentage": float(row["percentage"])},
                )
            )

        metrics = {
            "raw_rows": raw_rows,
            "rows": int(len(df)),
            "dropped_rows": raw_rows - int(len(df)),
            "classes": int(df[label_column].nunique()),
            **length_metrics,
        }
        context.log.info(
            "CSV data loaded and profiled.",
            metrics=metrics,
            metadata={
                "columns": list(df.columns),
                "class_distribution_path": class_distribution_path,
                "dataset_sample_path": dataset_sample_path,
            },
            artifacts={
                "class_distribution": class_distribution_path,
                "dataset_profile": dataset_profile_path,
                "dataset_sample": dataset_sample_path,
            },
        )

        output = {
            "dataframe": df,
            "id_column": id_column,
            "text_column": text_column,
            "label_column": label_column,
            "artifacts": {
                "class_distribution": class_distribution_path,
                "dataset_profile": dataset_profile_path,
            },
        }
        return StepResult(
            output=output,
            has_output=True,
            text="Loaded the DMOZ Health text collection from CSV and generated an ingestion profile.",
            metrics=metrics,
            params={"data_url": data_url, "id_column": id_column, "text_column": text_column, "label_column": label_column},
            metadata={"columns": list(df.columns)},
            artifacts={
                "class_distribution": class_distribution_path,
                "dataset_profile": dataset_profile_path,
                "dataset_sample": dataset_sample_path,
            },
            metric_records=metric_records,
        )
