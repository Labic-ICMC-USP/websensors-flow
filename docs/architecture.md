# Architecture

WebSensors Flow has five main parts:

1. configuration loading and validation;
2. pipeline execution;
3. step context and structured logging;
4. observers for console, local reports, Graylog, and MLflow;
5. optional FastAPI execution.

The pipeline engine is object-agnostic. It passes step outputs to later steps but does not inspect or serialize those objects.
