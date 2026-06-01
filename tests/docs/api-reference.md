# API mode

API mode starts a FastAPI server for a flow.

```bash
websensors-flow-api --config flows/example_dmoz/flow.yaml
```

The server exposes:

- `GET /health`
- `POST /runs`
- `GET /status/{run_id}`
- Swagger documentation at `/docs`

The request body is generated from `api.input_fields` in the main YAML file.

A call to `POST /runs` returns a run token. The caller uses the token to poll the status endpoint while the pipeline runs in a worker thread.
