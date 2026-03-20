from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from db_migrate.common import get_database_url, get_schema

# Import backend Base metadata
try:
    from app.database.models import Base
    target_metadata = Base.metadata
except ImportError:
    target_metadata = None

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)



def run_migrations_offline() -> None:
    url = get_database_url()
    schema = get_schema("DB_BACKEND_SCHEMA", "public")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version",
        include_schemas=False,
        version_table_schema=None,
        default_schema=None,
    )

    with context.begin_transaction():
        context.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        context.execute(text(f'SET search_path TO "{schema}"'))
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    schema = get_schema("DB_BACKEND_SCHEMA", "backend")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        connection.execute(text(f'SET search_path TO "{schema}"'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=False,
            version_table="alembic_version",
            version_table_schema=None,
            default_schema=None,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

