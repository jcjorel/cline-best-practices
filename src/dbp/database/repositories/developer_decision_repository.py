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
# Defines the DeveloperDecisionRepository class for managing DeveloperDecision
# entities in the database, providing operations to record and query developer decisions.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for developer decision operations.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on DeveloperDecision and Recommendation models from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:32:19Z : Created developer_decision_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted DeveloperDecisionRepository class from original repositories.py
###############################################################################

"""
Repository implementation for DeveloperDecision entity operations.
"""

import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import DeveloperDecision, Recommendation
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import DeveloperDecision, Recommendation


logger = logging.getLogger(__name__)


class DeveloperDecisionRepository(BaseRepository):
    """Repository for managing DeveloperDecision entities."""

    def create(self, recommendation_id: int, decision: str, comments: str = None, implementation_timestamp: datetime.datetime = None) -> DeveloperDecision | None:
        """
        [Function intent]
        Creates a new developer decision record.
        
        [Implementation details]
        Creates a DeveloperDecision entity linked to an existing Recommendation.
        Validates recommendation existence before creating the decision.
        
        [Design principles]
        Uses session context manager for proper transaction handling.
        Returns created object for immediate use.
        
        Args:
            recommendation_id: The ID of the recommendation this decision is for.
            decision: The developer's decision (e.g., 'Accept', 'Reject', 'Amend').
            comments: Optional developer comments explaining the decision.
            implementation_timestamp: Optional timestamp when the recommendation was implemented.

        Returns:
            The created DeveloperDecision object or None if creation failed.
        """
        operation = "create_developer_decision"
        logger.debug(f"{operation}: Recording decision '{decision}' for recommendation ID {recommendation_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Ensure recommendation exists
                recommendation = session.query(Recommendation).get(recommendation_id)
                if not recommendation:
                    logger.error(f"{operation}: Recommendation ID {recommendation_id} not found.")
                    return None

                dev_decision = DeveloperDecision(
                    recommendation_id=recommendation_id,
                    timestamp=datetime.datetime.now(),
                    decision=decision,
                    comments=comments,
                    implementation_timestamp=implementation_timestamp
                )
                session.add(dev_decision)
                session.flush()
                logger.info(f"{operation}: Decision '{decision}' recorded with ID {dev_decision.id} for recommendation ID {recommendation_id}.")
                return dev_decision
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_recommendation(self, recommendation_id: int) -> list[DeveloperDecision]:
        """
        [Function intent]
        Retrieves all decisions for a specific recommendation.
        
        [Implementation details]
        Queries decisions filtered by recommendation_id.
        Orders results by timestamp in descending order (newest first).
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        
        Args:
            recommendation_id: The ID of the recommendation to get decisions for.

        Returns:
            A list of DeveloperDecision objects for the recommendation.
        """
        operation = "get_decisions_by_recommendation"
        logger.debug(f"{operation}: Fetching decisions for recommendation ID {recommendation_id}.")
        try:
            with self.db_manager.get_session() as session:
                decisions = session.query(DeveloperDecision).filter(
                    DeveloperDecision.recommendation_id == recommendation_id
                ).order_by(DeveloperDecision.timestamp.desc()).all()
                logger.debug(f"{operation}: Found {len(decisions)} decisions for recommendation ID {recommendation_id}.")
                return decisions
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []
