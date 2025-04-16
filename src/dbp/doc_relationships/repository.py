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
# Implements the RelationshipRepository class, responsible for interacting with
# the database to persist and retrieve DocumentRelationship data. It uses the
# DatabaseManager for session handling and the DocRelationshipORM model for mapping.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern, abstracting database operations for relationships.
# - Provides methods for saving, updating, deleting, and querying relationships.
# - Handles conversion between the DocumentRelationship dataclass and the DocRelationshipORM model.
# - Uses the injected DatabaseManager for database sessions.
# - Includes error handling and logging for database operations.
###############################################################################
# [Source file constraints]
# - Depends on `DatabaseManager` and the `DocRelationshipORM` model.
# - Assumes the database schema includes the `doc_relationships` table.
# - Relies on `json` library for serializing/deserializing metadata.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - src/dbp/database/database.py
# - src/dbp/database/models.py
# - src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:19:15Z : Initial creation of RelationshipRepository class by CodeAssistant
# * Implemented CRUD operations and ORM/dataclass conversion logic.
###############################################################################

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# Assuming necessary imports
try:
    from ..database.database import DatabaseManager
    from ..database.models import DocRelationshipORM
    from .data_models import DocumentRelationship
    # Import Component for type hint if db_manager is passed via component
    from ..core.component import Component
