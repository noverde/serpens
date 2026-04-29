"""Helper to wire Alembic migrations against an app's `Base.metadata` with serpens defaults.

Usage in `migrations/env.py`:

    from myapp.models import Base
    from serpens.database.alembic import run_migrations

    run_migrations(target_metadata=Base.metadata)

This handles offline/online mode, picks `DATABASE_URL` from envvars, and uses
psycopg2 for sync migrations (Alembic doesn't run async).
"""

import os

try:
    from alembic import context  # type: ignore
except ImportError:  # pragma: no cover
    context = None

from sqlalchemy import create_engine, pool


def _resolve_url(url=None):
    url = url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql+asyncpg://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgresql+asyncpg://")
    return url


def run_migrations(target_metadata, url=None):
    """Run Alembic migrations in offline or online mode against `target_metadata`."""
    if context is None:
        raise RuntimeError("alembic is not installed; add it to your app's requirements")

    db_url = _resolve_url(url)

    if context.is_offline_mode():
        context.configure(
            url=db_url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_engine(db_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
