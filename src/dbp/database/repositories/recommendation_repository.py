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
# Defines the RecommendationRepository class for managing Recommendation entities
# in the database, providing operations to create, update, and query recommendations.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for recommendation lifecycle management.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Recommendation, Inconsistency, SuggestedChange, and Document models from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:18:25Z : Created recommendation_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted RecommendationRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Recommendation entity operations.
"""

import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Recommendation, Inconsistency, SuggestedChange, Document
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Recommendation, Inconsistency, SuggestedChange, Document


logger = logging.getLogger(__name__)


class RecommendationRepository(BaseRepository):
    """Repository for managing Recommendation entities."""

    def create(self, title: str, inconsistency_ids: list[int], suggested_changes_data: list[dict]) -> Recommendation | None:
        """
        [Function intent]
        Creates a new recommendation and associated suggested changes.
        
        [Implementation details]
        Creates a Recommendation entity linked to existing Inconsistency entities
        and creates new SuggestedChange entities.
        Updates the status of linked inconsistencies.
        
        [Design principles]
        Validates input data existence before creating relationships.
        Returns created object for immediate use.
        
        Args:
            title: The title of the recommendation.
            inconsistency_ids: List of inconsistency IDs to link to this recommendation.
            suggested_changes_data: List of dictionaries with suggested change data.

        Returns:
            The created Recommendation object or None if creation failed.
        """
        operation = "create_recommendation"
        logger.debug(f"{operation}: Creating recommendation '{title}'.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = Recommendation(
                    creation_timestamp=datetime.datetime.now(),
                    title=title,
                    status="Active" # Initial status
                )

                # Link inconsistencies
                inconsistencies = session.query(Inconsistency).filter(Inconsistency.id.in_(inconsistency_ids)).all()
                if len(inconsistencies) != len(inconsistency_ids):
                     logger.warning(f"{operation}: Some inconsistency IDs not found.")
                recommendation.inconsistencies.extend(inconsistencies)

                # Create suggested changes
                for change_data in suggested_changes_data:
                    doc = session.query(Document).get(change_data.get('document_id'))
                    if not doc:
                        logger.warning(f"{operation}: Document ID {change_data.get('document_id')} not found for suggested change.")
                        continue # Skip this change or raise error?

                    change = SuggestedChange(
                        document_id=change_data.get('document_id'),
                        change_type=change_data.get('change_type'),
                        location=change_data.get('location'),
                        before_text=change_data.get('before_text'),
                        after_text=change_data.get('after_text')
                    )
                    recommendation.suggested_changes.append(change)

                session.add(recommendation)

                # Update status of linked inconsistencies
                for inc in inconsistencies:
                    inc.status = "InRecommendation"

                session.flush()
                logger.info(f"{operation}: Recommendation '{title}' created with ID {recommendation.id}.")
                return recommendation
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_active(self) -> Recommendation | None:
        """
        [Function intent]
        Retrieves the currently active recommendation (should be only one).
        
        [Implementation details]
        Queries recommendations filtered by "Active" status.
        Eager loads relationships for better performance.
        
        [Design principles]
        Returns the oldest active recommendation by creation_timestamp if multiple exist.
        
        Returns:
            The active Recommendation object or None if no active recommendation exists.
        """
        operation = "get_active_recommendation"
        logger.debug(f"{operation}: Fetching active recommendation.")
        try:
            with self.db_manager.get_session() as session:
                # Load relationships eagerly
                recommendation = session.query(Recommendation).filter(
                    Recommendation.status == "Active"
                ).options(
                    joinedload(Recommendation.inconsistencies).joinedload(Inconsistency.affected_documents),
                    joinedload(Recommendation.suggested_changes).joinedload(SuggestedChange.document)
                ).order_by(Recommendation.creation_timestamp).first() # Get the oldest active one

                if recommendation:
                    logger.debug(f"{operation}: Found active recommendation ID {recommendation.id}.")
                else:
                    logger.debug(f"{operation}: No active recommendation found.")
                return recommendation
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def update_status(self, recommendation_id: int, new_status: str, feedback: str = None) -> bool:
        """
        [Function intent]
        Updates the status of a recommendation.
        
        [Implementation details]
        Fetches the recommendation by ID and updates its status field.
        Also updates developer_feedback if provided and status is "Amended".
        
        [Design principles]
        Returns boolean to indicate success/failure.
        Special handling for the "Amended" status with feedback.
        
        Args:
            recommendation_id: The ID of the recommendation to update.
            new_status: The new status to set (e.g., 'Active', 'Accepted', 'Rejected', 'Amended').
            feedback: Optional developer feedback for "Amended" status.

        Returns:
            True if the update was successful, False otherwise.
        """
        operation = "update_recommendation_status"
        logger.debug(f"{operation}: Updating status of recommendation ID {recommendation_id} to '{new_status}'.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = session.query(Recommendation).get(recommendation_id)
                if recommendation:
                    recommendation.status = new_status
                    if new_status == "Amended" and feedback:
                        recommendation.developer_feedback = feedback
                    # Reset feedback if status changes from Amended?
                    elif recommendation.status != "Amended":
                         recommendation.developer_feedback = None

                    session.flush()
                    logger.info(f"{operation}: Status updated for recommendation ID {recommendation_id}.")
                    return True
                else:
                    logger.warning(f"{operation}: Recommendation ID {recommendation_id} not found.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def invalidate_active(self, change_timestamp: datetime.datetime) -> bool:
        """
        [Function intent]
        Marks the active recommendation as Invalidated due to codebase changes.
        
        [Implementation details]
        Finds the active recommendation and updates its status to "Invalidated".
        Also records the timestamp of the codebase change.
        
        [Design principles]
        Returns boolean to indicate success/failure.
        Records change timestamp for audit purposes.
        
        Args:
            change_timestamp: The timestamp of the change that invalidated the recommendation.

        Returns:
            True if an active recommendation was invalidated, False otherwise.
        """
        operation = "invalidate_active_recommendation"
        logger.debug(f"{operation}: Invalidating active recommendation due to change at {change_timestamp}.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = session.query(Recommendation).filter(Recommendation.status == "Active").first()
                if recommendation:
                    recommendation.status = "Invalidated"
                    recommendation.last_codebase_change_timestamp = change_timestamp
                    session.flush()
                    logger.info(f"{operation}: Active recommendation ID {recommendation.id} invalidated.")
                    return True
                else:
                    logger.debug(f"{operation}: No active recommendation to invalidate.")
                    return False # Or True, as there was nothing to do?
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def delete_old_recommendations(self, days_old: int = 7) -> int:
        """
        [Function intent]
        Deletes recommendations older than a specified number of days.
        
        [Implementation details]
        Calculates a cutoff date and deletes recommendations created before that date.
        Excludes active recommendations from deletion.
        
        [Design principles]
        Returns count of deleted recommendations for reporting.
        Protects active recommendations regardless of age.
        
        Args:
            days_old: Number of days after which recommendations are considered old.

        Returns:
            Number of recommendations deleted.
        """
        operation = "delete_old_recommendations"
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        logger.info(f"{operation}: Deleting recommendations created before {cutoff_date}.")
        try:
            with self.db_manager.get_session() as session:
                # Find old recommendations (excluding Active ones)
                query = session.query(Recommendation).filter(
                    Recommendation.creation_timestamp < cutoff_date,
                    Recommendation.status != "Active" # Don't delete the active one
                )
                count = query.delete(synchronize_session=False)
                session.flush()
                logger.info(f"{operation}: Deleted {count} old recommendations.")
                return count
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return 0
