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
# Defines the BaseRepository class that provides common functionality for all
# repository implementations in the DBP system.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides common error handling and logging for all repositories.
# - Encapsulates database manager access.
# - Centralizes common repository functionality.
###############################################################################
# [Source file constraints]
# - Depends on the DatabaseManager from database.py.
# - Must handle SQLAlchemy errors consistently.
# - Should not contain entity-specific logic.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:00:02Z : Created base_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted BaseRepository class from original repositories.py
###############################################################################

"""
Base repository class that provides common functionality for all repository implementations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Import required dependencies
try:
    from ..database import DatabaseManager
except ImportError:
    # Fallback for potential execution context issues
    from database import DatabaseManager


logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common helper methods."""

    def __init__(self, db_manager: DatabaseManager):
        """
        [Function intent]
        Initializes the BaseRepository with a database manager.
        
        [Implementation details]
        Validates the db_manager parameter and stores it for later use.
        
        [Design principles]
        Ensures proper dependency injection of the database manager.
        
        Args:
            db_manager: An instance of DatabaseManager.
            
        Raises:
            TypeError: If db_manager is not an instance of DatabaseManager.
        """
        if not isinstance(db_manager, DatabaseManager):
             raise TypeError("db_manager must be an instance of DatabaseManager")
        self.db_manager = db_manager
        logger.debug(f"{self.__class__.__name__} initialized.")

    def _log_error(self, operation: str, error: Exception):
        """
        [Function intent]
        Logs repository errors consistently.
        
        [Implementation details]
        Uses the logger to record error details with proper context.
        
        [Design principles]
        Ensures consistent error logging across all repository implementations.
        
        Args:
            operation: The name of the operation that encountered the error.
            error: The exception that occurred.
        """
        logger.error(f"{self.__class__.__name__} error during '{operation}': {error}", exc_info=True)

    def _handle_sqla_error(self, operation: str, error: SQLAlchemyError):
        """
        [Function intent]
        Handles SQLAlchemy errors consistently, logs them, and re-raises.
        
        [Implementation details]
        Logs the error with operation context and provides special handling for integrity errors.
        
        [Design principles]
        Uses "throw on error" approach as required by design principles.
        
        Args:
            operation: The name of the operation that encountered the error.
            error: The SQLAlchemy error that occurred.
            
        Raises:
            The original SQLAlchemy error after logging.
        """
        self._log_error(operation, error)
        # Specific handling can be added here if needed, e.g., for IntegrityError
        if isinstance(error, IntegrityError):
            logger.warning(f"Integrity constraint violation during {operation}.")
        raise  # Re-raise the original error after logging
