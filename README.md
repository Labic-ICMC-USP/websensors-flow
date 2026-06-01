# WebSensors Flow

**WebSensors Flow** is a lightweight and customizable framework for building observable data, machine learning, and GenAI pipelines.

The main goal is to keep pipeline code simple while making each execution easy to inspect, monitor, debug, and reproduce.

WebSensors Flow is especially useful for high-scale pipelines organized as a single execution flow, where each step produces structured information such as metrics, parameters, artifacts, metadata, logs, and telemetry records.

---

## Purpose

In many AI projects, observability code is mixed directly with the pipeline code. For example, a training step may call MLflow directly, or an inference step may manually send logs to an external system.

WebSensors Flow avoids this coupling.

The pipeline describes **what happened** during execution.

The observer decides **where and how this information is stored**.

This makes the same pipeline reusable with different observability backends, such as MLflow, Graylog, local files, databases, or custom APIs.

---

## Main Features

* Lightweight execution model based on flows and steps.
* Backend-independent pipeline code.
* Custom metrics, parameters, artifacts, metadata, and telemetry.
* Support for traditional machine learning and GenAI pipelines.
* Step-by-step inspection for debugging and experimentation.
* Easy integration of new projects through custom steps.
* Useful for notebooks, scripts, experiments, and production-oriented workflows.

---

## Core Concepts

### Flow

A **Flow** represents the complete pipeline execution. It defines the sequence of steps and controls how data moves from one step to the next.

### Step

A **Step** represents one stage of the pipeline, such as data loading, preprocessing, feature extraction, model training, inference, evaluation, or serialization.

### StepResult

Each step returns a `StepResult`, which may contain:

* `metrics`;
* `params`;
* `artifacts`;
* `metadata`;
* telemetry records.

### Observer

An **Observer** collects the information produced by the steps and sends it to an observability backend.

The step does not need to know whether the backend is MLflow, Graylog, a database, or another service.

---

## General Pipeline Structure

```text
Input Data
   |
   v
Flow
   |
   v
Step 1 - Data Ingestion
   |
   v
Step 2 - Preprocessing
   |
   v
Step 3 - Feature Extraction / Prompt Configuration
   |
   v
Step 4 - Training / Inference / Evaluation
   |
   v
StepResult objects
   |
   v
Observer
   |
   v
Observability Backend
```

---

## Example Use Cases

WebSensors Flow can be used in different types of pipelines, such as:

* supervised text classification;
* LLM-based text classification;
* in-context learning workflows;
* prompt evaluation;
* event analysis;
* issue extraction;
* opinion mining;
* risk analysis;
* large-scale document processing.

---

## Adding New Projects

New projects can be incorporated by defining a new flow and implementing the required steps.

A typical process is:

1. define the pipeline goal;
2. split the pipeline into steps;
3. implement each step;
4. decide which metrics, parameters, artifacts, and metadata should be observed;
5. configure one or more observers;
6. run the complete flow.

For example, a supervised text classification project may include:

```text
LoadDataStep
PreprocessTextStep
VectorizeTextStep
TrainModelStep
EvaluateModelStep
SerializeModelStep
```

A GenAI classification project may include:

```text
LoadDataStep
BuildPromptStep
LLMClassificationStep
ParsePredictionStep
EvaluatePredictionStep
AggregateTelemetryStep
```

---

## Current Tutorials

The project includes tutorial notebooks for:

### Supervised Learning

A DMOZ Health text classification pipeline using TF-IDF, train/test split, `GridSearchCV`, and Multinomial Naive Bayes.

### GenAI Classification

A DMOZ Health text classification pipeline using an LLM-based classifier with in-context learning and GenAI telemetry.

Both tutorials show how WebSensors Flow can send metrics, parameters, artifacts, metadata, and execution records to MLflow without calling MLflow directly inside the pipeline steps.

---

## Main features

- Sequential pipeline execution with an all-or-nothing policy.
- YAML configuration for the project, runtime, observers, API mode, and steps.
- Optional Graylog and MLflow observers.
- Terminal output designed for SSH sessions.
- FastAPI mode with Swagger and asynchronous run status tokens.
- Step-level metrics, parameters, artifacts, logs, and repeated metric records.
- MLflow support for datasets, models, metrics, parameters, artifacts, nested runs, and system metrics.

## Install

```bash
pip install -e .[all]
```

## Run the example flow

```bash
websensors-flow-run --config flows/example_dmoz/flow.yaml
```

## Requirements

To use the observability examples, you need:

- **MLflow**, to track metrics, parameters, artifacts, and models.
- **Graylog**, to centralize logs.

For simple tests, MLflow can be installed and executed locally:

```bash
pip install mlflow
mlflow server --host 0.0.0.0 --port 5000
````

Then open:

```text
http://localhost:5000
```

For Graylog, we recommend using **Docker** or **Docker Compose**, especially for local tests and simple deployments.

WebSensors Flow does not replace MLflow or Graylog. It only sends pipeline information to these tools through observers.

```
```

## Summary

WebSensors Flow helps build observable AI pipelines without tying the pipeline logic to a specific monitoring tool.

It provides a simple structure for organizing steps, collecting execution information, and sending it to configurable observability backends.

The result is a cleaner, more reusable, and easier-to-monitor pipeline architecture.
