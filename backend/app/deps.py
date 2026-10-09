from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

COOKIE_SALT = "comppulse-session"


def signer(secret: str) -> TimestampSigner:
    return TimestampSigner(secret, salt=COOKIE_SALT)


def issue_token(secret: str, email: str) -> str:
    return signer(secret).sign(email.encode()).decode()


def require_hr(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    settings = request.app.state.settings
    try:
        raw = signer(settings.app_secret).unsign(
            token, max_age=settings.token_max_age_seconds
        )
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status_code=401, detail="Not authenticated") from exc
    email = raw.decode()
    if email != settings.hr_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email
