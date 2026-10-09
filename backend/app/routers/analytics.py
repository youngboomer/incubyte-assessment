from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_hr
from app.stats import AnalyticsOverview, load_overview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(require_hr),
) -> AnalyticsOverview:
    return await load_overview(session)
