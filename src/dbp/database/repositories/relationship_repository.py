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
# Defines the RelationshipRepository class for managing DocumentRelationship 
# entities in the database, providing operations to create and query document
# relationships.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for relationship operations.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on DocumentRelationship model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:13:00Z : Created relationship_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted RelationshipRepository class from original repositories.py
###############################################################################

"""
Repository implementation for DocumentRelationship entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import DocumentRelationship
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import DocumentRelationship


logger = logging.getLogger(__name__)


class RelationshipRepository(BaseRepository):
    """Repository for managing DocumentRelationship entities."""

    def create(self, source_id: int, target_id: int, relationship_type: str, topic: str, scope: str) -> DocumentRelationship | None:
        """
        [Function intent]
        Creates a new document relationship.
        
        [Implementation details]
        Checks for duplicate relationships before creating a new one.
        
        [Design principles]
        Prevents duplicate relationships for the same source, target, and type.
        
        Args:
            source_id: ID of the source document.
            target_id: ID of the target document.
            relationship_type: Type of relationship (e.g., 'DependsOn', 'Impacts').
            topic: Subject matter of the relationship.
            scope: How broadly the relationship applies.

        Returns:
            The created DocumentRelationship object or existing one if already exists,
            None if creation failed.
        """
        operation = "create_relationship"
        logger.debug(f"{operation}: Creating relationship {relationship_type} from {source_id} to {target_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Check if relationship already exists to avoid duplicates
                existing = session.query(DocumentRelationship).filter_by(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=relationship_type,
                    topic=topic,
                    scope=scope
                ).first()
                if existing:
                    logger.warning(f"{operation}: Relationship already exists (ID: {existing.id}).")
                    return existing

                relationship = DocumentRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=relationship_type,
                    topic=topic,
                    scope=scope
                )
                session.add(relationship)
                session.flush()
                logger.info(f"{operation}: Relationship created with ID {relationship.id}.")
                return relationship
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_relationships_for_document(self, document_id: int) -> list[DocumentRelationship]:
        """
        [Function intent]
        Retrieves all relationships where the document is either source or target.
        
        [Implementation details]
        Uses an OR condition to find relationships in both directions.
        Eager loads related documents for better performance.
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        
        Args:
            document_id: ID of the document to find relationships for.

        Returns:
            A list of DocumentRelationship objects involving the document.
        """
        operation = "get_relationships_for_document"
        logger.debug(f"{operation}: Getting relationships for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                relationships = session.query(DocumentRelationship).filter(
                    (DocumentRelationship.source_id == document_id) |
                    (DocumentRelationship.target_id == document_id)
                ).options(joinedload(DocumentRelationship.source), joinedload(DocumentRelationship.target)).all()
                logger.debug(f"{operation}: Found {len(relationships)} relationships for document ID {document_id}.")
                return relationships
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []

    def delete_relationships_for_document(self, document_id: int) -> bool:
        """
        [Function intent]
        Deletes all relationships associated with a document.
        
        [Implementation details]
        Deletes relationships where the document is either source or target.
        
        [Design principles]
        Returns boolean to indicate success/failure.
        
        Args:
            document_id: ID of the document to delete relationships for.

        Returns:
            True if deletion was successful, False otherwise.
        """
        operation = "delete_relationships_for_document"
        logger.debug(f"{operation}: Deleting relationships for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                deleted_count = session.query(DocumentRelationship).filter(
                    (DocumentRelationship.source_id == document_id) |
                    (DocumentRelationship.target_id == document_id)
                ).delete(synchronize_session=False)
                session.flush()
                logger.info(f"{operation}: Deleted {deleted_count} relationships for document ID {document_id}.")
                return True
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False
