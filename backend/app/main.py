import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db_engine, init_schema, session_factory
from app.login_limiter import LoginLimiter
from app.routers import routers
from app.seed import seed_if_empty
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = Settings() if settings is None else settings
    app_settings.assert_secure()
    engine = create_db_engine(app_settings.database_url)
    sessions = session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_schema(app.state.engine)
        await seed_if_empty(app.state.engine, app_settings.seed_count)
        yield
        await app.state.engine.dispose()

    docs_off = {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(
        title="CompPulse",
        lifespan=lifespan,
        **(docs_off if app_settings.app_env == "production" else {}),
    )
    app.state.settings = app_settings
    app.state.clock = time.monotonic
    app.state.login_limiter = LoginLimiter(
        app_settings.login_max_attempts,
        app_settings.login_window_seconds,
        lambda: app.state.clock(),
    )
    app.state.engine = engine
    app.state.sessionmaker = sessions
    for router in routers:
        app.include_router(router)
    return app


app = create_app()
