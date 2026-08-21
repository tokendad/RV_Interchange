"""ASGI application for the isolated public submission intake service."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI

from intake.config import Settings
from intake.db import migrate
from intake.routers.submissions import router as submissions_router
from intake.routers.verification import router as verification_router
from intake.security import new_secret
from intake.turnstile import TurnstileVerifier


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_app(
    settings: Settings,
    *,
    turnstile_verifier: TurnstileVerifier | None = None,
    clock: Callable[[], datetime] = _utc_now,
    secret_factory: Callable[[], str] = new_secret,
) -> FastAPI:
    """Create the service without exposing API documentation or schema routes."""

    owns_turnstile_verifier = turnstile_verifier is None
    if turnstile_verifier is None:
        try:
            turnstile_secret = settings.turnstile_secret_path.read_text().strip()
        except (OSError, UnicodeDecodeError) as error:
            raise RuntimeError("turnstile secret file must be readable text") from error
        turnstile_verifier = TurnstileVerifier(turnstile_secret)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        migrate(settings.database_path)
        try:
            yield
        finally:
            if owns_turnstile_verifier:
                turnstile_verifier.close()

    app = FastAPI(
        title="RV Interchange Submission Intake",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.turnstile_verifier = turnstile_verifier
    app.state.clock = clock
    app.state.secret_factory = secret_factory
    app.include_router(verification_router)
    app.include_router(submissions_router)

    @app.get("/health/")
    def health():
        return {"status": "ok"}

    return app


def app_factory() -> FastAPI:
    """Load deployment configuration before starting the ASGI application."""
    return create_app(Settings.from_env())
