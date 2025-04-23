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
# Implements the RecommendationRepository class, responsible for interacting
# with the database to persist and retrieve Recommendation data. It uses the
# DatabaseManager for session handling and the RecommendationORM model for mapping.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern for data access abstraction.
# - Provides methods for saving, updating, retrieving (by ID, with filters), and deleting recommendations.
# - Handles conversion between the Recommendation dataclass and the RecommendationORM model.
# - Uses the injected DatabaseManager for database sessions.
# - Includes error handling and logging for database operations.
# - Stores complex fields like inconsistency_ids, metadata, and feedback as JSON strings.
###############################################################################
# [Source file constraints]
# - Depends on `DatabaseManager` and the `RecommendationORM` model.
# - Assumes the database schema includes the `recommendations` table.
# - Relies on `json` library for serializing/deserializing complex fields.
# - Enum values are stored as strings.
# - Filtering by inconsistency_id relies on database-specific JSON querying capabilities or string matching.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# other:- src/dbp/database/database.py
# other:- src/dbp/database/models.py
# system:- src/dbp/recommendation_generator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:38:40Z : Initial creation of RecommendationRepository by CodeAssistant
# * Implemented CRUD operations and ORM/dataclass conversion logic for recommendations.
###############################################################################

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import desc # For ordering

# Assuming necessary imports
try:
    from ..database.database import DatabaseManager
    from ..database.models import RecommendationORM
    from .data_models import (
        Recommendation, RecommendationFeedback, RecommendationFixType,
        RecommendationSeverity, RecommendationStatus
    )
    # Import Component for type hint if db_manager is passed via component
    from ..core.component import Component
