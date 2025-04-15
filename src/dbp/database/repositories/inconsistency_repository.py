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
# Defines the InconsistencyRepository class for managing Inconsistency entities
# in the database, providing operations to create, update, and query inconsistencies.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for inconsistency lifecycle management.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Inconsistency and Document models from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:16:49Z : Created inconsistency_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted InconsistencyRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Inconsistency entity operations.
"""

import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Inconsistency, Document
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Inconsistency, Document


logger = logging.getLogger(__name__)


class InconsistencyRepository(BaseRepository):
    """Repository for managing Inconsistency entities."""

    def create(self, severity: str, type: str, description: str, affected_document_ids: list[int], suggested_resolution: str = None) -> Inconsistency | None:
        """
        [Function intent]
        Creates a new inconsistency record in the database.
        
        [Implementation details]
        Builds an Inconsistency object and connects it with affected documents.
        Validates document existence before creating relationships.
        
        [Design principles]
        Uses session context manager for proper transaction handling.
        Returns created object for immediate use.
        
        Args:
            severity: The severity level of the inconsistency (e.g., 'Critical', 'Major', 'Minor').
            type: The type of inconsistency (e.g., 'DocToDoc', 'DocToCode', 'DesignDecisionViolation').
            description: A description of the inconsistency.
            affected_document_ids: List of document IDs affected by this inconsistency.
            suggested_resolution: Optional suggested resolution for the inconsistency.

        Returns:
            The created Inconsistency object or None if creation failed.
        """
        operation = "create_inconsistency"
        logger.debug(f"{operation}: Creating inconsistency: type='{type}', severity='{severity}'.")
        try:
            with self.db_manager.get_session() as session:
                inconsistency = Inconsistency(
                    timestamp=datetime.datetime.now(),
                    severity=severity,
                    type=type,
                    description=description,
                    suggested_resolution=suggested_resolution,
                    status="Pending"
                )
                # Fetch Document objects for relationships
                affected_docs = session.query(Document).filter(Document.id.in_(affected_document_ids)).all()
                if len(affected_docs) != len(affected_document_ids):
                    logger.warning(f"{operation}: Some affected document IDs not found.")
                    # Decide whether to proceed or raise error
                inconsistency.affected_documents.extend(affected_docs)

                session.add(inconsistency)
                session.flush()
                logger.info(f"{operation}: Inconsistency created with ID {inconsistency.id}.")
                return inconsistency
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_pending(self) -> list[Inconsistency]:
        """
        [Function intent]
        Retrieves all inconsistencies with 'Pending' status.
        
        [Implementation details]
        Queries inconsistencies filtered by 'Pending' status.
        Eager loads affected document relationships for better performance.
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        Uses joinedload to optimize relationship loading.
        
        Returns:
            A list of Inconsistency objects with 'Pending' status.
        """
        operation = "get_pending_inconsistencies"
        logger.debug(f"{operation}: Fetching pending inconsistencies.")
        try:
            with self.db_manager.get_session() as session:
                inconsistencies = session.query(Inconsistency).filter(
                    Inconsistency.status == "Pending"
                ).options(joinedload(Inconsistency.affected_documents)).all()
                logger.debug(f"{operation}: Found {len(inconsistencies)} pending inconsistencies.")
                return inconsistencies
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []

    def update_status(self, inconsistency_id: int, new_status: str) -> bool:
        """
        [Function intent]
        Updates the status of an inconsistency.
        
        [Implementation details]
        Fetches the inconsistency by ID and updates its status field.
        
        [Design principles]
        Returns boolean to indicate success/failure.
        
        Args:
            inconsistency_id: The ID of the inconsistency to update.
            new_status: The new status to set (e.g., 'Pending', 'InRecommendation', 'Resolved').

        Returns:
            True if the update was successful, False otherwise.
        """
        operation = "update_inconsistency_status"
        logger.debug(f"{operation}: Updating status of inconsistency ID {inconsistency_id} to '{new_status}'.")
        try:
            with self.db_manager.get_session() as session:
                inconsistency = session.query(Inconsistency).get(inconsistency_id)
                if inconsistency:
                    inconsistency.status = new_status
                    session.flush()
                    logger.info(f"{operation}: Status updated for inconsistency ID {inconsistency_id}.")
                    return True
                else:
                    logger.warning(f"{operation}: Inconsistency ID {inconsistency_id} not found.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False
