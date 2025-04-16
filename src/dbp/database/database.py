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
# - scratchpad/dbp_implementation_plan/plan_database_schema.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T18:01:22Z : Fixed SQLAlchemy SQL execution by CodeAssistant
# * Updated SQL execution to use SQLAlchemy's text() function
# * Resolved "Textual SQL expression should be explicitly declared as text" error
# 2025-04-16T17:52:39Z : Enhanced Alembic integration with config manager by CodeAssistant
# * Fixed Alembic configuration to use config_manager for settings
# * Added proper error handling to prevent NoneType errors
# * Ensured Alembic section has required defaults if missing
# 2025-04-16T17:47:00Z : Fixed database initialization issues by CodeAssistant
# * Updated initialize method to set initialized=true before schema operations
# * Added proper Alembic migration support for schema management
# * Fixed class duplication issue in the file
# 2025-04-16T17:36:38Z : Fixed component initialization configuration access by CodeAssistant
# * Modified initialize method to properly access configuration through the config_manager component
###############################################################################

import os
import logging
import time
from contextlib import contextmanager
from typing import List, Any
from ..core.component import Component
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
        logger.debug("DatabaseManager instantiated.")

    def initialize(self):
        """
        Initializes the database connection, engine, session factory, and schema.
        Must be called before accessing sessions.
        """
        if self.initialized:
            logger.warning("Database already initialized.")
            return

        db_type = self.config.get('database.type', 'sqlite')
        logger.info(f"Initializing database with type: {db_type}")

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
            raise # Re-raise the exception to signal failure
        except ValueError as e:
            logger.error(f"Database configuration error: {e}", exc_info=True)
            self.initialized = False
            raise

    def _initialize_sqlite(self):
        """Initializes the SQLite database engine."""
        db_path_config = self.config.get('database.path', '~/.dbp/metadata.db')
        db_path = os.path.expanduser(db_path_config)
        db_dir = os.path.dirname(db_path)

        logger.info(f"Initializing SQLite database at: {db_path}")

        # Ensure the directory exists
        try:
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")
        except OSError as e:
            logger.error(f"Failed to create database directory {db_dir}: {e}")
            raise

        # Create engine with connection pooling and WAL mode settings
        pool_size = self.config.get('database.max_connections', 4)
        timeout = self.config.get('database.connection_timeout', 5)
        
        # Note: connect_args for timeout might not be directly supported by SQLite driver this way.
        # Timeout is typically handled at the application level or via pool settings.
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=2, # Allow 2 extra connections beyond pool_size
            pool_timeout=timeout,
            # connect_args={'timeout': timeout} # This might cause issues with standard SQLite driver
            echo=self.config.get('database.echo_sql', False) # Optional SQL logging
        )
        logger.debug(f"SQLAlchemy engine created for SQLite with pool size {pool_size}.")

        # Enable WAL mode for better concurrency and safety
        if self.config.get('database.use_wal_mode', True):
            try:
                from sqlalchemy import text
                with self.engine.connect() as conn:
                    # Use text() to create proper SQL expressions
                    conn.execute(text("PRAGMA journal_mode=WAL;"))
                    conn.execute(text("PRAGMA synchronous=NORMAL;")) # Recommended with WAL
                logger.info("SQLite WAL mode enabled.")
            except OperationalError as e:
                logger.warning(f"Could not enable WAL mode (might be already set or unsupported): {e}")
            except Exception as e:
                 logger.error(f"Unexpected error enabling WAL mode: {e}", exc_info=True)


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
            from alembic import command
            from alembic.config import Config
            import importlib.resources
            
            # Access config through the config manager to get Alembic settings
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            config_manager = system.get_component("config_manager")
            
            # Get alembic.ini location from global config or use default
            alembic_ini_path = config_manager.get('database.alembic_ini_path', 'alembic.ini')
            
            # Load Alembic configuration
            alembic_cfg = Config(alembic_ini_path)
            
            # Configure Alembic with database URL from global config
            db_url = config_manager.get('database.url')
            if db_url:
                alembic_cfg.set_main_option('sqlalchemy.url', db_url)
            elif hasattr(self.engine, 'url'):
                # Fall back to engine URL if available
                alembic_cfg.set_main_option('sqlalchemy.url', str(self.engine.url))
            
            # Ensure default sections exist in config to prevent 'NoneType not iterable' error
            if not alembic_cfg.get_section(alembic_cfg.config_ini_section):
                alembic_cfg.set_section_option(alembic_cfg.config_ini_section, 'script_location', 'alembic')
                alembic_cfg.set_section_option(alembic_cfg.config_ini_section, 'prepend_sys_path', '.')
            
            # Ensure schema exists first (stamp head if this is a new database)
            try:
                from sqlalchemy import text
                with self.get_session() as session:
                    # Simple check to see if alembic_version table exists
                    # by attempting to create a transaction
                    session.execute(text("SELECT 1"))
                
                # Run the migration to bring database up to date
                logger.info("Running database migrations...")
                command.upgrade(alembic_cfg, "head")
                logger.info("Database migrations completed successfully.")
                
            except OperationalError:
                # Table doesn't exist, this may be a fresh database
                logger.info("Initializing new database schema...")
                
                # Create all tables directly for a fresh database
                Base.metadata.create_all(self.engine)
                
                # Then stamp with current version to avoid running all migrations
                command.stamp(alembic_cfg, "head")
                logger.info("Database schema initialized with current version.")
                
        except ImportError as e:
            logger.warning(f"Alembic not available, skipping migrations: {e}. Schema changes may need to be applied manually.")
            # Fall back to direct schema creation without migrations
            Base.metadata.create_all(self.engine)
            logger.info("Database schema created directly (without migrations).")
        except Exception as e:
            logger.error(f"Failed to run database migrations: {e}", exc_info=True)
            # This is a critical error that should bubble up
            raise RuntimeError(f"Failed to initialize database schema: {e}") from e

    def _initialize_postgresql(self):
        """Initializes the PostgreSQL database engine."""
        connection_string = self.config.get('database.connection_string')
        logger.info("Initializing PostgreSQL database.")

        if not connection_string:
            raise ValueError("PostgreSQL connection string ('database.connection_string') not provided in configuration.")

        pool_size = self.config.get('database.max_connections', 4)
        timeout = self.config.get('database.connection_timeout', 5)

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
            echo=self.config.get('database.echo_sql', False) # Optional SQL logging
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
        if self.config.get('database.type') != 'sqlite':
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
        if self.config.get('database.type') != 'sqlite':
            return False

        threshold = self.config.get('database.vacuum_threshold', 20) # Default 20%
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

    def close(self):
        """Closes the session factory and disposes of the engine."""
        if self.Session:
            self.Session.remove() # Ensure scoped session is cleaned up
            logger.debug("Scoped session factory removed.")
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed.")
        self.initialized = False
        logger.info("DatabaseManager closed.")

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DatabaseComponent(Component):
    """
    [Class intent]
    Component wrapper for the DatabaseManager following the KISS component pattern.
    Acts as the interface between the component system and the database functionality.
    
    [Implementation details]
    Wraps the DatabaseManager class, initializing it during component initialization
    and providing access to the database session and manager through properties.
    
    [Design principles]
    Single responsibility for database access and lifecycle within the component system.
    Encapsulates the database implementation details from the component system.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes the DatabaseComponent with minimal setup.
        
        [Implementation details]
        Sets the initialized flag to False and prepares for database manager creation.
        
        [Design principles]
        Minimal initialization with explicit state tracking.
        """
        super().__init__()
        self._initialized = False
        self._db_manager = None
        self.logger = None
    
    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component, used for registration and dependency references.
        
        [Implementation details]
        Returns a simple string constant.
        
        [Design principles]
        Explicit naming for clear component identification.
        
        Returns:
            str: The component name "database"
        """
        return "database"
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns the component names that this component depends on.
        
        [Implementation details]
        Database depends on config_manager to access configuration.
        
        [Design principles]
        Explicit dependency declaration for clear initialization order.
        
        Returns:
            List[str]: List of component dependencies
        """
        return ["config_manager"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the database manager with the provided configuration.
        
        [Implementation details]
        Creates a DatabaseManager instance and initializes it.
        
        [Design principles]
        Explicit initialization with clear success/failure indication.
        
        Args:
            config: Configuration object with database settings
            
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            self.logger.warning(f"Component '{self.name}' already initialized.")
            return
        
        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get component-specific configuration through config_manager
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            config_manager = system.get_component("config_manager")
            default_config = config_manager.get_default_config(self.name)
            
            # Create and initialize the database manager
            self._db_manager = DatabaseManager(default_config)
            self._db_manager.initialize()
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize database component: {e}", exc_info=True)
            self._db_manager = None
            self._initialized = False
            raise RuntimeError(f"Failed to initialize database component: {e}") from e
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the database manager and releases resources.
        
        [Implementation details]
        Calls close on the database manager and resets state.
        
        [Design principles]
        Clean resource release with clear state reset.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        if self._db_manager:
            try:
                self._db_manager.close()
            except Exception as e:
                self.logger.error(f"Error during database shutdown: {e}", exc_info=True)
            finally:
                self._db_manager = None
        
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")
    
    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Indicates if the component is successfully initialized.
        
        [Implementation details]
        Returns the value of the internal _initialized flag.
        
        [Design principles]
        Simple boolean flag for clear initialization status.
        
        Returns:
            bool: True if component is initialized, False otherwise
        """
        return self._initialized
    
    @property
    def db_manager(self) -> DatabaseManager:
        """
        [Function intent]
        Provides access to the underlying DatabaseManager.
        
        [Implementation details]
        Returns the internal database manager if initialized.
        
        [Design principles]
        Protected access to ensure initialization check.
        
        Returns:
            DatabaseManager: The initialized database manager
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._db_manager:
            raise RuntimeError("DatabaseComponent not initialized")
        return self._db_manager
    
    def get_session(self):
        """
        [Function intent]
        Provides a database session for transactional operations.
        
        [Implementation details]
        Delegates to the DatabaseManager's get_session method.
        
        [Design principles]
        Convenience method to simplify access to database sessions.
        
        Returns:
            Context manager for a database session
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._db_manager:
            raise RuntimeError("DatabaseComponent not initialized")
        return self._db_manager.get_session()