except ImportError as e:
    logging.getLogger(__name__).error(f"RecommendationRepository ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    DatabaseManager = object
    RecommendationORM = object
    Recommendation = object
    RecommendationFeedback = object
    Component = object
    # Dummy Enum for placeholder
    class Enum:
        def __init__(self, value): self.value = value
    class RecommendationFixType(Enum): pass
    class RecommendationSeverity(Enum): pass
    class RecommendationStatus(Enum): pass


logger = logging.getLogger(__name__)

class RepositoryError(Exception):
    """Custom exception for repository-level errors."""
    pass

class RecommendationNotFoundError(ValueError):
    """Custom exception when a specific recommendation is not found."""
    pass


class RecommendationRepository:
    """
    Repository class for managing the persistence of Recommendation objects
    in the database.
    """

    def __init__(self, db_manager: DatabaseManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the RecommendationRepository.

        Args:
            db_manager: An initialized DatabaseManager instance.
            logger_override: Optional logger instance.
        """
        if not isinstance(db_manager, DatabaseManager):
             logger.warning("RecommendationRepository initialized with potentially incorrect db_manager type.")
        self.db_manager = db_manager
        self.logger = logger_override or logger
        self.logger.debug("RecommendationRepository initialized.")

    def save(self, recommendation: Recommendation) -> str:
        """
        Saves a new recommendation record to the database.

        Args:
            recommendation: The Recommendation dataclass instance to save.

        Returns:
            The unique ID (as string) assigned to the saved recommendation.

        Raises:
            RepositoryError: If saving fails.
        """
        self.logger.debug(f"Saving recommendation: '{recommendation.title}'")
        try:
            with self.db_manager.get_session() as session:
                # Convert recommendation dataclass to ORM model
                recommendation_orm = RecommendationORM(
                    title=recommendation.title,
                    description=recommendation.description,
                    strategy_name=recommendation.strategy_name,
                    fix_type=recommendation.fix_type.value,
                    severity=recommendation.severity.value,
                    status=recommendation.status.value,
                    source_file=recommendation.source_file,
                    target_file=recommendation.target_file,
                    inconsistency_ids=json.dumps(recommendation.inconsistency_ids or []),
                    code_snippet=recommendation.code_snippet,
                    doc_snippet=recommendation.doc_snippet,
                    created_at=recommendation.created_at or datetime.now(timezone.utc),
                    updated_at=recommendation.updated_at or datetime.now(timezone.utc),
                    applied_at=recommendation.applied_at,
                    metadata=json.dumps(recommendation.metadata) if recommendation.metadata else None,
                    feedback=json.dumps(recommendation.feedback.to_dict()) if recommendation.feedback else None
                )
                session.add(recommendation_orm)
                session.flush() # Flush to get the generated ID
                recommendation_id = str(recommendation_orm.id)
                # Update the dataclass with the generated ID if it was None
                if recommendation.id is None:
                     recommendation.id = recommendation_id
                self.logger.info(f"Saved recommendation with ID: {recommendation_id}")
                return recommendation_id
        except Exception as e:
            self.logger.error(f"Error saving recommendation '{recommendation.title}': {e}", exc_info=True)
            raise RepositoryError(f"Error saving recommendation: {e}") from e

    def update(self, recommendation: Recommendation):
        """
        Updates an existing recommendation record in the database.
        The recommendation object must have a valid `id`.

        Args:
            recommendation: The Recommendation dataclass instance with updated data.

        Raises:
            RepositoryError: If the recommendation ID is missing or the update fails.
            RecommendationNotFoundError: If the recommendation ID is not found.
        """
        if not recommendation.id:
            raise RepositoryError("Cannot update recommendation without a valid ID.")

        self.logger.debug(f"Updating recommendation ID: {recommendation.id}")
        try:
            with self.db_manager.get_session() as session:
                rec_id_int = int(recommendation.id)
                recommendation_orm = session.query(RecommendationORM).get(rec_id_int)
                if not recommendation_orm:
                    raise RecommendationNotFoundError(f"Recommendation with ID {recommendation.id} not found for update.")

                # Update fields from the dataclass
                recommendation_orm.title = recommendation.title
                recommendation_orm.description = recommendation.description
                recommendation_orm.strategy_name = recommendation.strategy_name
                recommendation_orm.fix_type = recommendation.fix_type.value
                recommendation_orm.severity = recommendation.severity.value
                recommendation_orm.status = recommendation.status.value
                recommendation_orm.source_file = recommendation.source_file
                recommendation_orm.target_file = recommendation.target_file
                recommendation_orm.inconsistency_ids = json.dumps(recommendation.inconsistency_ids or [])
                recommendation_orm.code_snippet = recommendation.code_snippet
                recommendation_orm.doc_snippet = recommendation.doc_snippet
                recommendation_orm.applied_at = recommendation.applied_at
                recommendation_orm.metadata = json.dumps(recommendation.metadata) if recommendation.metadata else None
                recommendation_orm.feedback = json.dumps(recommendation.feedback.to_dict()) if recommendation.feedback else None
                recommendation_orm.updated_at = datetime.now(timezone.utc) # Explicitly set update time

                session.flush()
                self.logger.info(f"Updated recommendation ID: {recommendation.id}")
        except ValueError as e:
             # Handles case where ID is not an integer or enum conversion fails
             self.logger.error(f"Value error updating recommendation {recommendation.id}: {e}")
             raise RecommendationNotFoundError(f"Invalid data for recommendation {recommendation.id}") from e # Re-raise as specific error
        except Exception as e:
            self.logger.error(f"Error updating recommendation {recommendation.id}: {e}", exc_info=True)
            raise RepositoryError(f"Error updating recommendation {recommendation.id}: {e}") from e

    def get(self, recommendation_id: str) -> Optional[Recommendation]:
        """
        Retrieves a single recommendation by its ID.

        Args:
            recommendation_id: The unique ID of the recommendation.

        Returns:
            A Recommendation object if found, otherwise None.

        Raises:
            RepositoryError: If retrieval fails.
        """
        self.logger.debug(f"Getting recommendation ID: {recommendation_id}")
        try:
            with self.db_manager.get_session() as session:
                rec_id_int = int(recommendation_id)
                recommendation_orm = session.query(RecommendationORM).get(rec_id_int)
                if recommendation_orm:
                    return self._convert_orm_to_recommendation(recommendation_orm)
                else:
                    self.logger.debug(f"Recommendation ID {recommendation_id} not found.")
                    return None
        except ValueError:
             self.logger.error(f"Invalid recommendation ID format for get: {recommendation_id}")
             return None
        except Exception as e:
            self.logger.error(f"Error getting recommendation {recommendation_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error getting recommendation {recommendation_id}: {e}") from e

    def get_recommendations(
        self,
        inconsistency_id: Optional[str] = None,
        status: Optional[RecommendationStatus] = None,
        limit: int = 100
    ) -> List[Recommendation]:
        """
        Retrieves a list of recommendations, optionally filtered by inconsistency ID
        and status.

        Args:
            inconsistency_id: If provided, returns recommendations linked to this inconsistency ID.
            status: If provided, filters by status (enum member).
            limit: The maximum number of records to return.

        Returns:
            A list of matching Recommendation objects.

        Raises:
            RepositoryError: If the query fails.
        """
        self.logger.debug(f"Getting recommendations (inconsistency='{inconsistency_id}', status='{status}', limit={limit})")
        try:
            with self.db_manager.get_session() as session:
                query = session.query(RecommendationORM)

                # Apply filters
                if inconsistency_id:
                    # Assumes inconsistency_ids is stored as a JSON string array.
                    # This query might be inefficient depending on DB.
                    query = query.filter(RecommendationORM.inconsistency_ids.like(f'%"{inconsistency_id}"%'))
                if status:
                    query = query.filter(RecommendationORM.status == status.value)

                # Apply ordering (e.g., by severity descending, then creation time descending)
                # query = query.order_by(desc(RecommendationORM.severity), desc(RecommendationORM.created_at))
                query = query.order_by(RecommendationORM.created_at.desc()) # Simpler ordering

                # Apply limit
                query = query.limit(limit)

                # Execute query
                results_orm = query.all()
                results = [self._convert_orm_to_recommendation(orm) for orm in results_orm]
                self.logger.debug(f"Retrieved {len(results)} recommendations matching criteria.")
                return results
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}", exc_info=True)
            raise RepositoryError(f"Error getting recommendations: {e}") from e

    def delete(self, recommendation_id: str) -> bool:
        """
        Deletes a recommendation record by its ID.

        Args:
            recommendation_id: The unique ID of the recommendation to delete.

        Returns:
            True if a record was deleted, False otherwise.

        Raises:
            RepositoryError: If deletion fails.
        """
        self.logger.debug(f"Deleting recommendation ID: {recommendation_id}")
        deleted_count = 0
        try:
            with self.db_manager.get_session() as session:
                rec_id_int = int(recommendation_id)
                deleted_count = session.query(RecommendationORM).filter(RecommendationORM.id == rec_id_int).delete()
                session.flush()

                if deleted_count == 0:
                    self.logger.warning(f"Recommendation ID {recommendation_id} not found for deletion.")
                else:
                    self.logger.info(f"Deleted recommendation ID: {recommendation_id}")
                return deleted_count > 0
        except ValueError:
             self.logger.error(f"Invalid recommendation ID format for deletion: {recommendation_id}")
             return False
        except Exception as e:
            self.logger.error(f"Error deleting recommendation {recommendation_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error deleting recommendation {recommendation_id}: {e}") from e

    def _convert_orm_to_recommendation(self, orm: RecommendationORM) -> Recommendation:
        """Converts a RecommendationORM object to a Recommendation dataclass."""
        feedback = None
        if orm.feedback:
            try:
                feedback_dict = json.loads(orm.feedback)
                feedback = RecommendationFeedback.from_dict(feedback_dict)
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning(f"Could not decode feedback JSON for recommendation ID {orm.id}: {e}")

        try:
            inconsistency_ids_list = json.loads(orm.inconsistency_ids or '[]')
            if not isinstance(inconsistency_ids_list, list):
                 inconsistency_ids_list = []
                 self.logger.warning(f"inconsistency_ids field for recommendation ID {orm.id} is not a list.")
        except json.JSONDecodeError:
            self.logger.warning(f"Could not decode inconsistency_ids JSON for recommendation ID {orm.id}. Using empty list.")
            inconsistency_ids_list = []

        try:
             metadata_dict = json.loads(orm.metadata) if orm.metadata else {}
        except json.JSONDecodeError:
             self.logger.warning(f"Could not decode metadata JSON for recommendation ID {orm.id}. Using empty dict.")
             metadata_dict = {}

        # Convert enum strings back to enums safely
        try: fix_type = RecommendationFixType(orm.fix_type)
        except ValueError: fix_type = RecommendationFixType.COMBINED; self.logger.warning(f"Invalid fix_type '{orm.fix_type}' for rec ID {orm.id}")
        try: severity = RecommendationSeverity(orm.severity)
        except ValueError: severity = RecommendationSeverity.LOW; self.logger.warning(f"Invalid severity '{orm.severity}' for rec ID {orm.id}")
        try: status = RecommendationStatus(orm.status)
        except ValueError: status = RecommendationStatus.PENDING; self.logger.warning(f"Invalid status '{orm.status}' for rec ID {orm.id}")


        return Recommendation(
            id=str(orm.id),
            title=orm.title,
            description=orm.description,
            strategy_name=orm.strategy_name,
            fix_type=fix_type,
            severity=severity,
            status=status,
            source_file=orm.source_file,
            target_file=orm.target_file,
            inconsistency_ids=inconsistency_ids_list,
            code_snippet=orm.code_snippet,
            doc_snippet=orm.doc_snippet,
            created_at=orm.created_at.replace(tzinfo=timezone.utc) if orm.created_at else None,
            updated_at=orm.updated_at.replace(tzinfo=timezone.utc) if orm.updated_at else None,
            applied_at=orm.applied_at.replace(tzinfo=timezone.utc) if orm.applied_at else None,
            metadata=metadata_dict,
            feedback=feedback
        )
