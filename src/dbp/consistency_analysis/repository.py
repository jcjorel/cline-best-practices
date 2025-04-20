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
# Implements the InconsistencyRepository class, responsible for interacting with
# the database to persist and retrieve inconsistency records detected by the
# Consistency Analysis component. It uses the DatabaseManager and InconsistencyORM model.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern for data access abstraction.
# - Provides methods for saving, updating, retrieving (by ID, with filters), and deleting inconsistency records.
# - Handles conversion between the InconsistencyRecord dataclass and the InconsistencyORM model.
# - Uses the injected DatabaseManager for database sessions.
# - Includes error handling and logging for database operations.
###############################################################################
# [Source file constraints]
# - Depends on `DatabaseManager` and the `InconsistencyORM` model.
# - Assumes the database schema includes the `inconsistencies` table.
# - Relies on `json` library for serializing/deserializing details/metadata fields.
# - Enum values are stored as strings in the database.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - src/dbp/database/database.py
# - src/dbp/database/models.py
# - src/dbp/consistency_analysis/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:28:45Z : Initial creation of InconsistencyRepository class by CodeAssistant
# * Implemented CRUD operations and ORM/dataclass conversion logic for inconsistencies.
###############################################################################

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import or_ # Required for OR condition in filtering

# Assuming necessary imports
try:
    from ..database.database import DatabaseManager
    from ..database.models import InconsistencyORM
    from .data_models import InconsistencyRecord, InconsistencyType, InconsistencySeverity, InconsistencyStatus
    # Import Component for type hint if db_manager is passed via component
    from ..core.component import Component
