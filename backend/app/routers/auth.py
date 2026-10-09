from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.deps import issue_token, require_hr

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


class MeResponse(BaseModel):
    email: str
    name: str


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    settings = request.app.state.settings
    if body.email != settings.hr_email or body.password != settings.hr_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(
        access_token=issue_token(settings.app_secret, settings.hr_email),
        token_type="bearer",
    )


@router.get("/me")
async def me(email: str = Depends(require_hr)) -> MeResponse:
    return MeResponse(email=email, name="HR Manager")
