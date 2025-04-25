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
# Provides specialized functionality for managing database schema migrations using Alembic.
# Extracts this responsibility from the main DatabaseManager to improve maintainability.
###############################################################################
# [Source file design principles]
# - Separates Alembic migration concerns from core database connection management.
# - Implements strict error handling with proper exceptions (no silent failures).
# - Provides detailed logging during migration operations for troubleshooting.
# - Supports configurable verbosity for migration operations.
# - Design Decision: Centralized Migration Management (2025-04-18)
#   * Rationale: Separates complex migration logic from core database functionality.
#   * Alternatives considered: Keeping migration code in database.py (rejected due to complexity).
###############################################################################
# [Source file constraints]
# - Requires Alembic library to be installed.
# - Depends on SQLAlchemy for database interaction.
# - Requires configuration object providing database and migration settings.
# - Needs access to a database engine and session manager.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
# codebase:- doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-20T23:50:00Z : Removed threading-based watchdog integration by CodeAssistant
# * Removed problematic threading.Event code that caused import errors
# * Removed watchdog keep_alive calls to simplify migration process
# * Fixed server startup issue caused by missing threading module
# 2025-04-18T10:51:00Z : Created alembic_manager.py by extracting from database.py by CodeAssistant
# * Extracted _run_alembic_migrations functionality into dedicated file
# * Added proper documentation sections to all methods
# * Implemented AlembicManager class with focused responsibility
###############################################################################

import os
import logging
import traceback
from contextlib import contextmanager
from typing import Optional, Callable

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

