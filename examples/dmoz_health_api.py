"""Start the FastAPI app for the DMOZ Health flow."""

from __future__ import annotations

import uvicorn

from websensors_flow import create_app, load_settings


CONFIG_PATH = "flows/example_dmoz/flow.yaml"


if __name__ == "__main__":
    settings = load_settings(CONFIG_PATH)
    app = create_app(settings)
    uvicorn.run(app, host=settings.api.host, port=settings.api.port)
