from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "outbox-relay"
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "book_user"
    db_password: str = "book_password"
    db_name: str = "book_search"
    es_host: str = "localhost"
    es_port: int = 9200
    poll_interval_seconds: float = 1.0

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
