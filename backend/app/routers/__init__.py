"""Router registry. Add routes on these objects; the app includes this list once."""

from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.employees import router as employees_router
from app.routers.fx import router as fx_router
from app.routers.health import router as health_router

routers = [
    health_router,
    auth_router,
    employees_router,
    analytics_router,
    fx_router,
]

__all__ = [
    "analytics_router",
    "auth_router",
    "employees_router",
    "fx_router",
    "health_router",
    "routers",
]
