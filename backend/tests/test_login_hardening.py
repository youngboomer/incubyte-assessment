from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.passwords import hash_password
from app.settings import Settings

STRONG_SECRET = "x" * 40


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    url = "sqlite+aiosqlite:///" + (tmp_path / "comppulse.db").resolve().as_posix()
    return Settings(database_url=url, seed_count=0, **overrides)


def _login(client: TestClient, password: str, email: str = "hr@acme.test", ip: str | None = None):
    headers = {"x-forwarded-for": ip} if ip else {}
    return client.post("/auth/login", json={"email": email, "password": password}, headers=headers)


def test_hashed_password(tmp_path: Path) -> None:
    settings = _settings(tmp_path, hr_password_hash=hash_password("hashed-pw"))
    with TestClient(create_app(settings)) as client:
        assert _login(client, "hashed-pw").status_code == 200
        assert _login(client, "wrong").status_code == 401
        assert _login(client, "compulse-demo").status_code == 401


def test_plain_password_and_wrong_email(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert _login(client, "compulse-demo").status_code == 200
        assert _login(client, "compulse-demo", email="x@acme.test").status_code == 401
        assert _login(client, "nope").status_code == 401


def test_malformed_configured_hash_rejects_login(tmp_path: Path) -> None:
    settings = _settings(tmp_path, hr_password_hash="garbage")
    with TestClient(create_app(settings)) as client:
        assert _login(client, "compulse-demo").status_code == 401


def test_lockout_after_failures(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        for _ in range(5):
            assert _login(client, "bad").status_code == 401
        blocked = _login(client, "bad")
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "Too many attempts. Try again in a few minutes."}
        assert int(blocked.headers["retry-after"]) > 0
        assert _login(client, "compulse-demo").status_code == 429


def test_success_resets_counter(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        for _ in range(4):
            _login(client, "bad")
        assert _login(client, "compulse-demo").status_code == 200
        for _ in range(4):
            assert _login(client, "bad").status_code == 401
        assert _login(client, "compulse-demo").status_code == 200


def test_window_expiry(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    clock = Clock()
    app.state.clock = clock
    with TestClient(app) as client:
        for _ in range(5):
            _login(client, "bad")
        blocked = _login(client, "compulse-demo")
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == "300"
        clock.now += 299
        assert _login(client, "compulse-demo").status_code == 429
        clock.now += 2
        assert _login(client, "compulse-demo").status_code == 200


def test_per_ip_isolation_with_trusted_proxy(tmp_path: Path) -> None:
    settings = _settings(tmp_path, trust_proxy_headers=True)
    with TestClient(create_app(settings)) as client:
        for _ in range(5):
            _login(client, "bad", ip="1.1.1.1")
        assert _login(client, "bad", ip="1.1.1.1").status_code == 429
        assert _login(client, "compulse-demo", ip="2.2.2.2").status_code == 200


def test_forwarded_header_ignored_by_default(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        for index in range(5):
            _login(client, "bad", ip=f"9.9.9.{index}")
        assert _login(client, "bad", ip="8.8.8.8").status_code == 429


def test_custom_limits(tmp_path: Path) -> None:
    settings = _settings(tmp_path, login_max_attempts=2)
    with TestClient(create_app(settings)) as client:
        _login(client, "bad")
        _login(client, "bad")
        assert _login(client, "bad").status_code == 429


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"app_secret": STRONG_SECRET},
        {"app_secret": "short", "hr_password": "real-password"},
        {"app_secret": STRONG_SECRET, "hr_password": "compulse-demo"},
    ],
)
def test_production_rejects_insecure(tmp_path: Path, overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="insecure_config"):
        create_app(_settings(tmp_path, app_env="production", **overrides))


def test_production_accepts_strong(tmp_path: Path) -> None:
    strong = {"app_env": "production", "app_secret": STRONG_SECRET}
    create_app(_settings(tmp_path, hr_password="real-password", **strong))
    create_app(_settings(tmp_path, hr_password_hash=hash_password("pw"), **strong))


def test_non_production_allows_defaults(tmp_path: Path) -> None:
    create_app(_settings(tmp_path, app_env="staging"))
