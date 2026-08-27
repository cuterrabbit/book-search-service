from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "query-service"
    es_host: str = "localhost"
    es_port: int = 9200


@lru_cache
def get_settings() -> Settings:
    return Settings()
