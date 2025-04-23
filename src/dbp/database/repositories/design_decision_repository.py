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
# Defines the DesignDecisionRepository class for managing DesignDecision entities
# in the database, providing operations to create, update, and query design decisions.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides bulk operation for design decision management.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on DesignDecision model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
# codebase:- doc/DESIGN_DECISIONS.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:33:27Z : Created design_decision_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted DesignDecisionRepository class from original repositories.py
###############################################################################

"""
Repository implementation for DesignDecision entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import DesignDecision
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import DesignDecision


logger = logging.getLogger(__name__)


class DesignDecisionRepository(BaseRepository):
    """Repository for managing DesignDecision entities."""

    def bulk_create_or_update(self, document_id: int, decisions_data: list[dict]):
        """
        [Function intent]
        Creates or updates design decisions for a given document.
        
        [Implementation details]
        Uses a replace approach: deletes existing design decisions and creates new ones.
        This simplifies management of design decisions that may have been removed or changed.
        
        [Design principles]
        Uses a bulk operation for better performance with multiple design decisions.
        Replaces rather than updates to ensure consistency.
        
        Args:
            document_id: ID of the document these design decisions belong to.
            decisions_data: List of dictionaries with design decision data.
        """
        operation = "bulk_create_or_update_design_decisions"
        logger.debug(f"{operation}: Processing {len(decisions_data)} design decisions for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Simple approach: delete existing and add new ones for the document
                session.query(DesignDecision).filter_by(document_id=document_id).delete(synchronize_session=False)
                added_count = 0
                for data in decisions_data:
                    decision = DesignDecision(
                        document_id=document_id,
                        description=data.get('description'),
                        rationale=data.get('rationale'),
                        alternatives=data.get('alternatives'),
                        decision_date=data.get('decision_date') # Assumes datetime object or None
                    )
                    session.add(decision)
                    added_count += 1
                session.flush()
                logger.info(f"{operation}: Added {added_count} design decisions for document ID {document_id}.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
