"""Alembic migration environment."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import all tables so metadata knows about them.
from hinge.infrastructure.db.tables import (  # noqa: F401
    chat_channel,
    chat_message,
    decision,
    profile,
    scan_run,
    session,
)
from hinge.infrastructure.db.metadata import metadata

# Allow DATABASE_URL override from settings (.env) without editing alembic.ini.
try:
    from hinge.core.config import Settings

    _settings = Settings()
    _database_url = getattr(_settings, "DATABASE_URL", None)
except Exception:  # pragma: no cover - keep alembic usable without full env
    _database_url = None

config = context.config
if _database_url:
    config.set_main_option("sqlalchemy.url", _database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
