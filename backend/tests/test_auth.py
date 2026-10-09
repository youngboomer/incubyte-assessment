from pathlib import Path

from fastapi.testclient import TestClient

from app.deps import issue_token, signer
from app.main import create_app
from app.settings import Settings


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def _settings(tmp_path: Path) -> Settings:
    return Settings(database_url=_sqlite_url(tmp_path / "comppulse.db"), seed_count=0)


def test_login_success(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": settings.hr_email, "password": settings.hr_password},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        token = body["access_token"]
        assert isinstance(token, str) and token
        assert (
            signer(settings.app_secret)
            .unsign(token, max_age=settings.token_max_age_seconds)
            .decode()
            == settings.hr_email
        )
        me = client.get("/auth/me", headers={"authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json() == {"email": settings.hr_email, "name": "HR Manager"}


def test_login_wrong_password(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": settings.hr_email, "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials"}


def test_me_with_and_without_token(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        missing = client.get("/auth/me")
        assert missing.status_code == 401
        assert missing.json() == {"detail": "Not authenticated"}

        logged_in = client.post(
            "/auth/login",
            json={"email": settings.hr_email, "password": settings.hr_password},
        )
        token = logged_in.json()["access_token"]
        me = client.get("/auth/me", headers={"authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json() == {"email": settings.hr_email, "name": "HR Manager"}

        other = issue_token(settings.app_secret, "other@acme.test")
        rejected = client.get("/auth/me", headers={"authorization": f"Bearer {other}"})
        assert rejected.status_code == 401
        assert rejected.json() == {"detail": "Not authenticated"}
