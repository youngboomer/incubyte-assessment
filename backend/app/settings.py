from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./comppulse.db"
    app_secret: str = "dev-secret-change-me"
    hr_email: str = "hr@acme.test"
    hr_password: str = "compulse-demo"
    token_max_age_seconds: int = 43200
    seed_count: int = 10000
