"""Shared bootstrap for seed scripts: sync engine + schema creation."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.models.orm import Base


def sync_database_url() -> str:
    # asyncpg URL -> psycopg2 URL for synchronous seed scripts.
    url = get_settings().database_url
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


def build_engine() -> Engine:
    return create_engine(sync_database_url(), future=True, pool_pre_ping=True)


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    Base.metadata.create_all(engine)


def truncate(engine: Engine, table: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
