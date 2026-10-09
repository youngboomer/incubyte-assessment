from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_hr
from app.directory import fetch_reference

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("")
async def read_reference(
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await fetch_reference(session)