except ImportError as e:
    logging.getLogger(__name__).error(f"InconsistencyRepository ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    DatabaseManager = object
    InconsistencyORM = object
    InconsistencyRecord = object
    InconsistencyType = object
    InconsistencySeverity = object
    InconsistencyStatus = object
    Component = object
    # Dummy Enum for placeholder
    class Enum:
        def __init__(self, value): self.value = value


logger = logging.getLogger(__name__)

class RepositoryError(Exception):
    """Custom exception for repository-level errors."""
    pass

class InconsistencyRepository:
    """
    Repository class for managing the persistence of InconsistencyRecord objects
    in the database.
    """

    def __init__(self, db_manager: DatabaseManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the InconsistencyRepository.

        Args:
            db_manager: An initialized DatabaseManager instance.
            logger_override: Optional logger instance.
        """
        if not isinstance(db_manager, DatabaseManager):
             logger.warning("InconsistencyRepository initialized with potentially incorrect db_manager type.")
        self.db_manager = db_manager
        self.logger = logger_override or logger
        self.logger.debug("InconsistencyRepository initialized.")

    def save(self, inconsistency: InconsistencyRecord) -> str:
        """
        Saves a new inconsistency record to the database.

        Args:
            inconsistency: The InconsistencyRecord dataclass instance to save.

        Returns:
            The unique ID (as string) assigned to the saved record.

        Raises:
            RepositoryError: If saving fails.
        """
        self.logger.debug(f"Saving inconsistency: Type='{inconsistency.inconsistency_type.value}', Source='{inconsistency.source_file}'")
        try:
            with self.db_manager.get_session() as session:
                # Convert dataclass to ORM model
                inconsistency_orm = InconsistencyORM(
                    source_file=inconsistency.source_file,
                    target_file=inconsistency.target_file,
                    inconsistency_type=inconsistency.inconsistency_type.value,
                    description=inconsistency.description,
                    details=json.dumps(inconsistency.details) if inconsistency.details else None,
                    severity=inconsistency.severity.value,
                    status=inconsistency.status.value,
                    confidence_score=inconsistency.confidence_score,
                    detected_at=inconsistency.detected_at or datetime.now(timezone.utc),
                    resolved_at=inconsistency.resolved_at,
                    metadata=json.dumps(inconsistency.metadata) if inconsistency.metadata else None
                )
                session.add(inconsistency_orm)
                session.flush() # Flush to get the generated ID
                inconsistency_id = str(inconsistency_orm.id)
                # Update the dataclass with the generated ID if it was None
                if inconsistency.id is None:
                     inconsistency.id = inconsistency_id
                self.logger.info(f"Saved inconsistency with ID: {inconsistency_id}")
                return inconsistency_id
        except Exception as e:
            self.logger.error(f"Error saving inconsistency (Type='{inconsistency.inconsistency_type.value}', Source='{inconsistency.source_file}'): {e}", exc_info=True)
            raise RepositoryError(f"Error saving inconsistency: {e}") from e

    def update(self, inconsistency: InconsistencyRecord):
        """
        Updates an existing inconsistency record in the database.
        The inconsistency object must have a valid `id`.

        Args:
            inconsistency: The InconsistencyRecord dataclass instance with updated data.

        Raises:
            RepositoryError: If the inconsistency ID is missing or the update fails.
            ValueError: If the inconsistency ID is not found.
        """
        if not inconsistency.id:
            raise RepositoryError("Cannot update inconsistency without a valid ID.")

        self.logger.debug(f"Updating inconsistency ID: {inconsistency.id}")
        try:
            with self.db_manager.get_session() as session:
                inconsistency_orm = session.query(InconsistencyORM).get(int(inconsistency.id))
                if not inconsistency_orm:
                    raise ValueError(f"Inconsistency with ID {inconsistency.id} not found for update.")

                # Update fields from the dataclass
                inconsistency_orm.source_file = inconsistency.source_file
                inconsistency_orm.target_file = inconsistency.target_file
                inconsistency_orm.inconsistency_type = inconsistency.inconsistency_type.value
                inconsistency_orm.description = inconsistency.description
                inconsistency_orm.details = json.dumps(inconsistency.details) if inconsistency.details else None
                inconsistency_orm.severity = inconsistency.severity.value
                inconsistency_orm.status = inconsistency.status.value
                inconsistency_orm.confidence_score = inconsistency.confidence_score
                inconsistency_orm.detected_at = inconsistency.detected_at
                inconsistency_orm.resolved_at = inconsistency.resolved_at
                inconsistency_orm.metadata = json.dumps(inconsistency.metadata) if inconsistency.metadata else None
                # updated_at is handled by the ORM model's onupdate

                session.flush()
                self.logger.info(f"Updated inconsistency ID: {inconsistency.id}")
        except ValueError as e:
             self.logger.error(f"Value error updating inconsistency {inconsistency.id}: {e}")
             raise e
        except Exception as e:
            self.logger.error(f"Error updating inconsistency {inconsistency.id}: {e}", exc_info=True)
            raise RepositoryError(f"Error updating inconsistency {inconsistency.id}: {e}") from e

    def get(self, inconsistency_id: str) -> Optional[InconsistencyRecord]:
        """
        Retrieves a single inconsistency record by its ID.

        Args:
            inconsistency_id: The unique ID of the inconsistency.

        Returns:
            An InconsistencyRecord object if found, otherwise None.

        Raises:
            RepositoryError: If retrieval fails.
        """
        self.logger.debug(f"Getting inconsistency ID: {inconsistency_id}")
        try:
            with self.db_manager.get_session() as session:
                inconsistency_orm = session.query(InconsistencyORM).get(int(inconsistency_id))
                if inconsistency_orm:
                    return self._convert_orm_to_inconsistency(inconsistency_orm)
                else:
                    self.logger.debug(f"Inconsistency ID {inconsistency_id} not found.")
                    return None
        except ValueError:
             self.logger.error(f"Invalid inconsistency ID format for get: {inconsistency_id}")
             return None
        except Exception as e:
            self.logger.error(f"Error getting inconsistency {inconsistency_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error getting inconsistency {inconsistency_id}: {e}") from e

    def get_inconsistencies(
        self,
        file_path: Optional[str] = None,
        severity: Optional[InconsistencySeverity] = None,
        status: Optional[InconsistencyStatus] = None,
        limit: int = 100
    ) -> List[InconsistencyRecord]:
        """
        Retrieves a list of inconsistency records, optionally filtered by file path,
        severity, and status.

        Args:
            file_path: If provided, returns inconsistencies where this path is either
                       the source_file or target_file.
            severity: If provided, filters by severity level (enum member).
            status: If provided, filters by status (enum member).
            limit: The maximum number of records to return.

        Returns:
            A list of matching InconsistencyRecord objects.

        Raises:
            RepositoryError: If the query fails.
        """
        self.logger.debug(f"Getting inconsistencies (file='{file_path}', severity='{severity}', status='{status}', limit={limit})")
        try:
            with self.db_manager.get_session() as session:
                query = session.query(InconsistencyORM)

                # Apply filters
                if file_path:
                    query = query.filter(or_(
                        InconsistencyORM.source_file == file_path,
                        InconsistencyORM.target_file == file_path
                    ))
                if severity:
                    query = query.filter(InconsistencyORM.severity == severity.value)
                if status:
                    query = query.filter(InconsistencyORM.status == status.value)

                # Apply ordering (e.g., by severity descending, then detection time descending)
                # Need to import desc from sqlalchemy
                # query = query.order_by(desc(InconsistencyORM.severity), desc(InconsistencyORM.detected_at))
                query = query.order_by(InconsistencyORM.detected_at.desc()) # Simpler ordering for now

                # Apply limit
                query = query.limit(limit)

                # Execute query
                results_orm = query.all()
                results = [self._convert_orm_to_inconsistency(orm) for orm in results_orm]
                self.logger.debug(f"Retrieved {len(results)} inconsistencies matching criteria.")
                return results
        except Exception as e:
            self.logger.error(f"Error getting inconsistencies: {e}", exc_info=True)
            raise RepositoryError(f"Error getting inconsistencies: {e}") from e

    def delete(self, inconsistency_id: str) -> bool:
        """
        Deletes an inconsistency record by its ID.

        Args:
            inconsistency_id: The unique ID of the inconsistency to delete.

        Returns:
            True if a record was deleted, False otherwise.

        Raises:
            RepositoryError: If deletion fails.
        """
        self.logger.debug(f"Deleting inconsistency ID: {inconsistency_id}")
        deleted_count = 0
        try:
            with self.db_manager.get_session() as session:
                rel_id_int = int(inconsistency_id)
                deleted_count = session.query(InconsistencyORM).filter(InconsistencyORM.id == rel_id_int).delete()
                session.flush()

                if deleted_count == 0:
                    self.logger.warning(f"Inconsistency ID {inconsistency_id} not found for deletion.")
                else:
                    self.logger.info(f"Deleted inconsistency ID: {inconsistency_id}")
                return deleted_count > 0
        except ValueError:
             self.logger.error(f"Invalid inconsistency ID format for deletion: {inconsistency_id}")
             return False
        except Exception as e:
            self.logger.error(f"Error deleting inconsistency {inconsistency_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error deleting inconsistency {inconsistency_id}: {e}") from e

    def _convert_orm_to_inconsistency(self, orm: InconsistencyORM) -> InconsistencyRecord:
        """Converts an InconsistencyORM object to an InconsistencyRecord dataclass."""
        try:
            details_dict = json.loads(orm.details) if orm.details else {}
        except json.JSONDecodeError:
            self.logger.warning(f"Could not decode details JSON for inconsistency ID {orm.id}. Using empty dict.")
            details_dict = {}
        try:
            metadata_dict = json.loads(orm.metadata) if orm.metadata else {}
        except json.JSONDecodeError:
            self.logger.warning(f"Could not decode metadata JSON for inconsistency ID {orm.id}. Using empty dict.")
            metadata_dict = {}

        # Convert string representations back to enums safely
        try:
            inc_type = InconsistencyType(orm.inconsistency_type)
        except ValueError:
            self.logger.warning(f"Invalid inconsistency type '{orm.inconsistency_type}' found in DB for ID {orm.id}. Using OTHER.")
            inc_type = InconsistencyType.OTHER
        try:
            inc_severity = InconsistencySeverity(orm.severity)
        except ValueError:
            self.logger.warning(f"Invalid severity '{orm.severity}' found in DB for ID {orm.id}. Using LOW.")
            inc_severity = InconsistencySeverity.LOW
        try:
            inc_status = InconsistencyStatus(orm.status)
        except ValueError:
            self.logger.warning(f"Invalid status '{orm.status}' found in DB for ID {orm.id}. Using OPEN.")
            inc_status = InconsistencyStatus.OPEN


        return InconsistencyRecord(
            id=str(orm.id),
            source_file=orm.source_file,
            target_file=orm.target_file,
            inconsistency_type=inc_type,
            description=orm.description,
            details=details_dict,
            severity=inc_severity,
            status=inc_status,
            confidence_score=orm.confidence_score,
            detected_at=orm.detected_at.replace(tzinfo=timezone.utc) if orm.detected_at else None, # Assume UTC
            resolved_at=orm.resolved_at.replace(tzinfo=timezone.utc) if orm.resolved_at else None, # Assume UTC
            metadata=metadata_dict
        )
