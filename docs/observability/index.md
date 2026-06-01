# Observability

WebSensors Flow always writes local reports. Graylog and MLflow are optional external observers.

Step developers use only `context.log`. The same log event can be printed to the console, sent to Graylog, and recorded in MLflow without changing step code.
