from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def test_health(tmp_path: Path) -> None:
    db_path = tmp_path / "comppulse.db"
    app = create_app(Settings(database_url=_sqlite_url(db_path)))
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "https://example.test"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "access-control-allow-origin" not in {key.lower() for key in response.headers}
        assert client.get("/employees").status_code == 404
        assert client.get("/analytics/overview").status_code == 404
        assert client.get("/fx").status_code == 404
        login = client.post("/auth/login", json={"email": "hr@acme.test", "password": "x"})
        assert login.status_code == 404
    assert db_path.exists()


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DATABASE_URL",
        "APP_SECRET",
        "HR_EMAIL",
        "HR_PASSWORD",
        "TOKEN_MAX_AGE_SECONDS",
        "SEED_COUNT",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    assert settings.database_url == "sqlite+aiosqlite:///./comppulse.db"
    assert settings.app_secret == "dev-secret-change-me"
    assert settings.hr_email == "hr@acme.test"
    assert settings.hr_password == "compulse-demo"
    assert settings.token_max_age_seconds == 43200
    assert settings.seed_count == 10000


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./override.db")
    monkeypatch.setenv("APP_SECRET", "secret")
    monkeypatch.setenv("HR_EMAIL", "hr@example.test")
    monkeypatch.setenv("HR_PASSWORD", "pw")
    monkeypatch.setenv("TOKEN_MAX_AGE_SECONDS", "10")
    monkeypatch.setenv("SEED_COUNT", "3")
    settings = Settings()
    assert settings.database_url == "sqlite+aiosqlite:///./override.db"
    assert settings.app_secret == "secret"
    assert settings.hr_email == "hr@example.test"
    assert settings.hr_password == "pw"
    assert settings.token_max_age_seconds == 10
    assert settings.seed_count == 3
