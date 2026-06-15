from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pastebin Service"
    VERSION: str = "1.0.0"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "pastebin"
    POSTGRES_PASSWORD: str = "pastebin_secret"
    POSTGRES_DB: str = "pastebin"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Monitoring
    PROMETHEUS_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            if self.POSTGRES_SERVER != "localhost":
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                    f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                )
            else:
                self.DATABASE_URL = (
                    f"sqlite+aiosqlite:///./pastebin.db"
                )


settings = Settings()
