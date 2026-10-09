from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db_engine, init_schema, session_factory
from app.routers import routers
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = Settings() if settings is None else settings
    engine = create_db_engine(app_settings.database_url)
    sessions = session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_schema(app.state.engine)
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="CompPulse", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.sessionmaker = sessions
    for router in routers:
        app.include_router(router)
    return app


app = create_app()
