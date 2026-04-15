from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://idd:idd@localhost:5432/idd",
        alias="DATABASE_URL",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    cache_maxsize: int = Field(default=10_000, alias="CACHE_MAXSIZE")
    scoring_config_path: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "scoring_config.yaml"),
        alias="SCORING_CONFIG_PATH",
    )

    radii_meters: tuple[int, ...] = (10_000, 50_000, 100_000)
    resilience_graph_radius_m: int = 100_000
    resilience_articulation_radius_m: int = 20_000
    line_endpoint_snap_m: float = 1500.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
