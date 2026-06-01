# WebSensors Flow

WebSensors Flow executes Python steps defined in YAML and records the execution in terminal reports, Graylog, and MLflow.

The framework is intentionally small. A step receives an input object and a context. The context provides the main flow configuration, the current step configuration, the logger, and the run metadata.

## Execution model

1. Load the main YAML file.
2. Load the YAML file of each step.
3. Build the observers selected in the main YAML file.
4. Run preflight checks and probes.
5. Execute each step in order.
6. Stop the pipeline if any step fails.
7. Write reports and close observers.

## Example

The included example classifies DMOZ Health documents using TF-IDF and Multinomial Naive Bayes. Each step emits metrics, parameters, artifacts, and metric records so that Graylog and MLflow receive detailed observability data.
