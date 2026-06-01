"""Final model training and serialization for the DMOZ Health flow.

The step trains the final classifier using the best hyperparameter selected by
GridSearchCV, combines the fitted TF-IDF vectorizer and classifier into one
scikit-learn pipeline, and writes a reusable model bundle to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline as SklearnPipeline

from projects.example_dmoz.utils import output_dir_from_config, write_json
from websensors_flow import MetricRecord, PipelineStep, StepResult


class PostprocessModelStep(PipelineStep):
    """Train and serialize the final text classification model."""

    name = "postprocess_model"

    def execute(self, input: dict[str, Any], context) -> StepResult:
        """Create a production-ready sklearn pipeline bundle."""

        config = context.step_config
        output_dir = output_dir_from_config(config, "outputs/dmoz_health/postprocess_model")
        model_bundle_path = Path(config.get("model_bundle_path", output_dir / "dmoz_health_model_bundle.joblib"))
        final_report_path = Path(config.get("final_report_path", output_dir / "final_model_report.json"))
        model_bundle_path.parent.mkdir(parents=True, exist_ok=True)
        final_report_path.parent.mkdir(parents=True, exist_ok=True)

        vectorizer = input["vectorizer"]
        final_model = MultinomialNB(alpha=float(input["best_alpha"]))

        # The final model is fitted on all available documents. The held-out
        # test metrics remain the unbiased evaluation already produced by the
        # model-selection step.
        context.log.info(
            "Training the final model on the complete dataset.",
            params={"best_alpha": float(input["best_alpha"])},
            metrics={
                "documents": int(len(input["dataframe"])),
                "classes": int(input["dataframe"][input["label_column"]].nunique()),
            },
        )
        final_model.fit(
            vectorizer.transform(input["dataframe"][input["text_column"]]),
            input["dataframe"][input["label_column"]],
        )

        # A single sklearn Pipeline keeps preprocessing and prediction together.
        # Loading the bundle later is enough to call ``predict`` on raw text.
        sklearn_pipeline = SklearnPipeline(steps=[("tfidf", vectorizer), ("classifier", final_model)])
        bundle = {
            "model": sklearn_pipeline,
            "best_alpha": input["best_alpha"],
            "best_cv_f1_macro": input["best_cv_f1_macro"],
            "test_accuracy": input["test_accuracy"],
            "test_f1_macro": input["test_f1_macro"],
            "text_column": input["text_column"],
            "label_column": input["label_column"],
        }
        joblib.dump(bundle, model_bundle_path)

        final_report = {
            "best_alpha": float(input["best_alpha"]),
            "best_cv_f1_macro": float(input["best_cv_f1_macro"]),
            "test_accuracy": float(input["test_accuracy"]),
            "test_f1_macro": float(input["test_f1_macro"]),
            "model_bundle_path": str(model_bundle_path),
            "classification_report": input["classification_report"],
        }
        report_path = write_json(final_report_path, final_report)
        model_size_bytes = int(model_bundle_path.stat().st_size)
        report_size_bytes = int(Path(report_path).stat().st_size)

        metrics = {
            "best_cv_f1_macro": float(input["best_cv_f1_macro"]),
            "test_accuracy": float(input["test_accuracy"]),
            "test_f1_macro": float(input["test_f1_macro"]),
            "model_size_bytes": model_size_bytes,
            "report_size_bytes": report_size_bytes,
        }

        # The model artifact is also consumed by the MLflow observer, which logs
        # it as an MLflow model when the MLflow backend is enabled.
        metric_records = [
            MetricRecord(
                name="final_model",
                params={
                    "model_name": "dmoz_health_multinomial_nb",
                    "algorithm": "MultinomialNB",
                    "alpha": float(input["best_alpha"]),
                },
                metrics={
                    "best_cv_f1_macro": float(input["best_cv_f1_macro"]),
                    "test_accuracy": float(input["test_accuracy"]),
                    "test_f1_macro": float(input["test_f1_macro"]),
                    "model_size_bytes": model_size_bytes,
                },
                metadata={"registered_model_name": "dmoz_health_multinomial_nb"},
                artifacts={"model_bundle": str(model_bundle_path), "final_report": report_path},
            ),
            MetricRecord(
                name="serialized_artifact",
                params={"artifact_name": "model_bundle", "path": str(model_bundle_path)},
                metrics={"size_bytes": model_size_bytes},
                artifacts={"model_bundle": str(model_bundle_path)},
            ),
            MetricRecord(
                name="serialized_artifact",
                params={"artifact_name": "final_report", "path": str(report_path)},
                metrics={"size_bytes": report_size_bytes},
                artifacts={"final_report": str(report_path)},
            ),
        ]
        context.log.info(
            "Final model bundle serialized.",
            metrics=metrics,
            metadata={
                "model_bundle_path": str(model_bundle_path),
                "final_report_path": report_path,
                "registered_model_name": "dmoz_health_multinomial_nb",
            },
            artifacts={"model_bundle": str(model_bundle_path), "final_report": report_path},
        )
        return StepResult(
            output={**input, "model_bundle_path": str(model_bundle_path), "final_report_path": report_path},
            has_output=True,
            text="Trained the final model on the complete dataset and serialized the preprocessing and classifier bundle.",
            metrics=metrics,
            params={"best_alpha": float(input["best_alpha"])},
            metadata={
                "model_bundle_path": str(model_bundle_path),
                "final_report_path": report_path,
                "registered_model_name": "dmoz_health_multinomial_nb",
            },
            artifacts={"model_bundle": str(model_bundle_path), "final_report": report_path},
            metric_records=metric_records,
        )
