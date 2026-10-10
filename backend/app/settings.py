from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-secret-change-me"
DEFAULT_PASSWORD = "compulse-demo"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./comppulse.db"
    app_secret: str = DEFAULT_SECRET
    hr_email: str = "hr@acme.test"
    hr_password: str = DEFAULT_PASSWORD
    hr_password_hash: str | None = None
    app_env: str = "development"
    trust_proxy_headers: bool = False
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    token_max_age_seconds: int = 43200
    seed_count: int = 10000

    def assert_secure(self) -> None:
        if self.app_env != "production":
            return
        problems = []
        if self.app_secret == DEFAULT_SECRET or len(self.app_secret) < MIN_SECRET_LENGTH:
            problems.append(f"APP_SECRET must be non-default, {MIN_SECRET_LENGTH}+ chars")
        if not self.hr_password_hash and self.hr_password == DEFAULT_PASSWORD:
            problems.append("HR_PASSWORD must not be the demo default (or set HR_PASSWORD_HASH)")
        if problems:
            raise ValueError("insecure_config: " + "; ".join(problems))
