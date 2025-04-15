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
# Defines the ChangeRecordRepository class for managing ChangeRecord entities
# in the database, providing operations to create and query change history records.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides bulk operations for change record management.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on ChangeRecord model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:35:04Z : Created change_record_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted ChangeRecordRepository class from original repositories.py
###############################################################################

"""
Repository implementation for ChangeRecord entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import ChangeRecord
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import ChangeRecord


logger = logging.getLogger(__name__)


class ChangeRecordRepository(BaseRepository):
    """Repository for managing ChangeRecord entities."""

    def bulk_create(self, document_id: int, records_data: list[dict]):
        """
        [Function intent]
        Bulk creates change records for a document.
        
        [Implementation details]
        Uses a replace approach: deletes existing change records and creates new ones.
        This ensures the change history is completely refreshed with each update.
        
        [Design principles]
        Uses a bulk operation for better performance with multiple records.
        Replaces rather than updates to ensure consistency.
        
        Args:
            document_id: ID of the document these change records belong to.
            records_data: List of dictionaries with change record data.
        """
        operation = "bulk_create_change_records"
        logger.debug(f"{operation}: Adding {len(records_data)} change records for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                 # Simple approach: delete existing and add new ones for the document
                session.query(ChangeRecord).filter_by(document_id=document_id).delete(synchronize_session=False)
                added_count = 0
                for data in records_data:
                    record = ChangeRecord(
                        document_id=document_id,
                        timestamp=data.get('timestamp'), # Assumes datetime object
                        summary=data.get('summary'),
                        details=data.get('details')
                    )
                    session.add(record)
                    added_count += 1
                session.flush()
                logger.info(f"{operation}: Added {added_count} change records for document ID {document_id}.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)

    def get_by_document(self, document_id: int) -> list[ChangeRecord]:
        """
        [Function intent]
        Retrieves change records for a specific document.
        
        [Implementation details]
        Queries change records filtered by document_id.
        Orders results by timestamp in descending order (newest first).
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        
        Args:
            document_id: The ID of the document to get change records for.

        Returns:
            A list of ChangeRecord objects for the document.
        """
        operation = "get_change_records_by_document"
        logger.debug(f"{operation}: Fetching change records for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                records = session.query(ChangeRecord).filter(
                    ChangeRecord.document_id == document_id
                ).order_by(ChangeRecord.timestamp.desc()).all()
                logger.debug(f"{operation}: Found {len(records)} change records for document ID {document_id}.")
                return records
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []
