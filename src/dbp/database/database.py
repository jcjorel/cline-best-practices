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
# 2025-04-15T09:32:15Z : Initial creation of DatabaseManager class by CodeAssistant
# * Implemented initialization, session management, schema creation, and retry logic.
###############################################################################

import os
import logging
import time
from contextlib import contextmanager
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

            # Initialize schema (create tables if they don't exist)
            self._initialize_schema()

            self.initialized = True
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
                with self.engine.connect() as conn:
                    # Use execute() directly on the connection
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;") # Recommended with WAL
                logger.info("SQLite WAL mode enabled.")
            except OperationalError as e:
                logger.warning(f"Could not enable WAL mode (might be already set or unsupported): {e}")
            except Exception as e:
                 logger.error(f"Unexpected error enabling WAL mode: {e}", exc_info=True)


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
                with self.engine.connect() as connection:
                    connection.execute("VACUUM")
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
            with self.engine.connect() as connection:
                page_count_result = connection.execute("PRAGMA page_count").scalar()
                freelist_count_result = connection.execute("PRAGMA freelist_count").scalar() # More direct than free_page_count

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
