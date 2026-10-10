import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.deps import issue_token, token_hash
from app.main import create_app
from app.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    url = "sqlite+aiosqlite:///" + (tmp_path / "comppulse.db").resolve().as_posix()
    return Settings(database_url=url, seed_count=0)


def _auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def _login(client: TestClient, settings: Settings) -> str:
    response = client.post(
        "/auth/login", json={"email": settings.hr_email, "password": settings.hr_password}
    )
    return response.json()["access_token"]


def test_logout_revokes_only_that_token(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        first = _login(client, settings)
        time.sleep(1.1)
        second = issue_token(settings.app_secret, settings.hr_email)
        assert client.get("/auth/me", headers=_auth(first)).status_code == 200
        assert client.post("/auth/logout", headers=_auth(first)).status_code == 204
        again = client.get("/auth/me", headers=_auth(first))
        assert again.status_code == 401
        assert again.json() == {"detail": "Not authenticated"}
        assert client.post("/auth/logout", headers=_auth(first)).status_code == 401
        assert client.get("/auth/me", headers=_auth(second)).status_code == 200


def test_revocation_survives_restart(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        token = _login(client, settings)
        assert client.post("/auth/logout", headers=_auth(token)).status_code == 204
    with TestClient(create_app(settings)) as client:
        assert client.get("/auth/me", headers=_auth(token)).status_code == 401


def test_logout_requires_token(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.post("/auth/logout").status_code == 401
        assert client.post("/auth/logout", headers=_auth("garbage")).status_code == 401


def test_logout_prunes_expired_rows(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        token = _login(client, settings)
        engine = create_engine(f"sqlite:///{(tmp_path / 'comppulse.db').as_posix()}")
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO revoked_tokens VALUES ('old', :t), ('live', :f)"),
                {"t": past, "f": future},
            )
        assert client.post("/auth/logout", headers=_auth(token)).status_code == 204
        with engine.connect() as conn:
            hashes = {r[0] for r in conn.execute(text("SELECT token_hash FROM revoked_tokens"))}
        engine.dispose()
    assert hashes == {"live", token_hash(token)}
