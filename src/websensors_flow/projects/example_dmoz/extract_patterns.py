"""Model-selection step for the DMOZ Health classification flow.

The step searches for the best smoothing parameter of a Multinomial Naive Bayes
classifier. Each candidate model is emitted as a metric record, which allows
observers to show model-level comparisons without the step importing MLflow or
Graylog directly.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.naive_bayes import MultinomialNB

from projects.example_dmoz.utils import output_dir_from_config, write_dataframe, write_json
from websensors_flow import MetricRecord, PipelineStep, StepResult


class ExtractPatternsStep(PipelineStep):
    """Tune and evaluate a Multinomial Naive Bayes classifier."""

    name = "extract_patterns"

    def execute(self, input: dict[str, Any], context) -> StepResult:
        """Run GridSearchCV and evaluate the selected candidate on the test set."""

        config = context.step_config
        output_dir = output_dir_from_config(config, "outputs/dmoz_health/extract_patterns")
        cv_folds = int(config.get("cv_folds", context.config.pipeline.params.get("cv_folds", 3)))
        alpha_grid = [float(value) for value in config.get("alpha_grid", [0.01, 0.1, 0.5, 1.0])]

        # The search keeps both train and validation scores. Train scores help
        # detect overfitting; validation scores drive model selection.
        search = GridSearchCV(
            estimator=MultinomialNB(),
            param_grid={"alpha": alpha_grid},
            scoring={"f1_macro": "f1_macro", "accuracy": "accuracy"},
            refit="f1_macro",
            cv=cv_folds,
            n_jobs=None,
            return_train_score=True,
        )
        context.log.info(
            "Starting GridSearchCV for MultinomialNB.",
            params={"alpha_grid": alpha_grid, "cv_folds": cv_folds},
            metrics={"candidate_models": int(len(alpha_grid)), "cv_folds": cv_folds},
        )
        search.fit(input["X_train_tfidf"], input["y_train"])

        # Store a compact table with the most useful GridSearchCV columns. The
        # complete sklearn object remains in memory for the next step if needed.
        grid_results = pd.DataFrame(search.cv_results_)
        selected_columns = [
            "param_alpha",
            "mean_test_f1_macro",
            "std_test_f1_macro",
            "rank_test_f1_macro",
            "mean_test_accuracy",
            "std_test_accuracy",
            "mean_train_f1_macro",
            "mean_train_accuracy",
        ]
        grid_results_path = write_dataframe(output_dir / "grid_search_results.csv", grid_results[selected_columns])

        best_model = search.best_estimator_
        predictions = best_model.predict(input["X_test_tfidf"])
        test_accuracy = float(accuracy_score(input["y_test"], predictions))
        test_f1_macro = float(f1_score(input["y_test"], predictions, average="macro"))
        report = classification_report(input["y_test"], predictions, output_dict=True, zero_division=0)
        report_path = write_json(output_dir / "classification_report_test.json", report)

        labels = sorted(input["y_test"].unique())
        confusion = confusion_matrix(input["y_test"], predictions, labels=labels)
        confusion_frame = pd.DataFrame(confusion, index=labels, columns=labels)
        confusion_matrix_path = write_dataframe(output_dir / "confusion_matrix.csv", confusion_frame)

        # Candidate model records appear as nested runs in MLflow. They provide
        # searchable model parameters and metrics for every alpha value tested.
        metric_records: list[MetricRecord] = []
        for _, row in grid_results.iterrows():
            alpha = float(row["param_alpha"])
            metric_records.append(
                MetricRecord(
                    name="candidate_model",
                    params={
                        "model_name": f"MultinomialNB_alpha_{alpha}",
                        "algorithm": "MultinomialNB",
                        "alpha": alpha,
                        "cv_folds": cv_folds,
                    },
                    metrics={
                        "cv_f1_macro": float(row["mean_test_f1_macro"]),
                        "cv_accuracy": float(row["mean_test_accuracy"]),
                        "train_f1_macro": float(row["mean_train_f1_macro"]),
                        "train_accuracy": float(row["mean_train_accuracy"]),
                        "rank_f1_macro": int(row["rank_test_f1_macro"]),
                    },
                    metadata={"selection_metric": "f1_macro"},
                )
            )

        metric_records.append(
            MetricRecord(
                name="selected_model",
                params={
                    "model_name": "MultinomialNB",
                    "algorithm": "MultinomialNB",
                    "alpha": float(search.best_params_["alpha"]),
                    "selection_metric": "f1_macro",
                },
                metrics={
                    "best_cv_f1_macro": float(search.best_score_),
                    "test_accuracy": test_accuracy,
                    "test_f1_macro": test_f1_macro,
                },
                metadata={"evaluation_split": "test"},
                artifacts={"classification_report": report_path, "confusion_matrix": confusion_matrix_path},
            )
        )

        # Class-level records make the model behavior visible beyond one global
        # accuracy value.
        for class_name, class_metrics in report.items():
            if class_name in {"accuracy", "macro avg", "weighted avg"}:
                continue
            metric_records.append(
                MetricRecord(
                    name="class_evaluation",
                    params={"class_name": str(class_name), "model_name": "MultinomialNB"},
                    metrics={
                        "precision": float(class_metrics.get("precision", 0.0)),
                        "recall": float(class_metrics.get("recall", 0.0)),
                        "f1_score": float(class_metrics.get("f1-score", 0.0)),
                        "support": float(class_metrics.get("support", 0.0)),
                    },
                )
            )

        output = {
            **input,
            "best_alpha": float(search.best_params_["alpha"]),
            "best_cv_f1_macro": float(search.best_score_),
            "test_accuracy": test_accuracy,
            "test_f1_macro": test_f1_macro,
            "classification_report": report,
            "best_model": best_model,
            "grid_search": search,
            "predictions": predictions,
            "artifacts": {
                **input.get("artifacts", {}),
                "grid_search_results": grid_results_path,
                "classification_report_test": report_path,
                "confusion_matrix": confusion_matrix_path,
            },
        }
        metrics = {
            "candidates": int(len(alpha_grid)),
            "cv_folds": cv_folds,
            "best_alpha": float(search.best_params_["alpha"]),
            "best_cv_f1_macro": float(search.best_score_),
            "test_accuracy": test_accuracy,
            "test_f1_macro": test_f1_macro,
        }
        context.log.info(
            "GridSearchCV completed and test metrics were calculated.",
            metrics=metrics,
            metadata={"best_params": search.best_params_},
            artifacts={
                "grid_search_results": grid_results_path,
                "classification_report_test": report_path,
                "confusion_matrix": confusion_matrix_path,
            },
        )
        return StepResult(
            output=output,
            has_output=True,
            text="Selected the best MultinomialNB hyperparameter using GridSearchCV and evaluated it on the test set.",
            metrics=metrics,
            params={"cv_folds": cv_folds, "alpha_grid": str(alpha_grid)},
            metadata={"best_params": search.best_params_},
            artifacts={
                "grid_search_results": grid_results_path,
                "classification_report_test": report_path,
                "confusion_matrix": confusion_matrix_path,
            },
            metric_records=metric_records,
        )
