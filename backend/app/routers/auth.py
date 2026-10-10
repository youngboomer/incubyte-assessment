import hmac
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import bearer_token, issue_token, require_hr, token_expiry, token_hash
from app.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_PRUNE_REVOKED_SQL = text("DELETE FROM revoked_tokens WHERE expires_at <= :now")
_REVOKE_TOKEN_SQL = text(
    "INSERT OR IGNORE INTO revoked_tokens (token_hash, expires_at) "
    "VALUES (:token_hash, :expires_at)"
)


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


def _client_key(request: Request) -> str:
    if request.app.state.settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _credentials_match(settings, email: str, password: str) -> bool:
    email_ok = hmac.compare_digest(email.encode(), settings.hr_email.encode())
    if settings.hr_password_hash:
        password_ok = verify_password(password, settings.hr_password_hash)
    else:
        password_ok = hmac.compare_digest(password.encode(), settings.hr_password.encode())
    return email_ok and password_ok


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    settings = request.app.state.settings
    limiter = request.app.state.login_limiter
    client = _client_key(request)
    retry_after = limiter.retry_after(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again in a few minutes.",
            headers={"Retry-After": str(retry_after)},
        )
    if not _credentials_match(settings, body.email, body.password):
        limiter.record_failure(client)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    limiter.clear(client)
    return LoginResponse(
        access_token=issue_token(settings.app_secret, settings.hr_email),
        token_type="bearer",
    )


@router.get("/me")
async def me(email: str = Depends(require_hr)) -> MeResponse:
    return MeResponse(email=email, name="HR Manager")


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    _email: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> Response:
    token = bearer_token(request)
    _, expires_at = token_expiry(request, token)
    await session.execute(_PRUNE_REVOKED_SQL, {"now": datetime.now(UTC).isoformat()})
    await session.execute(
        _REVOKE_TOKEN_SQL,
        {"token_hash": token_hash(token), "expires_at": expires_at.isoformat()},
    )
    await session.commit()
    return Response(status_code=204)
