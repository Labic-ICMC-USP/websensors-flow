"""Shared file and profiling helpers for the DMOZ Health example.

The helpers keep the step classes focused on the experiment logic. They also
standardize how small artifacts are written so that reports, MLflow, and
Graylog can reference the same local paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def output_dir_from_config(config: dict[str, Any], default: str) -> Path:
    """Return the step output directory declared in YAML.

    Parameters
    ----------
    config:
        Step configuration loaded from the step YAML file.
    default:
        Directory used when the YAML file does not provide ``output_dir``.
    """

    path = Path(config.get("output_dir", default))
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: str | Path, data: Any) -> str:
    """Write a JSON artifact and return its path as a string."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(output_path)


def write_dataframe(path: str | Path, dataframe: pd.DataFrame) -> str:
    """Write a dataframe artifact as CSV and return its path as a string."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)
    return str(output_path)


def text_length_summary(series: pd.Series) -> dict[str, float]:
    """Calculate simple word-count statistics for a text column.

    These metrics help detect unexpectedly short or long documents before the
    feature extraction step starts.
    """

    lengths = series.astype(str).str.split().str.len()
    return {
        "text_words_min": float(lengths.min()),
        "text_words_mean": float(lengths.mean()),
        "text_words_median": float(lengths.median()),
        "text_words_max": float(lengths.max()),
    }
