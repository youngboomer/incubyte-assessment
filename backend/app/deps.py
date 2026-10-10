import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

COOKIE_SALT = "comppulse-session"
_REVOKED_SQL = text("SELECT 1 FROM revoked_tokens WHERE token_hash = :token_hash")


def signer(secret: str) -> TimestampSigner:
    return TimestampSigner(secret, salt=COOKIE_SALT)


def issue_token(secret: str, email: str) -> str:
    return signer(secret).sign(email.encode()).decode()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def token_expiry(request: Request, token: str) -> tuple[str, datetime]:
    settings = request.app.state.settings
    try:
        raw, issued_at = signer(settings.app_secret).unsign(
            token, max_age=settings.token_max_age_seconds, return_timestamp=True
        )
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status_code=401, detail="Not authenticated") from exc
    email = raw.decode()
    if email != settings.hr_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email, issued_at.astimezone(UTC) + timedelta(seconds=settings.token_max_age_seconds)


async def require_hr(request: Request, session: AsyncSession = Depends(get_session)) -> str:
    token = bearer_token(request)
    email, _ = token_expiry(request, token)
    revoked = await session.execute(_REVOKED_SQL, {"token_hash": token_hash(token)})
    if revoked.first() is not None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email
