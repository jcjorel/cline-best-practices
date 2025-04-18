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
# Provides a DatabaseManager class responsible for initializing, managing, and
# providing access to the database (SQLite or PostgreSQL) used by the DBP system.
# It handles connection pooling, session management, schema initialization, and retries.
###############################################################################
# [Source file design principles]
# - Encapsulates database connection logic.
# - Supports configurable database backends (SQLite default, PostgreSQL).
# - Ensures thread-safe database access using scoped sessions.
# - Implements connection pooling for efficiency.
# - Handles schema creation and basic version checking.
# - Provides context manager for session handling (commit/rollback).
# - Includes retry logic for transient operational errors.
# - Design Decision: Centralized Database Manager (2025-04-13)
#   * Rationale: Consolidates database setup and access logic, simplifying component interactions with the database.
#   * Alternatives considered: Direct engine/session creation in each component (rejected for complexity and inconsistency).
# - Design Decision: Support SQLite and PostgreSQL (2025-04-13)
#   * Rationale: Offers flexibility for different deployment scenarios (simple local vs. robust server).
#   * Alternatives considered: SQLite only (rejected for scalability concerns), PostgreSQL only (rejected for lack of simple default).
###############################################################################
# [Source file constraints]
# - Requires configuration object providing database settings.
# - Depends on SQLAlchemy library.
# - Assumes `models.py` defines the `Base` and `SchemaVersion` model.
# - Schema migration beyond initial creation is handled externally (e.g., Alembic).
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T08:15:00Z : Fixed database URL configuration in Alembic setup by CodeAssistant
# * Modified _run_alembic_migrations to construct database URL from configuration
# * Fixed error: "Configuration key 'database.url' not found"
# * Implemented database type-specific URL construction for SQLite and PostgreSQL
# 2025-04-17T10:55:37Z : Fixed Alembic configuration handling by CodeAssistant
# * Updated _run_alembic_migrations method to safely handle Alembic configuration
# * Resolved AttributeError: 'Config' object has no attribute 'sections'
# * Implemented robust error handling for Alembic configuration access
# 2025-04-17T10:47:23Z : Updated DatabaseManager to use config_manager properly by CodeAssistant
# * Modified DatabaseManager to use config_manager's get method for configuration
# * Added robust error handling for configuration access
# * Fixed AttributeError: 'ConfigManagerComponent' object has no attribute 'items'
# 2025-04-17T10:05:04Z : Fixed initialization context handling by CodeAssistant
###############################################################################

import os
import logging
import time
import shutil
import sqlite3
import traceback
import sys
from pathlib import Path
from contextlib import contextmanager
from typing import List, Any, Dict, Optional
from ..core.component import Component, InitializationContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Assuming models.py is in the same directory or accessible via python path
try:
    from .models import Base, SchemaVersion
except ImportError:
    # Fallback for potential execution context issues
    from models import Base, SchemaVersion


logger = logging.getLogger(__name__)

