"""ASGI application for the isolated public submission intake service."""

from fastapi import FastAPI

from intake.config import Settings


def create_app(settings: Settings) -> FastAPI:
    """Create the service without exposing API documentation or schema routes."""
    app = FastAPI(
        title="RV Interchange Submission Intake",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health/")
    def health():
        return {"status": "ok"}

    return app


def app_factory() -> FastAPI:
    """Load deployment configuration before starting the ASGI application."""
    return create_app(Settings.from_env())