class AlembicManager:
    """
    [Class intent]
    Manages database schema migrations using Alembic with enhanced logging and error handling.
    Provides isolation of migration concerns from core database operations.
    
    [Implementation details]
    Uses Alembic to handle database schema versioning, creation, and upgrades.
    Includes specialized error handling and diagnostics for migration failures.
    Supports configurable verbosity levels for troubleshooting migration issues.
    
    [Design principles]
    Single responsibility for schema migration operations.
    Detailed logging for database migration operations with configurable verbosity.
    Strict error handling with no fallbacks to ensure schema integrity.
    Support for both component-driven and direct CLI-driven migrations.
    """

    def __init__(self, config, engine, get_session_func):
        """
        [Function intent]
        Initializes the AlembicManager with required dependencies and configuration.
        
        [Implementation details]
        Stores references to configuration, database engine, and session factory method.
        Does not perform any actual initialization operations until explicitly requested.
        
        [Design principles]
        Dependency injection for flexible testing and integration with different database systems.
        Clear separation of initialization from operation for deterministic behavior.
        
        Args:
            config: Configuration object containing database and migration settings
            engine: SQLAlchemy engine for database connections
            get_session_func: Function that returns a session context manager
        """
        self.config = config
        self.engine = engine
        self.get_session = get_session_func
        self.logger = logger

    def run_migrations(self):
        """
        [Function intent]
        Runs Alembic migrations to create and/or update the database schema with
        configurable verbosity for detailed insight into the migration process.
        
        [Implementation details]
        Executes Alembic commands to create tables if they don't exist and
        applies all pending migrations to bring the schema up to date.
        Temporarily increases logging verbosity for Alembic and SQLAlchemy
        when configured for detailed output during migrations.
        
        [Design principles]
        Database schema should be managed through migrations rather than
        direct table creation to ensure consistency across environments.
        Migration operations should provide visibility into their steps
        when detailed debugging is needed.
        Logging configuration should be temporarily enhanced and properly
        restored after migration completes.
        
        Raises:
            RuntimeError: If migrations fail for any reason
            ImportError: If Alembic is not available
        """
        self.logger.info("Running Alembic migrations to initialize/update the database schema...")
        
        # Store original logging levels to restore later
        import logging
        alembic_logger = logging.getLogger('alembic')
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        original_alembic_level = alembic_logger.level
        original_sqlalchemy_level = sqlalchemy_logger.level
        
        # Check if verbose migrations are enabled in the configuration
        # Default to False if the attribute doesn't exist
        verbose_migrations = False
        try:
            # Try accessing through direct attribute for type-safe config
            if hasattr(self.config.database, 'verbose_migrations'):
                verbose_migrations = self.config.database.verbose_migrations
            # Fallback for dictionary-based config
            elif hasattr(self.config, 'get'):
                verbose_migrations = self.config.get('database.verbose_migrations', False)
        except Exception:
            # Ignore errors in accessing config and use default value
            pass
        
        try:
            # Set enhanced verbosity if configured
            if verbose_migrations:
                self.logger.info("Enhanced migration verbosity enabled")
                # Configure loggers for maximum verbosity
                alembic_logger.setLevel(logging.DEBUG)
                sqlalchemy_logger.setLevel(logging.DEBUG)
                
                # Ensure handlers are attached to see output
                if not alembic_logger.handlers:
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(logging.Formatter('%(levelname)-5.5s [%(name)s] %(message)s'))
                    alembic_logger.addHandler(console_handler)
                    
                if not sqlalchemy_logger.handlers:
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(logging.Formatter('%(levelname)-5.5s [%(name)s] %(message)s'))
                    sqlalchemy_logger.addHandler(console_handler)
                
                # Log that verbosity is enabled
                self.logger.info("Verbose logging enabled for migration operations")
            
            # Import alembic modules here to avoid unnecessary dependencies
            # if the feature is not used
            self.logger.debug("Importing Alembic modules...")
            try:
                from alembic import command
                from alembic.config import Config
                import importlib.resources
                self.logger.debug("Alembic modules imported successfully")
            except ImportError as e:
                self.logger.error(f"Failed to import Alembic modules: {e}")
                self.logger.error("Make sure Alembic is installed. Try: pip install alembic")
                raise RuntimeError(f"Failed to import Alembic: {e}")
            
            # Access config through the config manager to get Alembic settings
            self.logger.debug("Getting ComponentSystem instance...")
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            if not system:
                self.logger.error("Failed to get ComponentSystem instance - it may not be initialized")
                raise RuntimeError("ComponentSystem not initialized")
                
            self.logger.debug("Getting config_manager component...")
            config_manager = system.get_component("config_manager")
            if not config_manager:
                self.logger.error("Failed to get config_manager component")
                raise RuntimeError("config_manager component not found")
                
            self.logger.debug("Config manager retrieved successfully")
            
            # Get alembic.ini location from global config using typed config
            typed_config = config_manager.get_typed_config()
            alembic_ini_path = typed_config.database.alembic_ini_path
            self.logger.debug(f"Using alembic.ini path: {alembic_ini_path}")
            
            # Use module-specific Alembic migrations directory
            module_alembic_dir = os.path.join(os.path.dirname(__file__), 'alembic')
            self.logger.debug(f"Using module-specific Alembic directory: {module_alembic_dir}")
            
            # Verify that the required Alembic files exist
            if not os.path.exists(alembic_ini_path):
                raise FileNotFoundError(f"Alembic config file not found: {alembic_ini_path}")
                
            if not os.path.isdir(module_alembic_dir):
                raise FileNotFoundError(f"Module Alembic directory not found: {module_alembic_dir}")
            
            # Load Alembic configuration
            self.logger.debug(f"Loading Alembic configuration from: {alembic_ini_path}")
            alembic_cfg = Config(alembic_ini_path)
            
            # Configure Alembic with database URL from global config
            # Construct database URL based on database type and configuration from typed config
            db_url = None
            try:
                # Use typed config to access database configuration
                db_type = typed_config.database.type
                if db_type == 'sqlite':
                    db_path = typed_config.database.path
                    db_url = f"sqlite:///{db_path}"
                    self.logger.debug(f"Constructed SQLite URL: {db_url}")
                elif db_type == 'postgresql':
                    conn_string = typed_config.database.connection_string
                    if conn_string:
                        db_url = conn_string
                        self.logger.debug(f"Using PostgreSQL connection string")
                    else:
                        self.logger.warning("PostgreSQL selected but no connection_string provided")
            except Exception as e:
                self.logger.warning(f"Failed to construct database URL from config: {e}")
                
            if db_url:
                self.logger.debug(f"Using constructed database URL: {db_url}")
                alembic_cfg.set_main_option('sqlalchemy.url', db_url)
            elif hasattr(self.engine, 'url'):
                # Fall back to engine URL if available
                engine_url = str(self.engine.url)
                self.logger.debug(f"Using engine URL: {engine_url}")
                alembic_cfg.set_main_option('sqlalchemy.url', engine_url)
            else:
                self.logger.error("No database URL available for Alembic")
                raise ValueError("No database URL available for Alembic")
            
            # Configure Alembic to use our module-specific migrations directory
            self.logger.debug("Setting Alembic script_location to module-specific alembic directory")
            alembic_cfg.set_main_option('script_location', module_alembic_dir)
            
            # Ensure other required config options are set
            alembic_cfg.set_main_option('prepend_sys_path', '.')
            
            # Set verbosity-specific options if enabled
            if verbose_migrations:
                # Log available migration versions for context
                self.logger.info("Checking available migration versions...")
                try:
                    # Get current migration version
                    from alembic.script import ScriptDirectory
                    script_dir = ScriptDirectory.from_config(alembic_cfg)
                    # Use the correct method to get heads - get_heads() instead of get_current_heads()
                    current_heads = script_dir.get_heads()
                    self.logger.info(f"Available migration heads: {current_heads}")
                    
                    # Get all available revisions
                    all_revisions = list(script_dir.walk_revisions())
                    self.logger.info(f"Total available revisions: {len(all_revisions)}")
                    
                    # List the latest 5 revisions for context
                    if all_revisions:
                        self.logger.info("Latest available revisions:")
                        for rev in all_revisions[:5]:
                            self.logger.info(f"  - {rev.revision}: {rev.doc}")
                except Exception as e:
                    self.logger.warning(f"Could not list available migrations: {e}")
            
            # Log main Alembic configuration options
            self.logger.debug("Alembic configuration:")
            main_section = alembic_cfg.config_ini_section
            self.logger.debug(f"  Main section: {main_section}")
            
            # Try to safely log configuration options
            try:
                if hasattr(alembic_cfg, 'get_section') and callable(alembic_cfg.get_section):
                    section_items = alembic_cfg.get_section(main_section)
                    if section_items:
                        for key, value in section_items.items():
                            self.logger.debug(f"    {key} = {value}")
                elif hasattr(alembic_cfg, 'get_main_option') and callable(alembic_cfg.get_main_option):
                    self.logger.debug(f"    sqlalchemy.url = {alembic_cfg.get_main_option('sqlalchemy.url')}")
            except Exception as e:
                self.logger.warning(f"Could not log detailed Alembic configuration: {e}")
            
            # Ensure schema exists first (stamp head if this is a new database)
            try:
                self.logger.info("Running database migrations...")
                
                # Log sequence of operations for debugging
                if verbose_migrations:
                    self.logger.info("Migration sequence:")
                    self.logger.info("1. Testing database connection")
                    self.logger.info("2. Running upgrade to latest version")
                    self.logger.info("3. Verifying migration success")
                
                with self.get_session() as session:
                    # Simple check to see if alembic_version table exists
                    # by attempting to create a transaction
                    self.logger.debug("Testing database connection...")
                    session.execute(text("SELECT 1"))
                    self.logger.debug("Database connection successful")
                
                # Check current version before upgrade (if possible)
                if verbose_migrations:
                    try:
                        with self.get_session() as session:
                            # Try to get current version - may not exist yet
                            try:
                                version_result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                                if version_result:
                                    self.logger.info(f"Current version before migration: {version_result[0]}")
                                else:
                                    self.logger.info("No current version found - this appears to be initial schema creation")
                            except Exception:
                                self.logger.info("No alembic_version table found - this appears to be initial schema creation")
                                
                            # Get database schema information for context
                            try:
                                if hasattr(self.config.database, 'type') and self.config.database.type == 'sqlite':
                                    tables = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
                                    self.logger.info(f"Existing tables before migration: {[t[0] for t in tables]}")
                                elif hasattr(self.config.database, 'type') and self.config.database.type == 'postgresql':
                                    tables = session.execute(text(
                                        "SELECT table_name FROM information_schema.tables "
                                        "WHERE table_schema='public'"
                                    )).fetchall()
                                    self.logger.info(f"Existing tables before migration: {[t[0] for t in tables]}")
                            except Exception as e:
                                self.logger.warning(f"Could not list existing tables: {e}")
                    except Exception as e:
                        self.logger.warning(f"Could not check current migration state: {e}")
                
                # Run the migration to bring database up to date
                self.logger.info("Upgrading database schema to latest version...")
                try:
                    # Run the migration with appropriate verbosity
                    if verbose_migrations:
                        self.logger.info("Running migration with enhanced logging...")
                    
                    # Run the migration directly without watchdog interaction
                    self.logger.debug("Running database migration")
                    command.upgrade(alembic_cfg, "head")
                    self.logger.info("Database migrations completed successfully.")
                    
                    # Verify that migrations were applied correctly
                    with self.get_session() as session:
                        version_result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                        if version_result:
                            self.logger.info(f"Current alembic version after migration: {version_result[0]}")
                            
                            # In verbose mode, show additional schema info
                            if verbose_migrations:
                                try:
                                    if hasattr(self.config.database, 'type') and self.config.database.type == 'sqlite':
                                        tables = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
                                        self.logger.info(f"Tables after migration: {[t[0] for t in tables]}")
                                        
                                        # For each table, show columns
                                        for table in [t[0] for t in tables]:
                                            if table != 'sqlite_sequence':  # Skip sqlite internal tables
                                                try:
                                                    columns = session.execute(text(f"PRAGMA table_info({table})")).fetchall()
                                                    self.logger.info(f"Table '{table}' columns: {[col[1] for col in columns]}")
                                                except Exception as e:
                                                    self.logger.warning(f"Could not list columns for table {table}: {e}")
                                    elif hasattr(self.config.database, 'type') and self.config.database.type == 'postgresql':
                                        tables = session.execute(text(
                                            "SELECT table_name FROM information_schema.tables "
                                            "WHERE table_schema='public'"
                                        )).fetchall()
                                        self.logger.info(f"Tables after migration: {[t[0] for t in tables]}")
                                except Exception as e:
                                    self.logger.warning(f"Could not list tables after migration: {e}")
                        else:
                            self.logger.error("Alembic version table exists but contains no version information")
                            raise RuntimeError("Database migration incomplete: missing version information")
                    
                except Exception as e:
                    self.logger.error(f"Alembic upgrade failed: {e}")
                    self.logger.error(traceback.format_exc())
                    
                    # Try to capture alembic version information for diagnostic purposes
                    try:
                        with self.get_session() as session:
                            version_result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                            if version_result:
                                self.logger.error(f"Current alembic version before failure: {version_result[0]}")
                    except Exception:
                        self.logger.error("Could not determine current alembic version")
                    
                    # Always throw the error without any fallback
                    raise RuntimeError(f"Database migration failed: {e}") from e
                
            except OperationalError as e:
                # Table doesn't exist, but we won't create tables directly as fallback
                self.logger.error(f"Database error during migration: {e}")
                self.logger.error("Alembic encountered an operational error - cannot proceed")
                self.logger.error("Make sure the database is properly configured and accessible")
                raise RuntimeError(f"Alembic operational error: {e}") from e
                
        except ImportError as e:
            self.logger.error(f"Alembic not available: {e}")
            self.logger.error("Alembic is required for schema management - cannot proceed without it")
            raise RuntimeError(f"Failed to initialize database: Alembic not available: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to run database migrations: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.error(traceback.format_exc())
            # This is a critical error that should bubble up
            raise RuntimeError(f"Failed to initialize database schema: {e}") from e
        finally:
            # Restore original logging levels
            if verbose_migrations:
                alembic_logger.setLevel(original_alembic_level)
                sqlalchemy_logger.setLevel(original_sqlalchemy_level)
                self.logger.info("Restored original logging levels after migration")
        
        self.logger.info("Alembic migrations completed successfully.")

    def generate_migration(self, message):
        """
        [Function intent]
        Creates a new migration script for schema changes with the provided message.
        
        [Implementation details]
        Uses Alembic's autogenerate functionality to create a migration script
        by comparing the SQLAlchemy models with the current database schema.
        
        [Design principles]
        Automation of migration script creation to reduce manual effort and errors.
        Proper documentation of schema changes through descriptive migration messages.
        
        Args:
            message: Description of the schema changes for the migration file
            
        Raises:
            RuntimeError: If migration script generation fails
        """
        self.logger.info(f"Generating migration script with message: {message}")
        
        try:
            from alembic import command
            from alembic.config import Config
        except ImportError as e:
            self.logger.error(f"Failed to import Alembic: {e}")
            raise RuntimeError(f"Alembic not available. Install with: pip install alembic")
        
        try:
            # Get ComponentSystem and config_manager
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            config_manager = system.get_component("config_manager")
            
            # Get alembic.ini path and module directory using typed config
            typed_config = config_manager.get_typed_config()
            alembic_ini_path = typed_config.database.alembic_ini_path
            module_alembic_dir = os.path.join(os.path.dirname(__file__), 'alembic')
            
            # Create alembic config
            alembic_cfg = Config(alembic_ini_path)
            alembic_cfg.set_main_option('script_location', module_alembic_dir)
            
            # Set database URL using typed config
            db_url = None
            db_type = typed_config.database.type
            if db_type == 'sqlite':
                db_path = typed_config.database.path
                db_url = f"sqlite:///{db_path}"
            elif db_type == 'postgresql':
                db_url = typed_config.database.connection_string
                
            if db_url:
                alembic_cfg.set_main_option('sqlalchemy.url', db_url)
            elif hasattr(self.engine, 'url'):
                alembic_cfg.set_main_option('sqlalchemy.url', str(self.engine.url))
            
            # Generate migration script
            command.revision(alembic_cfg, message=message, autogenerate=True)
            self.logger.info("Migration script generated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration script: {e}")
            self.logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to generate migration script: {e}") from e

    def get_current_version(self):
        """
        [Function intent]
        Retrieves the current database schema version from Alembic metadata.
        
        [Implementation details]
        Queries the alembic_version table to get the current version number.
        Returns None if no version information is available (fresh database).
        
        [Design principles]
        Provides visibility into current schema state for monitoring and diagnostics.
        Safe operation that handles missing version information gracefully.
        
        Returns:
            str: Current version or None if not available
            
        Raises:
            RuntimeError: If database access fails
        """
        self.logger.debug("Retrieving current database schema version...")
        
        try:
            with self.get_session() as session:
                try:
                    version_result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                    if version_result:
                        version = version_result[0]
                        self.logger.debug(f"Current database schema version: {version}")
                        return version
                    else:
                        self.logger.debug("No version information found in database")
                        return None
                except OperationalError:
                    self.logger.debug("No alembic_version table found")
                    return None
                except Exception as e:
                    self.logger.error(f"Error retrieving schema version: {e}")
                    raise RuntimeError(f"Failed to retrieve current schema version: {e}") from e
        except Exception as e:
            self.logger.error(f"Database session error retrieving schema version: {e}")
            raise RuntimeError(f"Database access error: {e}") from e
