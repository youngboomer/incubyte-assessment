from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.passwords import hash_password
from app.settings import Settings


@pytest.mark.parametrize("env,status", [("production", 404), ("development", 200)])
def test_interactive_docs_only_outside_production(tmp_path: Path, env: str, status: int) -> None:
    url = "sqlite+aiosqlite:///" + (tmp_path / "comppulse.db").resolve().as_posix()
    settings = Settings(
        database_url=url,
        seed_count=0,
        app_env=env,
        app_secret="x" * 40,
        hr_password_hash=hash_password("pw"),
    )
    with TestClient(create_app(settings)) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == status
