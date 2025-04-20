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
# Defines the DocumentRepository class for managing Document entities in the
# database, providing CRUD operations and specialized queries.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for common CRUD operations on documents.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Document model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:00:55Z : Created document_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted DocumentRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Document entity operations.
"""

import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Document
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Document


logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    """Repository for managing Document entities."""

    def create(self, path: str, document_type: str, project_id: int, last_modified: datetime.datetime, file_size: int = 0, md5_digest: str = None, content: str = None, header_data: dict = None) -> Document | None:
        """
        [Function intent]
        Creates a new document record in the database.
        
        [Implementation details]
        Builds a Document object with provided parameters and adds it to the database.
        Handles header data by extracting specific fields from the provided dictionary.
        
        [Design principles]
        Uses session context manager for proper transaction handling.
        Returns created object for immediate use.
        
        Args:
            path: Full path to the document file.
            document_type: Type of the document (e.g., 'Code', 'Markdown').
            project_id: ID of the project this document belongs to.
            last_modified: The last modified timestamp of the file.
            file_size: Size of the file in bytes.
            md5_digest: MD5 hash of the file content.
            content: Optional file content to store.
            header_data: Optional dictionary with extracted header sections.

        Returns:
            The created Document object or None if creation failed.
        """
        operation = "create_document"
        logger.debug(f"{operation}: Creating document for path '{path}' in project {project_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = Document(
                    path=path,
                    type=document_type,
                    project_id=project_id,
                    last_modified=last_modified,
                    file_size=file_size,
                    md5_digest=md5_digest or "",
                    content=content
                )
                if header_data:
                    document.intent = header_data.get('intent')
                    # Assuming lists are stored as delimited strings or JSON
                    document.design_principles = str(header_data.get('designPrinciples', []))
                    document.constraints = str(header_data.get('constraints', []))
                    document.reference_documentation = str(header_data.get('referenceDocumentation', []))

                session.add(document)
                session.flush() # Flush to get the ID if needed immediately
                logger.info(f"{operation}: Document created with ID {document.id} for path '{path}'.")
                # Eager load relationships if needed, though usually not required on create
                # session.refresh(document, attribute_names=['project'])
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None # Explicitly return None on failure

    def get_by_path(self, path: str) -> Document | None:
        """
        [Function intent]
        Retrieves a document by its full path.
        
        [Implementation details]
        Performs a database query filtering by the path field.
        
        [Design principles]
        Simple read operation with proper error handling.
        
        Args:
            path: The full path of the document file.

        Returns:
            The Document object if found, otherwise None.
        """
        operation = "get_document_by_path"
        logger.debug(f"{operation}: Getting document for path '{path}'.")
        try:
            with self.db_manager.get_session() as session:
                # Consider adding options like joinedload for relationships if frequently accessed
                document = session.query(Document).filter(Document.path == path).first()
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id} for path '{path}'.")
                else:
                    logger.debug(f"{operation}: No document found for path '{path}'.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_id(self, document_id: int) -> Document | None:
        """
        [Function intent]
        Retrieves a document by its ID.
        
        [Implementation details]
        Uses SQLAlchemy's get() method for primary key lookup.
        
        [Design principles]
        Simple read operation with proper error handling.
        
        Args:
            document_id: The unique ID of the document.

        Returns:
            The Document object if found, otherwise None.
        """
        operation = "get_document_by_id"
        logger.debug(f"{operation}: Getting document for ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id}.")
                else:
                    logger.debug(f"{operation}: No document found for ID {document_id}.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def update(self, document_id: int, update_data: dict) -> bool:
        """
        [Function intent]
        Updates an existing document record.
        
        [Implementation details]
        Fetches the document by ID and applies the updates from the update_data dictionary.
        Special handling for the header_data nested dictionary.
        
        [Design principles]
        Validates document existence before update.
        Returns boolean to indicate success/failure.
        
        Args:
            document_id: The ID of the document to update.
            update_data: A dictionary containing fields to update (e.g., 'file_size', 'md5_digest', 'header_data').

        Returns:
            True if the update was successful, False otherwise.
        """
        operation = "update_document"
        logger.debug(f"{operation}: Updating document ID {document_id} with data: {list(update_data.keys())}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if not document:
                    logger.warning(f"{operation}: Document ID {document_id} not found for update.")
                    return False

                # Update fields provided in update_data
                for key, value in update_data.items():
                    if hasattr(document, key):
                        setattr(document, key, value)
                    elif key == 'header_data' and isinstance(value, dict):
                         # Handle nested header data update
                         header_data = value
                         document.intent = header_data.get('intent', document.intent)
                         document.design_principles = str(header_data.get('designPrinciples', document.design_principles))
                         document.constraints = str(header_data.get('constraints', document.constraints))
                         document.reference_documentation = str(header_data.get('referenceDocumentation', document.reference_documentation))
                    else:
                        logger.warning(f"{operation}: Invalid field '{key}' provided for Document update.")

                # Always update the last_modified timestamp on any update
                document.last_modified = datetime.datetime.now()

                session.flush() # Commit happens at the end of the 'with' block
                logger.info(f"{operation}: Document ID {document_id} updated successfully.")
                return True
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def delete(self, document_id: int) -> bool:
        """
        [Function intent]
        Deletes a document record by its ID.
        
        [Implementation details]
        Fetches the document by ID and removes it from the database.
        
        [Design principles]
        Validates document existence before deletion.
        Returns boolean to indicate success/failure.
        
        Args:
            document_id: The ID of the document to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        operation = "delete_document"
        logger.debug(f"{operation}: Deleting document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    session.delete(document)
                    session.flush() # Commit happens at the end of the 'with' block
                    logger.info(f"{operation}: Document ID {document_id} deleted successfully.")
                    return True
                else:
                    logger.warning(f"{operation}: Document ID {document_id} not found for deletion.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def list_by_project(self, project_id: int, document_type: str = None) -> list[Document]:
        """
        [Function intent]
        Lists documents belonging to a specific project, optionally filtered by type.
        
        [Implementation details]
        Queries documents filtered by project_id and optionally by document_type.
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        
        Args:
            project_id: The ID of the project.
            document_type: Optional document type to filter by.

        Returns:
            A list of Document objects.
        """
        operation = "list_documents_by_project"
        filter_msg = f" for project ID {project_id}" + (f" and type '{document_type}'" if document_type else "")
        logger.debug(f"{operation}: Listing documents{filter_msg}.")
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Document).filter(Document.project_id == project_id)
                if document_type:
                    query = query.filter(Document.type == document_type)
                documents = query.all()
                logger.debug(f"{operation}: Found {len(documents)} documents{filter_msg}.")
                return documents
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return [] # Return empty list on error

    def find_by_md5(self, md5_digest: str, project_id: int) -> Document | None:
        """
        [Function intent]
        Finds a document by its MD5 digest within a specific project.
        
        [Implementation details]
        Queries documents filtered by md5_digest and project_id.
        
        [Design principles]
        Specialized query method for fast content-based lookups.
        
        Args:
            md5_digest: The MD5 hash of the document content.
            project_id: The ID of the project to search within.

        Returns:
            The Document object if found, otherwise None.
        """
        operation = "find_document_by_md5"
        logger.debug(f"{operation}: Searching for MD5 '{md5_digest}' in project {project_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).filter(
                    Document.project_id == project_id,
                    Document.md5_digest == md5_digest
                ).first()
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id} with MD5 '{md5_digest}'.")
                else:
                    logger.debug(f"{operation}: No document found with MD5 '{md5_digest}'.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None