except ImportError as e:
    logging.getLogger(__name__).error(f"RelationshipRepository ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    DatabaseManager = object
    DocRelationshipORM = object
    DocumentRelationship = object
    Component = object

logger = logging.getLogger(__name__)

class RepositoryError(Exception):
    """Custom exception for repository-level errors."""
    pass

class RelationshipRepository:
    """
    Repository class for managing the persistence of DocumentRelationship objects
    in the database.
    """

    def __init__(self, db_manager: DatabaseManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the RelationshipRepository.

        Args:
            db_manager: An initialized DatabaseManager instance.
            logger_override: Optional logger instance.
        """
        if not isinstance(db_manager, DatabaseManager):
             logger.warning("RelationshipRepository initialized with potentially incorrect db_manager type.")
        self.db_manager = db_manager
        self.logger = logger_override or logger
        self.logger.debug("RelationshipRepository initialized.")

    def save_relationship(self, relationship: DocumentRelationship) -> str:
        """
        Saves a new document relationship to the database.

        Args:
            relationship: The DocumentRelationship dataclass instance to save.

        Returns:
            The unique ID (as string) assigned to the saved relationship.

        Raises:
            RepositoryError: If saving fails.
        """
        self.logger.debug(f"Saving relationship: {relationship.source_document} -> {relationship.target_document} ({relationship.relationship_type})")
        try:
            with self.db_manager.get_session() as session:
                # Convert dataclass to ORM model
                relationship_orm = DocRelationshipORM(
                    source_document=relationship.source_document,
                    target_document=relationship.target_document,
                    relationship_type=relationship.relationship_type,
                    topic=relationship.topic,
                    scope=relationship.scope,
                    # Serialize metadata dict to JSON string for storage
                    metadata=json.dumps(relationship.metadata) if relationship.metadata else None,
                    # created_at and updated_at have defaults in the model
                )
                session.add(relationship_orm)
                session.flush() # Flush to get the generated ID
                relationship_id = str(relationship_orm.id)
                self.logger.info(f"Saved relationship with ID: {relationship_id}")
                return relationship_id
        except Exception as e:
            self.logger.error(f"Error saving relationship ({relationship.source_document} -> {relationship.target_document}): {e}", exc_info=True)
            raise RepositoryError(f"Error saving relationship: {e}") from e

    def update_relationship(self, relationship: DocumentRelationship):
        """
        Updates an existing document relationship in the database.
        The relationship object must have a valid `id`.

        Args:
            relationship: The DocumentRelationship dataclass instance with updated data.

        Raises:
            RepositoryError: If the relationship ID is missing or the update fails.
            ValueError: If the relationship ID is not found.
        """
        if not relationship.id:
            raise RepositoryError("Cannot update relationship without a valid ID.")

        self.logger.debug(f"Updating relationship ID: {relationship.id}")
        try:
            with self.db_manager.get_session() as session:
                relationship_orm = session.query(DocRelationshipORM).get(int(relationship.id)) # Fetch by primary key
                if not relationship_orm:
                    raise ValueError(f"Relationship with ID {relationship.id} not found for update.")

                # Update fields from the dataclass
                relationship_orm.source_document = relationship.source_document
                relationship_orm.target_document = relationship.target_document
                relationship_orm.relationship_type = relationship.relationship_type
                relationship_orm.topic = relationship.topic
                relationship_orm.scope = relationship.scope
                relationship_orm.metadata = json.dumps(relationship.metadata) if relationship.metadata else None
                # updated_at is handled by the ORM model's onupdate

                session.flush() # Ensure changes are flushed before commit (optional here)
                self.logger.info(f"Updated relationship ID: {relationship.id}")
        except ValueError as e:
             self.logger.error(f"Value error updating relationship {relationship.id}: {e}")
             raise e
        except Exception as e:
            self.logger.error(f"Error updating relationship {relationship.id}: {e}", exc_info=True)
            raise RepositoryError(f"Error updating relationship {relationship.id}: {e}") from e

    def delete_relationship(self, relationship_id: str):
        """
        Deletes a document relationship from the database by its ID.

        Args:
            relationship_id: The unique ID of the relationship to delete.

        Raises:
            RepositoryError: If deletion fails.
        """
        self.logger.debug(f"Deleting relationship ID: {relationship_id}")
        try:
            with self.db_manager.get_session() as session:
                # Convert id back to int for query
                rel_id_int = int(relationship_id)
                result = session.query(DocRelationshipORM).filter(DocRelationshipORM.id == rel_id_int).delete()
                session.flush()

                if result == 0:
                    self.logger.warning(f"Relationship ID {relationship_id} not found for deletion.")
                else:
                    self.logger.info(f"Deleted relationship ID: {relationship_id}")
        except ValueError:
             self.logger.error(f"Invalid relationship ID format for deletion: {relationship_id}")
             # Or raise RepositoryError("Invalid ID format")
        except Exception as e:
            self.logger.error(f"Error deleting relationship {relationship_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error deleting relationship {relationship_id}: {e}") from e

    def get_relationship(self, relationship_id: str) -> Optional[DocumentRelationship]:
        """
        Retrieves a single document relationship by its ID.

        Args:
            relationship_id: The unique ID of the relationship.

        Returns:
            A DocumentRelationship object if found, otherwise None.

        Raises:
            RepositoryError: If retrieval fails.
        """
        self.logger.debug(f"Getting relationship ID: {relationship_id}")
        try:
            with self.db_manager.get_session() as session:
                rel_id_int = int(relationship_id)
                relationship_orm = session.query(DocRelationshipORM).get(rel_id_int)
                if relationship_orm:
                    return self._convert_orm_to_relationship(relationship_orm)
                else:
                    self.logger.debug(f"Relationship ID {relationship_id} not found.")
                    return None
        except ValueError:
             self.logger.error(f"Invalid relationship ID format for get: {relationship_id}")
             return None
        except Exception as e:
            self.logger.error(f"Error getting relationship {relationship_id}: {e}", exc_info=True)
            raise RepositoryError(f"Error getting relationship {relationship_id}: {e}") from e

    def get_all_relationships(self) -> List[DocumentRelationship]:
        """Retrieves all document relationships from the database."""
        self.logger.debug("Getting all document relationships from database.")
        try:
            with self.db_manager.get_session() as session:
                all_orms = session.query(DocRelationshipORM).all()
                results = [self._convert_orm_to_relationship(orm) for orm in all_orms]
                self.logger.debug(f"Retrieved {len(results)} relationships.")
                return results
        except Exception as e:
            self.logger.error(f"Error getting all relationships: {e}", exc_info=True)
            raise RepositoryError(f"Error getting all relationships: {e}") from e

    def get_relationships_by_source(self, source_document: str) -> List[DocumentRelationship]:
        """Retrieves all relationships originating from a specific source document."""
        self.logger.debug(f"Getting relationships by source: {source_document}")
        try:
            with self.db_manager.get_session() as session:
                orms = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.source_document == source_document
                ).all()
                results = [self._convert_orm_to_relationship(orm) for orm in orms]
                self.logger.debug(f"Found {len(results)} relationships for source: {source_document}")
                return results
        except Exception as e:
            self.logger.error(f"Error getting relationships for source {source_document}: {e}", exc_info=True)
            raise RepositoryError(f"Error getting relationships for source {source_document}: {e}") from e

    def get_relationships_by_target(self, target_document: str) -> List[DocumentRelationship]:
        """Retrieves all relationships pointing to a specific target document."""
        self.logger.debug(f"Getting relationships by target: {target_document}")
        try:
            with self.db_manager.get_session() as session:
                orms = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.target_document == target_document
                ).all()
                results = [self._convert_orm_to_relationship(orm) for orm in orms]
                self.logger.debug(f"Found {len(results)} relationships for target: {target_document}")
                return results
        except Exception as e:
            self.logger.error(f"Error getting relationships for target {target_document}: {e}", exc_info=True)
            raise RepositoryError(f"Error getting relationships for target {target_document}: {e}") from e

    def delete_relationships_for_document(self, document_path: str) -> int:
        """
        Deletes all relationships where the given document is either the source or the target.

        Args:
            document_path: The path of the document whose relationships should be deleted.

        Returns:
            The total number of relationships deleted.

        Raises:
            RepositoryError: If deletion fails.
        """
        self.logger.debug(f"Deleting all relationships involving document: {document_path}")
        deleted_count = 0
        try:
            with self.db_manager.get_session() as session:
                # Delete outgoing relationships
                deleted_outgoing = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.source_document == document_path
                ).delete(synchronize_session=False) # Use False for potentially better performance

                # Delete incoming relationships
                deleted_incoming = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.target_document == document_path
                ).delete(synchronize_session=False)

                session.flush() # Apply deletions
                deleted_count = (deleted_outgoing or 0) + (deleted_incoming or 0)
                self.logger.info(f"Deleted {deleted_count} relationships involving document: {document_path}")
                return deleted_count
        except Exception as e:
            self.logger.error(f"Error deleting relationships for document {document_path}: {e}", exc_info=True)
            raise RepositoryError(f"Error deleting relationships for document {document_path}: {e}") from e


    def _convert_orm_to_relationship(self, orm: DocRelationshipORM) -> DocumentRelationship:
        """Converts a DocRelationshipORM object to a DocumentRelationship dataclass."""
        try:
            metadata_dict = json.loads(orm.metadata) if orm.metadata else {}
        except json.JSONDecodeError:
            self.logger.warning(f"Could not decode metadata JSON for relationship ID {orm.id}. Using empty dict.")
            metadata_dict = {}

        return DocumentRelationship(
            id=str(orm.id),
            source_document=orm.source_document,
            target_document=orm.target_document,
            relationship_type=orm.relationship_type,
            topic=orm.topic,
            scope=orm.scope,
            metadata=metadata_dict,
            created_at=orm.created_at.replace(tzinfo=timezone.utc) if orm.created_at else None, # Assume UTC if not timezone aware
            updated_at=orm.updated_at.replace(tzinfo=timezone.utc) if orm.updated_at else None
        )
