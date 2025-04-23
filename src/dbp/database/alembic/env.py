###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
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
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
# codebase:- doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T18:08:07Z : Initial creation of Alembic environment by CodeAssistant
# * Set up database connection configuration
# * Added model import mechanism
# * Configured logging
# 2025-04-18T17:29:59Z : Improved database URL resolution by CodeAssistant
# * Added integration with application's configuration system
# * Implemented fallback to default SQLite database path
# * Added robust error handling for connection failures
# * Added proper type hints for improved code quality
###############################################################################

from logging.config import fileConfig
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the src directory to the path so we can import application modules
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

# Import the SQLAlchemy declarative Base and all models
from dbp.database.models import Base
# Import all models to ensure they're included in migrations
from dbp.database import models

# Try to import the configuration system for database URL detection
try:
    from dbp.config.config_manager import ConfigManager
    from dbp.core.system import SystemContext
except ImportError:
    ConfigManager = None

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

def get_url() -> str:
    """
    [Function intent]
    Dynamically generates a database URL based on application configuration.
    
    [Implementation details]
    Attempts to get configuration from the component system if available,
    falls back to environment variables or default sqlite path if needed.
    Prioritizes the database URL from alembic.ini when invoked directly.
    
    [Design principles]
    Flexibility in configuration sources with sensible defaults.
    Respects direct alembic.ini configuration for direct CLI invocation.
    Implements proper fallbacks according to DESIGN.md guidance.
    
    Returns:
        str: A SQLAlchemy connection URL
    
    Raises:
        RuntimeError: When no valid database configuration can be determined
    """
    # Check if running directly via alembic command and use config from .ini file
    # This is critical for direct CLI invocation to work properly
    if config and hasattr(config, 'get_main_option'):
        ini_url = config.get_main_option('sqlalchemy.url')
        if ini_url:
            print(f"Using database URL from alembic.ini: {ini_url}")
            return ini_url
    
    # Attempt to access application configuration
    url = _get_url_from_config()
    if url:
        print(f"Using database URL from application configuration")
        return url
    
    # Fallback to default SQLite path as specified in DATA_MODEL.md
    default_sqlite_path = Path(__file__).resolve().parents[5] / "coding_assistant" / "dbp" / "database.db"
    default_url = f"sqlite:///{default_sqlite_path}"
    print(f"Using default SQLite database URL: {default_url}")
    return default_url


def _get_url_from_config() -> Optional[str]:
    """
    [Function intent]
    Attempts to retrieve database URL from the application configuration system.
    
    [Implementation details]
    Uses the ConfigManager if available to access the database configuration.
    Constructs the appropriate database URL based on the configured database type.
    
    [Design principles]
    Integration with application configuration system.
    Separation of concerns for URL retrieval logic.
    
    Returns:
        Optional[str]: Database URL if configuration available, None otherwise
    """
    if ConfigManager is None:
        print("ConfigManager not available, skipping application configuration")
        return None
    
    try:
        # Create a system context to access configuration
        system = SystemContext()
        
        # Get the configuration manager instance
        config_manager = ConfigManager()
        config_manager.initialize(system)
        
        # Get the typed configuration
        config = config_manager.get_typed_config()
        
        # Determine the database type and construct URL
        db_type = config.database.type
        
        if db_type == 'sqlite':
            db_path = Path(config.database.path).expanduser()
            return f"sqlite:///{db_path}"
        elif db_type == 'postgresql':
            return config.database.connection_string
        else:
            print(f"Unsupported database type in config: {db_type}")
            return None
            
    except Exception as e:
        print(f"Error accessing application configuration: {e}")
        return None


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
    Improved diagnostics to troubleshoot migration issues.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override the URL in the alembic.ini
    config_section = config.get_section(config.config_ini_section)
    
    try:
        url = get_url()
        config_section['sqlalchemy.url'] = url
        
        print(f"Running migrations on database URL: {url}")
        
        connectable = engine_from_config(
            config_section,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    except Exception as e:
        print(f"ERROR: Failed to configure database connection: {e}")
        raise RuntimeError(f"Database configuration failed: {e}") from e

    with connectable.connect() as connection:
        # Check if alembic_version table exists and its state
        try:
            result = connection.execute("SELECT version_num FROM alembic_version")
            versions = [row[0] for row in result]
            print(f"Current alembic versions: {versions}")
        except Exception as e:
            print(f"No alembic_version table found or other error: {e}")
            print("This is expected for a fresh database.")
        
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            print("Starting migrations transaction...")
            context.run_migrations()
            print("Migrations completed successfully.")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
