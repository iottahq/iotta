"""
alembic/env.py – Alembic environment for iotta.
"""

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib
import pkgutil

import src.models as _models_pkg
from src.database import Base

for _, mod_name, _ in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"src.models.{mod_name}")

config = context.config

DB_URL = (
    f"postgresql://{os.getenv('DB_USER', 'iotta')}:"
    f"{os.getenv('DB_PASSWORD', 'iotta')}@"
    f"db:5432/"
    f"{os.getenv('DB_NAME', 'iotta')}"
)
config.set_main_option("sqlalchemy.url", DB_URL)

# DO NOT call fileConfig() here – iotta manages its own logging

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
