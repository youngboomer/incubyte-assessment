from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.compensation import (
    FX_SCALE,
    NotFound,
    Unprocessable,
    list_currencies,
    update_exchange_rate,
)
from app.db import get_session
from app.deps import require_hr
from app.money import scaled_to_decimal

router = APIRouter(prefix="/fx", tags=["fx"])


def _raise_for_result(result: object) -> None:
    if isinstance(result, NotFound):
        raise HTTPException(status_code=404, detail=result.detail)
    if isinstance(result, Unprocessable):
        raise HTTPException(status_code=422, detail=result.detail)


class FxRatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units_per_usd_scaled: str = Field(max_length=20)

    @field_validator("units_per_usd_scaled")
    @classmethod
    def _rate(cls, value: str) -> str:
        rate = scaled_to_decimal(value, FX_SCALE)
        if rate <= 0:
            raise ValueError("units_per_usd_scaled must be positive")
        return value


@router.get("")
async def get_fx(
    session: AsyncSession = Depends(get_session),
    _actor: str = Depends(require_hr),
) -> list[dict[str, object]]:
    return await list_currencies(session)


@router.patch("/{code}")
async def patch_fx(
    code: str,
    body: FxRatePatch,
    session: AsyncSession = Depends(get_session),
    _actor: str = Depends(require_hr),
) -> dict[str, object]:
    result = await update_exchange_rate(session, code, body.units_per_usd_scaled)
    _raise_for_result(result)
    return result
