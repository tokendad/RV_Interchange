from contextlib import asynccontextmanager

from fastapi import FastAPI

from intake import db
from review.config import Settings
from review.routers import router


def create_app(settings: Settings | None = None, validator=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_app):
        db.migrate(settings.database_path)
        yield

    app = FastAPI(title="RV Interchange Review", lifespan=lifespan)

    @app.get("/health/")
    def health():
        return {"status": "ok"}

    app.include_router(router(settings, validator))
    return app




def app_factory() -> FastAPI:
    return create_app(Settings.from_env())
