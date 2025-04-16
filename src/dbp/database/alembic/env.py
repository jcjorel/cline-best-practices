###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Provides the Alembic environment configuration for database migrations.
# This file is responsible for connecting to the database and initializing the
# migration environment based on the project's configuration.
###############################################################################
# [Source file design principles]
# - Integrates with the application's configuration system
# - Ensures proper access to all models for automatic revision generation
# - Supports both online and offline migration operations
# - Provides flexibility for different database backends
# - Logs migration operations appropriately
###############################################################################
# [Source file constraints]
# - Must not introduce circular imports with application code
# - Should gracefully handle missing configuration
# - Must import all models to ensure they're included in migrations
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T18:08:07Z : Initial creation of Alembic environment by CodeAssistant
# * Set up database connection configuration
# * Added model import mechanism
# * Configured logging
###############################################################################

from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the src directory to the path so we can import application modules
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

# Import the SQLAlchemy declarative Base and all models
from dbp.database.models import Base
# Import all models to ensure they're included in migrations
from dbp.database import models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """
    [Function intent]
    Dynamically generates a database URL based on application configuration.
    
    [Implementation details]
    Attempts to get configuration from the component system if available,
    falls back to environment variables or default sqlite path if needed.
    
    [Design principles]
    Flexibility in configuration sources with sensible defaults.
    
    Returns:
        str: A SQLAlchemy connection URL
    """
    try:
        # Try to get configuration from the application's component system
        from dbp.core.system import ComponentSystem
        system = ComponentSystem.get_instance()
        
        # Only proceed if system is initialized
        if system and system.is_initialized():
            config_manager = system.get_component("config_manager")
            if config_manager:
                db_type = config_manager.get('database.type', 'sqlite')
                
                if db_type == 'sqlite':
                    db_path = config_manager.get('database.path', '~/.dbp/metadata.db')
                    db_path = os.path.expanduser(db_path)
                    return f"sqlite:///{db_path}"
                elif db_type == 'postgresql':
                    return config_manager.get('database.connection_string')
    except (ImportError, AttributeError, Exception) as e:
        print(f"Warning: Could not get database configuration from component system: {e}")
    
    # Fallback to environment variables
    url = os.environ.get("DBP_DATABASE_URL")
    if url:
        return url
        
    # Ultimate fallback - use a default sqlite database
    default_path = os.path.expanduser("~/.dbp/metadata.db")
    # Ensure directory exists
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    return f"sqlite:///{default_path}"


def run_migrations_offline() -> None:
    """
    [Function intent]
    Run migrations in 'offline' mode for generating SQL scripts.
    
    [Implementation details]
    Configures the context with connection URL and executes migration directives
    to generate SQL rather than execute it directly on a database.
    
    [Design principles]
    Support offline migration generation for review or deployment scenarios.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
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
    """
    [Function intent]
    Run migrations in 'online' mode for direct database updates.
    
    [Implementation details]
    Creates a connection engine and executes migrations directly on the database.
    Handles connection configuration based on the application settings.
    
    [Design principles]
    Efficient and reliable database migration with proper connection handling.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override the URL in the alembic.ini
    config_section = config.get_section(config.config_ini_section)
    config_section['sqlalchemy.url'] = get_url()
    
    connectable = engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
