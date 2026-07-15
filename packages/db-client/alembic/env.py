"""Alembic environment configuration for async migrations."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# shared_types is a path-based package (packages/shared-types/src); alias it
# so src.database's imports resolve when alembic runs outside pytest
import importlib.util as _ilu
import sys as _sys
import types as _types
from pathlib import Path as _Path

_shared_src = _Path(__file__).resolve().parent.parent.parent / "shared-types" / "src"
if "shared_types" not in _sys.modules and _shared_src.exists():
    _pkg = _types.ModuleType("shared_types")
    _pkg.__path__ = [str(_shared_src)]
    _sys.modules["shared_types"] = _pkg
    _spec = _ilu.spec_from_file_location("shared_types.models", _shared_src / "models.py")
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules["shared_types.models"] = _mod
    _spec.loader.exec_module(_mod)

from src.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Deployments pass the connection via environment, not by editing the ini
import os

if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])




def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
