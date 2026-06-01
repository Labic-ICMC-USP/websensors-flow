"""Text preprocessing step for the DMOZ Health classification flow.

The step receives the dataframe created by the ingestion step, creates a
stratified train/test split, and fits a TF-IDF bag-of-words representation on
the training texts. The fitted vectorizer and sparse matrices are kept in the
step output for the model-selection step.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from projects.example_dmoz.utils import output_dir_from_config, write_dataframe, write_json
from websensors_flow import MetricRecord, PipelineStep, StepResult


class PreprocessTextStep(PipelineStep):
    """Create train/test data and a TF-IDF text representation."""

    name = "preprocess_text"

    def execute(self, input: dict[str, Any], context) -> StepResult:
        """Transform raw text into numeric features for classification."""

        config = context.step_config
        df = input["dataframe"]
        text_column = input["text_column"]
        label_column = input["label_column"]
        output_dir = output_dir_from_config(config, "outputs/dmoz_health/preprocess_text")

        # Step YAML values take precedence. Pipeline-level parameters provide a
        # convenient default shared by multiple steps.
        test_size = float(config.get("test_size", context.config.pipeline.params.get("test_size", 0.25)))
        random_state = int(config.get("random_state", context.config.pipeline.params.get("random_state", 42)))
        max_features = int(config.get("max_features", 5000))
        min_df = int(config.get("min_df", 2))
        ngram_range = tuple(config.get("ngram_range", [1, 2]))
        stop_words = config.get("stop_words", "english")

        context.log.info(
            "Creating stratified train/test split.",
            params={"test_size": test_size, "random_state": random_state},
            metrics={"documents": int(len(df)), "classes": int(df[label_column].nunique())},
        )
        X_train, X_test, y_train, y_test = train_test_split(
            df[text_column],
            df[label_column],
            test_size=test_size,
            random_state=random_state,
            stratify=df[label_column],
        )

        # The vectorizer learns the vocabulary only from the training partition.
        # The test partition is transformed with the fitted vocabulary to avoid
        # leaking information from evaluation data into preprocessing.
        context.log.info(
            "Fitting TF-IDF vectorizer.",
            params={
                "max_features": max_features,
                "min_df": min_df,
                "ngram_range": str(ngram_range),
                "stop_words": stop_words,
            },
        )
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=stop_words,
            max_features=max_features,
            min_df=min_df,
            ngram_range=ngram_range,
        )
        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)

        # Small CSV/JSON artifacts make the representation auditable without
        # serializing the full sparse matrices to the report directory.
        vocabulary = vectorizer.get_feature_names_out()
        vocabulary_preview = pd.DataFrame({"term": vocabulary[: min(200, len(vocabulary))]})
        vocabulary_path = write_dataframe(output_dir / "vocabulary_preview.csv", vocabulary_preview)
        vectorizer_profile_path = write_json(
            output_dir / "vectorizer_profile.json",
            {
                "max_features": max_features,
                "min_df": min_df,
                "ngram_range": list(ngram_range),
                "stop_words": stop_words,
                "vocabulary_size": int(len(vocabulary)),
                "train_shape": list(X_train_tfidf.shape),
                "test_shape": list(X_test_tfidf.shape),
            },
        )
        train_sample_path = write_dataframe(
            output_dir / "train_sample.csv",
            pd.DataFrame({text_column: X_train, label_column: y_train}).head(200),
        )
        test_sample_path = write_dataframe(
            output_dir / "test_sample.csv",
            pd.DataFrame({text_column: X_test, label_column: y_test}).head(200),
        )

        train_counts = y_train.value_counts().sort_index()
        test_counts = y_test.value_counts().sort_index()
        split_distribution = pd.DataFrame({"class_name": sorted(set(train_counts.index).union(test_counts.index))})
        split_distribution["train_documents"] = split_distribution["class_name"].map(train_counts).fillna(0).astype(int)
        split_distribution["test_documents"] = split_distribution["class_name"].map(test_counts).fillna(0).astype(int)
        split_distribution_path = write_dataframe(output_dir / "split_distribution.csv", split_distribution)

        train_density = float(X_train_tfidf.nnz / (X_train_tfidf.shape[0] * X_train_tfidf.shape[1]))
        test_density = float(X_test_tfidf.nnz / (X_test_tfidf.shape[0] * X_test_tfidf.shape[1]))
        metrics = {
            "train_rows": int(X_train_tfidf.shape[0]),
            "test_rows": int(X_test_tfidf.shape[0]),
            "vocabulary_size": int(len(vectorizer.vocabulary_)),
            "train_nonzero": int(X_train_tfidf.nnz),
            "test_nonzero": int(X_test_tfidf.nnz),
            "train_density": train_density,
            "test_density": test_density,
        }

        # Dataset records for the train and test partitions are logged as MLflow
        # inputs. Their samples are also uploaded as artifacts.
        metric_records = [
            MetricRecord(
                name="dataset",
                params={
                    "dataset_name": "Dmoz-Health train split",
                    "source": "train_test_split",
                    "rows": int(len(X_train)),
                    "target_column": label_column,
                },
                metrics={"rows": int(len(X_train)), "classes": int(y_train.nunique()), "test_size": test_size},
                metadata={"context": "training", "random_state": random_state},
                artifacts={"dataset_sample": train_sample_path},
            ),
            MetricRecord(
                name="dataset",
                params={
                    "dataset_name": "Dmoz-Health test split",
                    "source": "train_test_split",
                    "rows": int(len(X_test)),
                    "target_column": label_column,
                },
                metrics={"rows": int(len(X_test)), "classes": int(y_test.nunique()), "test_size": test_size},
                metadata={"context": "evaluation", "random_state": random_state},
                artifacts={"dataset_sample": test_sample_path},
            ),
        ]
        for _, row in split_distribution.iterrows():
            metric_records.append(
                MetricRecord(
                    name="split_class_distribution",
                    params={"class_name": str(row["class_name"])},
                    metrics={"train_documents": int(row["train_documents"]), "test_documents": int(row["test_documents"])},
                )
            )

        context.log.info(
            "TF-IDF representation created.",
            metrics=metrics,
            artifacts={
                "vocabulary_preview": vocabulary_path,
                "split_distribution": split_distribution_path,
                "vectorizer_profile": vectorizer_profile_path,
                "train_sample": train_sample_path,
                "test_sample": test_sample_path,
            },
        )

        output = {
            **input,
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test,
            "X_train_tfidf": X_train_tfidf,
            "X_test_tfidf": X_test_tfidf,
            "vectorizer": vectorizer,
            "artifacts": {
                **input.get("artifacts", {}),
                "vocabulary_preview": vocabulary_path,
                "split_distribution": split_distribution_path,
                "vectorizer_profile": vectorizer_profile_path,
            },
        }
        return StepResult(
            output=output,
            has_output=True,
            text="Created the train/test split and the TF-IDF bag-of-words representation.",
            metrics=metrics,
            params={
                "test_size": test_size,
                "random_state": random_state,
                "max_features": max_features,
                "min_df": min_df,
                "ngram_range": str(ngram_range),
                "stop_words": stop_words,
            },
            artifacts={
                "vocabulary_preview": vocabulary_path,
                "split_distribution": split_distribution_path,
                "vectorizer_profile": vectorizer_profile_path,
                "train_sample": train_sample_path,
                "test_sample": test_sample_path,
            },
            metric_records=metric_records,
        )
