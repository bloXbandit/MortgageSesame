"""
Alembic environment configuration — async SQLAlchemy.

Supports both SQLite (dev) and PostgreSQL (prod).
DATABASE_URL is read from the .env file at runtime; alembic.ini provides
the fallback SQLite URL for local use without a .env.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import all models so Alembic sees them for autogenerate ──────────────────
# This import triggers all SQLAlchemy model registrations.
from app.database import Base
import app.models  # noqa: F401 — side-effect: registers all Table metadata

# alembic.ini-level logging config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata

# ── Resolve DATABASE_URL ─────────────────────────────────────────────────────
# Priority: env var DATABASE_URL → .env file → alembic.ini sqlalchemy.url

def _get_url() -> str:
    """Read DATABASE_URL from environment, falling back to alembic.ini value."""
    # Try loading .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

    # SQLAlchemy 2 needs async drivers; patch postgres:// → postgresql+asyncpg://
    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


# ── Offline migration (generates SQL without connecting) ─────────────────────

def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migration (connects and executes) ──────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = _get_url()
    connectable = async_engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