class DatabaseComponent(Component):
    """
    [Class intent]
    Component wrapper for DatabaseManager that integrates with the component lifecycle
    system. Provides database access to other components via component registry.
    
    [Implementation details]
    Acts as an adapter between DatabaseManager and Component protocol.
    Manages database initialization and shutdown as part of the component lifecycle.
    
    [Design principles]
    Single source of database access through component system.
    Centralized database initialization and configuration.
    """

    def __init__(self):
        """
        [Function intent]
        Initializes the DatabaseComponent with a new DatabaseManager instance.
        
        [Implementation details]
        Creates a DatabaseManager but does not initialize it yet.
        Full initialization happens during component initialization.
        
        [Design principles]
        Deferred initialization to support component lifecycle management.
        """
        super().__init__()
        self._db_manager = None
        self.logger = logging.getLogger(f"dbp.{self.name}")

    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component for registration and dependency references.
        
        [Implementation details]
        Simple property returning the standard name for this component.
        
        [Design principles]
        Consistent naming convention for database component.
        
        Returns:
            str: 'database' as the component name
        """
        return "database"

    @property
    def dependencies(self) -> list[str]:
        """
        [Function intent]
        Declares dependencies required by this component.
        
        [Implementation details]
        Depends only on the config_manager component to obtain database configuration.
        
        [Design principles]
        Minimal dependencies for database functionality.
        
        Returns:
            list[str]: List of component names this component depends on
        """
        return ["config_manager"]

    def initialize(self, context: InitializationContext) -> None:
        """
        [Function intent]
        Initializes the database component with the application configuration.
        
        [Implementation details]
        Creates and initializes the DatabaseManager with typed configuration.
        Sets _initialized flag to indicate successful initialization.
        
        [Design principles]
        Clean initialization with proper error handling.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with typed configuration and resources
        
        Raises:
            RuntimeError: If database initialization fails
        """
        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get the strongly-typed configuration directly
            typed_config = context.get_typed_config()
            
            # Create database manager if it doesn't exist
            if not self._db_manager:
                self._db_manager = DatabaseManager(typed_config)
                
            # Initialize the database
            self._db_manager.initialize()
            
            # Mark component as initialized
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database component: {e}", exc_info=True)
            self.set_initialization_error(e)
            raise RuntimeError(f"Database component initialization failed: {e}") from e

    def shutdown(self) -> None:
        """
        [Function intent]
        Performs graceful shutdown of the database component.
        
        [Implementation details]
        Currently no explicit cleanup needed for DatabaseManager.
        Sets _initialized flag to False to indicate component is inactive.
        
        [Design principles]
        Clean resource release and state management.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        # Nothing to do for now, but in the future might need to close connections
        
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")
        
    def get_manager(self) -> 'DatabaseManager':
        """
        [Function intent]
        Provides access to the underlying DatabaseManager.
        
        [Implementation details]
        Returns the encapsulated DatabaseManager instance for direct database access.
        
        [Design principles]
        Controlled access to database functionality.
        
        Returns:
            DatabaseManager: The database manager instance
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized:
            self.logger.error("Attempted to access database manager before initialization")
            raise RuntimeError("Database component not initialized")
            
        return self._db_manager
        
    def get_session(self):
        """
        [Function intent]
        Provides a transactional scope for a series of database operations.
        
        [Implementation details]
        Delegates to DatabaseManager's get_session context manager.
        
        [Design principles]
        Consistent database session access through component layer.
        
        Returns:
            Context manager yielding a SQLAlchemy session
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized:
            self.logger.error("Attempted to get database session before initialization")
            raise RuntimeError("Database component not initialized")
            
        return self._db_manager.get_session()
        
    def execute_with_retry(self, operation, max_retries=3, retry_interval=1):
        """
        [Function intent]
        Delegates to DatabaseManager's execute_with_retry method.
        
        [Implementation details]
        Passes the operation along with retry parameters to the database manager.
        
        [Design principles]
        Consistent error handling and retry logic access through component layer.
        
        Args:
            operation: Callable database operation
            max_retries: Maximum retry attempts
            retry_interval: Time between retries in seconds
            
        Returns:
            Result of the operation
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized:
            self.logger.error("Attempted to execute database operation before initialization")
            raise RuntimeError("Database component not initialized")
            
        return self._db_manager.execute_with_retry(operation, max_retries, retry_interval)


class DatabaseManager:
    """Manages database connections, sessions, and schema initialization."""

    def __init__(self, config):
        """
        Initializes the DatabaseManager.

        Args:
            config (dict): Configuration dictionary containing database settings.
                           Expected keys: 'database.type', 'database.path' (for sqlite),
                           'database.connection_string' (for postgresql),
                           'database.max_connections', 'database.connection_timeout',
                           'database.use_wal_mode', 'database.vacuum_threshold'.
        """
        self.config = config
        self.engine = None
        self.Session = None
        self.initialized = False
        self.db_path = None
        logger.debug("DatabaseManager instantiated.")

    def initialize(self):
        """
        Initializes the database connection, engine, session factory, and schema.
        Must be called before accessing sessions.
        """
        if self.initialized:
            logger.warning("Database already initialized.")
            return

        # Access configuration using direct attribute access for strongly-typed config
        db_type = self.config.database.type
        logger.info(f"Initializing database with type: {db_type}")

        # Log detailed configuration for debugging
        try:
            # Access database configuration through attributes directly
            db_config = {
                'database.type': self.config.database.type,
                'database.path': self.config.database.path,
                'database.max_connections': self.config.database.max_connections,
                'database.connection_timeout': self.config.database.connection_timeout,
                'database.use_wal_mode': self.config.database.use_wal_mode,
                'database.vacuum_threshold': self.config.database.vacuum_threshold,
                'database.echo_sql': self.config.database.echo_sql
            }
            
            # Add PostgreSQL config if attribute exists
            if hasattr(self.config.database, 'connection_string'):
                db_config['database.connection_string'] = self.config.database.connection_string
                
            logger.debug(f"Database configuration: {db_config}")
        except Exception as e:
            logger.warning(f"Could not log detailed configuration: {e}")

        try:
            if db_type == 'sqlite':
                self._initialize_sqlite()
            elif db_type == 'postgresql':
                self._initialize_postgresql()
            else:
                raise ValueError(f"Unsupported database type: {db_type}")

            # Create scoped session factory for thread safety
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            logger.debug("Scoped session factory created.")

            # Mark as initialized so we can use sessions in schema initialization
            self.initialized = True

            # Initialize schema using Alembic
            self._run_alembic_migrations()

            logger.info("Database initialized successfully.")

        except SQLAlchemyError as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            self.initialized = False # Ensure state reflects failure
            
            # Log more details about the SQLAlchemy error
            self._log_detailed_sqlalchemy_error(e)
            
            # Gather and log system information that might help diagnose issues
            self._log_system_info()
            
            raise # Re-raise the exception to signal failure
        except ValueError as e:
            logger.error(f"Database configuration error: {e}", exc_info=True)
            self.initialized = False
            raise
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(traceback.format_exc())
            self.initialized = False
            raise

    def _log_detailed_sqlalchemy_error(self, error: SQLAlchemyError):
        """
        [Function intent]
        Logs detailed information about SQLAlchemy errors.
        
        [Implementation details]
        Extracts specific error details from different types of SQLAlchemy exceptions.
        
        [Design principles]
        Provides actionable error information for database failures.
        """
        logger.error(f"SQLAlchemy error details:")
        
        # Get error class and module
        error_class = error.__class__.__name__
        error_module = error.__class__.__module__
        logger.error(f"  Error class: {error_module}.{error_class}")
        
        # Extract connection information if available
        if hasattr(error, 'connection'):
            conn = error.connection
            logger.error(f"  Connection info: {conn}")
            
        # Log statement that caused the error if available
        if hasattr(error, 'statement'):
            logger.error(f"  Failed statement: {error.statement}")
        
        # For operational errors, log more details
        if isinstance(error, OperationalError):
            if hasattr(error, 'orig') and error.orig:
                logger.error(f"  Original error: {error.orig}")
                
                # For SQLite errors, provide more specific info
                if isinstance(error.orig, sqlite3.OperationalError):
                    sqlite_err = str(error.orig)
                    logger.error(f"  SQLite error: {sqlite_err}")
                    
                    # Check for common SQLite errors
                    if "unable to open database file" in sqlite_err:
                        logger.error("  This indicates filesystem permission issues or missing directories.")
                    elif "database is locked" in sqlite_err:
                        logger.error("  This indicates another process has locked the database.")
                    elif "disk I/O error" in sqlite_err:
                        logger.error("  This indicates filesystem/disk errors accessing the database file.")

    def _log_system_info(self):
        """
        [Function intent]
        Logs system information relevant to database operation.
        
        [Implementation details]
        Collects and logs information about filesystem, SQLAlchemy version, 
        and database configuration that might help diagnose issues.
        
        [Design principles]
        Provides context for error diagnosis without exposing sensitive information.
        """
        logger.error("System information for database diagnosis:")
        
        # Log SQLAlchemy version
        import sqlalchemy
        logger.error(f"  SQLAlchemy version: {sqlalchemy.__version__}")
        
        # Log database type and path
        db_type = self.config.database.type
        logger.error(f"  Database type: {db_type}")
        
        if db_type == 'sqlite' and self.db_path:
            db_path = self.db_path
            
            # Log path information
            logger.error(f"  Database path: {db_path}")
            
            # Check if directory exists
            db_dir = os.path.dirname(db_path)
            dir_exists = os.path.exists(db_dir)
            logger.error(f"  Database directory exists: {dir_exists}")
            
            if dir_exists:
                # Check permissions
                try:
                    readable = os.access(db_dir, os.R_OK)
                    writable = os.access(db_dir, os.W_OK)
                    executable = os.access(db_dir, os.X_OK)
                    logger.error(f"  Directory permissions: read={readable}, write={writable}, execute={executable}")
                    
                    # Check free space
                    try:
                        free_space = shutil.disk_usage(db_dir).free / (1024 * 1024)  # MB
                        logger.error(f"  Free disk space: {free_space:.2f} MB")
                    except Exception as e:
                        logger.error(f"  Could not determine free space: {e}")
                        
                    # Check if database file exists
                    file_exists = os.path.exists(db_path)
                    logger.error(f"  Database file exists: {file_exists}")
                    
                    if file_exists:
                        # Log file size and permissions
                        size = os.path.getsize(db_path) / 1024  # KB
                        logger.error(f"  Database file size: {size:.2f} KB")
                        
                        file_readable = os.access(db_path, os.R_OK)
                        file_writable = os.access(db_path, os.W_OK)
                        logger.error(f"  File permissions: read={file_readable}, write={file_writable}")
                        
                        # Check if file is a valid SQLite database
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("PRAGMA integrity_check")
                            result = cursor.fetchone()[0]
                            conn.close()
                            logger.error(f"  Database integrity: {result}")
                        except Exception as e:
                            logger.error(f"  Database integrity check failed: {e}")
                except Exception as e:
                    logger.error(f"  Error checking directory/file access: {e}")
        
        # Log process information
        import os
        logger.error(f"  Process ID: {os.getpid()}")
        logger.error(f"  Process username: {os.getlogin()}")
        logger.error(f"  Current working directory: {os.getcwd()}")

    def _initialize_sqlite(self):
        """Initializes the SQLite database engine."""
        db_path_config = self.config.database.path
        db_path = os.path.expanduser(db_path_config)
        db_dir = os.path.dirname(db_path)
        
        # Save for potential error logging
        self.db_path = db_path

        logger.info(f"Initializing SQLite database at: {db_path}")

        # Ensure the directory exists
        try:
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")
                
            # Verify the directory is writable after creation
            if not os.access(db_dir, os.W_OK):
                logger.error(f"Database directory {db_dir} is not writable!")
                raise PermissionError(f"Database directory {db_dir} is not writable!")
                
        except OSError as e:
            logger.error(f"Failed to create database directory {db_dir}: {e}")
            logger.error(f"Directory creation error type: {type(e).__name__}")
            logger.error(traceback.format_exc())
            
            # Check parent directory permissions
            parent_dir = os.path.dirname(db_dir)
            if os.path.exists(parent_dir):
                parent_writable = os.access(parent_dir, os.W_OK)
                logger.error(f"Parent directory {parent_dir} writable: {parent_writable}")
            
            raise

        # Create engine with connection pooling and WAL mode settings
        pool_size = self.config.database.max_connections
        timeout = self.config.database.connection_timeout
        
        # Log configuration values
        logger.info(f"SQLite configuration: pool_size={pool_size}, timeout={timeout}")
        logger.info(f"SQLite path: absolute={os.path.abspath(db_path)}, normalized={os.path.normpath(db_path)}")
        
        # Note: connect_args for timeout might not be directly supported by SQLite driver this way.
        # Timeout is typically handled at the application level or via pool settings.
        try:
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=2, # Allow 2 extra connections beyond pool_size
                pool_timeout=timeout,
                # connect_args={'timeout': timeout} # This might cause issues with standard SQLite driver
                echo=self.config.database.echo_sql # Optional SQL logging
            )
            logger.debug(f"SQLAlchemy engine created for SQLite with pool size {pool_size}.")
        except Exception as e:
            logger.error(f"Failed to create SQLAlchemy engine: {e}")
            logger.error(f"Engine creation error type: {type(e).__name__}")
            logger.error(traceback.format_exc())
            raise

        # Enable WAL mode for better concurrency and safety
        if self.config.database.use_wal_mode:
            try:
                from sqlalchemy import text
                with self.engine.connect() as conn:
                    # Use text() to create proper SQL expressions
                    logger.info("Enabling SQLite WAL mode...")
                    conn.execute(text("PRAGMA journal_mode=WAL;"))
                    conn.execute(text("PRAGMA synchronous=NORMAL;")) # Recommended with WAL
                
                # Verify WAL mode was set
                with self.engine.connect() as conn:
                    result = conn.execute(text("PRAGMA journal_mode;")).scalar()
                    logger.info(f"SQLite WAL mode enabled. Current journal mode: {result}")
            except OperationalError as e:
                logger.warning(f"Could not enable WAL mode (might be already set or unsupported): {e}")
                logger.warning(traceback.format_exc())
            except Exception as e:
                logger.error(f"Unexpected error enabling WAL mode: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(traceback.format_exc())


    def _run_alembic_migrations(self):
        """
        Runs Alembic migrations to create and/or update the database schema.

        [Function intent]
        Uses Alembic to handle database schema creation and migrations.
        
        [Implementation details]
        Executes Alembic commands to create tables if they don't exist and
        apply all pending migrations to bring the schema up to date.
        
        [Design principles]
        Database schema should be managed through migrations rather than
        direct table creation to ensure consistency across environments.
        """
        logger.info("Running Alembic migrations to initialize/update the database schema...")
        try:
            # Import alembic modules here to avoid unnecessary dependencies
            # if the feature is not used
            logger.debug("Importing Alembic modules...")
            try:
                from alembic import command
                from alembic.config import Config
                import importlib.resources
                logger.debug("Alembic modules imported successfully")
            except ImportError as e:
                logger.error(f"Failed to import Alembic modules: {e}")
                logger.error("Make sure Alembic is installed. Try: pip install alembic")
                raise RuntimeError(f"Failed to import Alembic: {e}")
            
            # Access config through the config manager to get Alembic settings
            logger.debug("Getting ComponentSystem instance...")
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            if not system:
                logger.error("Failed to get ComponentSystem instance - it may not be initialized")
                raise RuntimeError("ComponentSystem not initialized")
                
            logger.debug("Getting config_manager component...")
            config_manager = system.get_component("config_manager")
            if not config_manager:
                logger.error("Failed to get config_manager component")
                raise RuntimeError("config_manager component not found")
                
            logger.debug("Config manager retrieved successfully")
            
            # Get alembic.ini location from global config
            alembic_ini_path = config_manager.get('database.alembic_ini_path')
            logger.debug(f"Using alembic.ini path: {alembic_ini_path}")
            
            # Use module-specific Alembic migrations directory
            module_alembic_dir = os.path.join(os.path.dirname(__file__), 'alembic')
            logger.debug(f"Using module-specific Alembic directory: {module_alembic_dir}")
            
            # Verify that the required Alembic files exist
            if not os.path.exists(alembic_ini_path):
                raise FileNotFoundError(f"Alembic config file not found: {alembic_ini_path}")
                
            if not os.path.isdir(module_alembic_dir):
                raise FileNotFoundError(f"Module Alembic directory not found: {module_alembic_dir}")
            
            # Load Alembic configuration
            logger.debug(f"Loading Alembic configuration from: {alembic_ini_path}")
            alembic_cfg = Config(alembic_ini_path)
            
            # Configure Alembic with database URL from global config
            # Construct database URL based on database type and configuration
            db_url = None
            try:
                db_type = config_manager.get('database.type')
                if db_type == 'sqlite':
                    db_path = config_manager.get('database.path')
                    db_url = f"sqlite:///{db_path}"
                    logger.debug(f"Constructed SQLite URL: {db_url}")
                elif db_type == 'postgresql':
                    conn_string = config_manager.get('database.connection_string')
                    if conn_string:
                        db_url = conn_string
                        logger.debug(f"Using PostgreSQL connection string")
                    else:
                        logger.warning("PostgreSQL selected but no connection_string provided")
            except Exception as e:
                logger.warning(f"Failed to construct database URL from config: {e}")
                
            if db_url:
                logger.debug(f"Using constructed database URL: {db_url}")
                alembic_cfg.set_main_option('sqlalchemy.url', db_url)
            elif hasattr(self.engine, 'url'):
                # Fall back to engine URL if available
                engine_url = str(self.engine.url)
                logger.debug(f"Using engine URL: {engine_url}")
                alembic_cfg.set_main_option('sqlalchemy.url', engine_url)
            else:
                logger.error("No database URL available for Alembic")
                raise ValueError("No database URL available for Alembic")
            
            # Configure Alembic to use our module-specific migrations directory
            logger.debug("Setting Alembic script_location to module-specific alembic directory")
            alembic_cfg.set_main_option('script_location', module_alembic_dir)
            
            # Ensure other required config options are set
            alembic_cfg.set_main_option('prepend_sys_path', '.')
            
            # Log main Alembic configuration options for debugging
            logger.debug("Alembic configuration:")
            main_section = alembic_cfg.config_ini_section
            logger.debug(f"  Main section: {main_section}")
            
            # Try to safely log configuration options
            try:
                if hasattr(alembic_cfg, 'get_section') and callable(alembic_cfg.get_section):
                    section_items = alembic_cfg.get_section(main_section)
                    if section_items:
                        for key, value in section_items.items():
                            logger.debug(f"    {key} = {value}")
                elif hasattr(alembic_cfg, 'get_main_option') and callable(alembic_cfg.get_main_option):
                    logger.debug(f"    sqlalchemy.url = {alembic_cfg.get_main_option('sqlalchemy.url')}")
            except Exception as e:
                logger.warning(f"Could not log detailed Alembic configuration: {e}")
            
            # Ensure schema exists first (stamp head if this is a new database)
            try:
                from sqlalchemy import text
                logger.info("Running database migrations...")
                
                with self.get_session() as session:
                    # Simple check to see if alembic_version table exists
                    # by attempting to create a transaction
                    logger.debug("Testing database connection...")
                    session.execute(text("SELECT 1"))
                    logger.debug("Database connection successful")
                
                # Run the migration to bring database up to date
                logger.info("Upgrading database schema to latest version...")
                try:
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Database migrations completed successfully.")
                except Exception as e:
                    logger.error(f"Alembic upgrade failed: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Try to capture alembic version information
                    try:
                        with self.get_session() as session:
                            version_result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                            if version_result:
                                logger.error(f"Current alembic version before failure: {version_result[0]}")
                    except Exception:
                        logger.error("Could not determine current alembic version")
                    
                    raise
                
            except OperationalError as e:
                # Table doesn't exist, this may be a fresh database
                logger.info(f"Database appears to be new or empty: {e}")
                logger.info("Initializing new database schema...")
                
                # Create all tables directly for a fresh database
                try:
                    logger.debug("Creating database tables directly...")
                    Base.metadata.create_all(self.engine)
                    logger.debug("Tables created successfully")
                    
                    # Then stamp with current version to avoid running all migrations
                    logger.debug("Stamping database with current version...")
                    command.stamp(alembic_cfg, "head")
                    logger.info("Database schema initialized with current version.")
                except Exception as table_error:
                    logger.error(f"Failed to create database tables: {table_error}")
                    logger.error(traceback.format_exc())
                    raise
                
        except ImportError as e:
            logger.warning(f"Alembic not available, skipping migrations: {e}. Schema changes may need to be applied manually.")
            # Fall back to direct schema creation without migrations
            try:
                logger.info("Creating tables directly (without migrations)...")
                Base.metadata.create_all(self.engine)
                logger.info("Database schema created directly (without migrations).")
            except Exception as direct_error:
                logger.error(f"Failed to create schema directly: {direct_error}")
                logger.error(traceback.format_exc())
                raise
        except Exception as e:
            logger.error(f"Failed to run database migrations: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(traceback.format_exc())
            # This is a critical error that should bubble up
            raise RuntimeError(f"Failed to initialize database schema: {e}") from e

    def _initialize_postgresql(self):
        """Initializes the PostgreSQL database engine."""
        connection_string = self.config.database.connection_string
        logger.info("Initializing PostgreSQL database.")

        if not connection_string:
            raise ValueError("PostgreSQL connection string ('database.connection_string') not provided in configuration.")

        pool_size = self.config.database.max_connections
        timeout = self.config.database.connection_timeout

        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=2,
            pool_timeout=timeout,
            pool_pre_ping=True, # Check connection validity before use
            connect_args={
                'connect_timeout': timeout # PostgreSQL specific connection timeout
            },
            echo=self.config.database.echo_sql # Optional SQL logging
        )
        logger.debug(f"SQLAlchemy engine created for PostgreSQL with pool size {pool_size}.")

    def _initialize_schema(self):
        """Creates database tables defined in models.py if they don't exist."""
        logger.info("Initializing database schema...")
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database schema checked/created.")

            # Insert initial schema version if the table is empty
            with self.get_session() as session:
                if session.query(SchemaVersion).count() == 0:
                    initial_version = SchemaVersion(version="1.0.0") # TODO: Make version dynamic?
                    session.add(initial_version)
                    session.commit() # Commit specifically for version insertion
                    logger.info(f"Initialized schema version to {initial_version.version}.")
                else:
                    current_version = session.query(SchemaVersion).order_by(SchemaVersion.applied_at.desc()).first()
                    logger.info(f"Existing schema version found: {current_version.version}")
                    # TODO: Add migration logic here if needed in the future using Alembic

        except OperationalError as e:
             logger.error(f"Database operational error during schema initialization: {e}. Check connection and permissions.", exc_info=True)
             raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
            raise

    @contextmanager
    def get_session(self):
        """Provides a transactional scope around a series of operations."""
        if not self.initialized:
            logger.error("DatabaseManager not initialized. Call initialize() first.")
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self.Session()
        logger.debug(f"Session {id(session)} acquired from scoped session factory.")
        try:
            yield session
            session.commit()
            logger.debug(f"Session {id(session)} committed.")
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error in session {id(session)}, rolling back: {e}", exc_info=True)
            session.rollback()
            raise # Re-raise the original exception
        except Exception as e:
            logger.error(f"Unexpected error in session {id(session)}, rolling back: {e}", exc_info=True)
            session.rollback()
            raise # Re-raise the original exception
        finally:
            logger.debug(f"Session {id(session)} closed.")
            self.Session.remove() # Return session to the pool/registry

    def execute_with_retry(self, operation, max_retries=3, retry_interval=1):
        """
        Executes a database operation with retry logic for OperationalErrors.

        Args:
            operation (callable): The function to execute, typically involving a session.
            max_retries (int): Maximum number of retries.
            retry_interval (int): Base interval between retries in seconds.

        Returns:
            The result of the operation.

        Raises:
            OperationalError: If the operation fails after all retries.
            Exception: If the operation raises an exception other than OperationalError.
        """
        retries = 0
        while retries <= max_retries:
            try:
                return operation()
            except OperationalError as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Database operation failed after {max_retries} retries: {e}", exc_info=True)
                    raise
                wait_time = retry_interval * (2 ** (retries - 1)) # Exponential backoff
                logger.warning(f"Database operational error, retrying ({retries}/{max_retries}) in {wait_time}s: {e}")
                time.sleep(wait_time)
            except Exception as e:
                 logger.error(f"Non-retryable error during operation: {e}", exc_info=True)
                 raise # Re-raise non-operational errors immediately

    def vacuum(self):
        """Performs VACUUM operation on SQLite database if needed."""
        if self.config.database.type != 'sqlite':
            logger.debug("Vacuum operation skipped (not SQLite).")
            return

        if self.check_vacuum_needed():
            logger.info("Vacuum threshold reached, performing VACUUM...")
            try:
                # VACUUM cannot run inside a transaction, needs raw connection execution
                from sqlalchemy import text
                with self.engine.connect() as connection:
                    connection.execute(text("VACUUM"))
                logger.info("Database VACUUM completed successfully.")
            except OperationalError as e:
                 # May fail if other connections are active
                 logger.warning(f"Could not perform VACUUM, possibly due to active connections: {e}")
            except SQLAlchemyError as e:
                logger.error(f"Failed to VACUUM database: {e}", exc_info=True)
        else:
            logger.debug("Vacuum not needed based on threshold.")


    def check_vacuum_needed(self):
        """Checks if SQLite database fragmentation exceeds the configured threshold."""
        if self.config.database.type != 'sqlite':
            return False

        threshold = self.config.database.vacuum_threshold # Using attribute access
        if not (0 < threshold <= 100):
             logger.warning(f"Invalid vacuum threshold {threshold}, using default 20.")
             threshold = 20

        try:
            from sqlalchemy import text
            with self.engine.connect() as connection:
                page_count_result = connection.execute(text("PRAGMA page_count")).scalar()
                freelist_count_result = connection.execute(text("PRAGMA freelist_count")).scalar() # More direct than free_page_count

                page_count = int(page_count_result) if page_count_result else 0
                freelist_count = int(freelist_count_result) if freelist_count_result else 0

                if page_count > 0:
                    free_percent = (freelist_count / page_count) * 100
                    logger.debug(f"Database fragmentation: {free_percent:.2f}% (Threshold: {threshold}%)")
                    return free_percent >= threshold
                else:
                    logger.debug("Database is empty, vacuum not applicable.")
                    return False

        except SQLAlchemyError as e:
            logger.error(f"Failed to check database fragmentation: {e}", exc_info=True)
            return False # Avoid vacuuming on error
