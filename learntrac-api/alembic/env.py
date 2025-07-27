from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from src.db.models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """Get database URL from environment variables"""
    from urllib.parse import quote_plus
    
    url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('RDS_ENDPOINT')}/{os.getenv('DB_NAME')}"
    )
    
    # Ensure we use postgresql:// not postgres://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    
    # Use psycopg (v3) instead of psycopg2
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    # Manual parsing for URLs with special characters that break urlparse
    if '://' in url and '@' in url:
        scheme_rest = url.split('://', 1)
        scheme = scheme_rest[0]
        rest = scheme_rest[1]
        
        userpass_host = rest.split('@', 1)
        if len(userpass_host) == 2:
            userpass = userpass_host[0]
            host_rest = userpass_host[1]
            
            if ':' in userpass:
                username = userpass.split(':', 1)[0]
                password = userpass.split(':', 1)[1]
                
                # Encode password if it has special characters
                if any(c in password for c in '{}[]()&%'):
                    password = quote_plus(password)
                
                # Rebuild URL
                url = f'{scheme}://{username}:{password}@{host_rest}'
    
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()