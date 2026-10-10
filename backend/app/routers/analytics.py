from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_hr
from app.stats import AnalyticsOverview, load_overview

router = APIRouter(prefix="/analytics", tags=["analytics"])

_Level = Literal["IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"]


@router.get("/overview")
async def overview(
    department_id: int | None = None,
    country: str | None = None,
    level: _Level | None = None,
    currency: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(require_hr),
) -> AnalyticsOverview:
    return await load_overview(session, department_id, country, level, currency)
