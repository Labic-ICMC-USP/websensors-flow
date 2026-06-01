import os

import pytest

from websensors_flow.config import ConfigurationError, load_settings


def test_disabled_observers_do_not_require_service_values(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: test_pipeline
environment:
  name: test
observability:
  mlflow:
    enabled: false
  graylog:
    enabled: false
"""
    )
    settings = load_settings(config)
    assert settings.observability.mlflow.enabled is False
    assert settings.observability.graylog.enabled is False


def test_enabled_yaml_values_are_exported_to_environment(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: test_pipeline
environment:
  name: test
observability:
  mlflow:
    enabled: true
    tracking_uri: file:./mlruns
    experiment_name: test-exp
  graylog:
    enabled: true
    host: 127.0.0.1
    port: 12201
"""
    )
    settings = load_settings(config)
    assert settings.observability.mlflow.tracking_uri == "file:./mlruns"
    assert os.environ["MLFLOW_TRACKING_URI"] == "file:./mlruns"
    assert os.environ["GRAYLOG_HOST"] == "127.0.0.1"


def test_enabled_missing_yaml_uses_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "file:./env-mlruns")
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "env-exp")
    monkeypatch.setenv("GRAYLOG_HOST", "graylog.local")
    monkeypatch.setenv("GRAYLOG_PORT", "12202")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: env_pipeline
environment:
  name: homolog
observability:
  mlflow:
    enabled: true
  graylog:
    enabled: true
"""
    )
    settings = load_settings(config)
    assert settings.observability.mlflow.tracking_uri == "file:./env-mlruns"
    assert settings.observability.graylog.host == "graylog.local"
    assert settings.observability.graylog.port == 12202


def test_auth_enabled_requires_secret(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: bad_auth
environment:
  name: test
observability:
  mlflow:
    enabled: true
    tracking_uri: file:./mlruns
    experiment_name: exp
    auth:
      enabled: true
"""
    )
    with pytest.raises(ConfigurationError):
        load_settings(config)


def test_unknown_top_level_keys_are_rejected(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: invalid_pipeline
environment:
  name: test
profiles:
  prod:
    environment:
      name: prod
"""
    )
    with pytest.raises(ConfigurationError):
        load_settings(config)


def test_step_config_file_is_loaded(tmp_path):
    (tmp_path / "steps").mkdir()
    (tmp_path / "steps" / "a.yaml").write_text("threshold: 0.7\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
project:
  name: step_config_pipeline
environment:
  name: test
steps:
  - name: step_a
    class_path: tests.fake.StepA
    config_path: steps/a.yaml
    config:
      limit: 10
"""
    )
    settings = load_settings(config)
    assert settings.get_step_config("step_a") == {"threshold": 0.7, "limit": 10}
