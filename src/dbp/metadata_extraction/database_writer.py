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
# Implements the DatabaseWriter class, responsible for persisting the processed
# FileMetadata object into the database. It interacts with the database
# repositories (e.g., DocumentRepository, FunctionRepository) to create or update
# records corresponding to the extracted metadata.
###############################################################################
# [Source file design principles]
# - Decouples metadata persistence logic from the extraction and processing steps.
# - Uses repository patterns for database interaction, abstracting direct ORM/SQL calls.
# - Handles the logic for checking if a document record exists and deciding whether
#   to create a new record or update an existing one.
# - Persists nested metadata structures (header sections, functions, classes)
#   by calling appropriate repository methods.
# - Includes error handling for database operations.
# - Design Decision: Separate Database Writer (2025-04-15)
#   * Rationale: Isolates database persistence logic, making the extraction service cleaner and improving testability of database interactions.
#   * Alternatives considered: Writing directly from ResultProcessor (mixes concerns), Writing from ExtractionService (increases service complexity).
###############################################################################
# [Source file constraints]
# - Depends on the database repositories (e.g., `DocumentRepository`) being available
#   and correctly implemented.
# - Requires an initialized `DatabaseManager` instance passed via the `db_component`.
# - Assumes the input `FileMetadata` object is valid and processed.
# - Database transaction management is handled by the repositories/DatabaseManager.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - src/dbp/metadata_extraction/data_structures.py
# - src/dbp/database/repositories.py # Depends on this module
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:53:15Z : Initial creation of DatabaseWriter class by CodeAssistant
# * Implemented logic to write FileMetadata using database repositories.
###############################################################################

import logging
from typing import Optional, Any

# Assuming data_structures and database repositories are accessible
try:
    from .data_structures import FileMetadata, HeaderSections, FunctionMetadata, ClassMetadata
    # Import necessary repositories from the database package
    from ..database.repositories import (
        DocumentRepository, FunctionRepository, ClassRepository,
        ChangeRecordRepository, DesignDecisionRepository
        # Add other repositories if needed (e.g., ProjectRepository if project context is managed here)
    )
    from ..database.database import DatabaseManager # Needed for type hint, though not directly used
    # Import the actual DB Component type if available, otherwise use Any
    from ..core.component import Component # Use Component protocol/base
except ImportError as e:
    logging.getLogger(__name__).error(f"DatabaseWriter ImportError: {e}. Check package structure.", exc_info=True)
    # Define placeholders
    FileMetadata = object
    HeaderSections = object
    FunctionMetadata = object
    ClassMetadata = object
    DocumentRepository = object
    FunctionRepository = object
    ClassRepository = object
    ChangeRecordRepository = object
    DesignDecisionRepository = object
    DatabaseManager = object
    Component = object


logger = logging.getLogger(__name__)

class DatabaseWriteError(Exception):
    """Custom exception for errors during database writing."""
    pass

class DatabaseWriter:
    """
    Handles writing processed FileMetadata objects to the database
    using the defined repository classes.
    """

    def __init__(self, db_manager: DatabaseManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the DatabaseWriter.

        Args:
            db_manager: An initialized DatabaseManager instance providing access to sessions.
            logger_override: Optional logger instance.
        """
        self.db_manager = db_manager
        self.logger = logger_override or logger
        # Instantiate repositories needed
        # It might be better if these were injected or retrieved from a central place,
        # but direct instantiation is simpler for now.
        self.doc_repo = DocumentRepository(self.db_manager)
        self.func_repo = FunctionRepository(self.db_manager)
        self.class_repo = ClassRepository(self.db_manager)
        self.change_repo = ChangeRecordRepository(self.db_manager)
        self.design_repo = DesignDecisionRepository(self.db_manager)
        # self.project_repo = ProjectRepository(self.db_manager) # If needed
        self.logger.debug("DatabaseWriter initialized.")

    def write(self, metadata: FileMetadata, project_id: int) -> bool:
        """
        Writes the provided FileMetadata to the database for a specific project.
        It checks if a document record exists and either updates it or creates a new one.

        Args:
            metadata: The FileMetadata object to persist.
            project_id: The ID of the project this metadata belongs to.

        Returns:
            True if the write operation was successful, False otherwise.

        Raises:
            DatabaseWriteError: If a critical error occurs during the database operation.
        """
        if not isinstance(metadata, FileMetadata):
            self.logger.error("Invalid metadata object provided to DatabaseWriter.")
            return False
        if not project_id:
             self.logger.error("Invalid project_id provided to DatabaseWriter.")
             return False


        self.logger.info(f"Writing metadata to database for: {metadata.path} (Project ID: {project_id})")

        try:
            # Check if document exists by path within the project
            # Note: DocumentRepository needs modification if project_id isn't directly filterable
            # Assuming get_by_path implicitly handles project context or needs project_id
            # Let's modify the call assuming get_by_path needs project_id (better design)
            # existing_doc = self.doc_repo.get_by_path(metadata.path, project_id=project_id) # Ideal
            existing_doc = self.doc_repo.get_by_path(metadata.path) # Current repo implementation

            # Filter further by project_id if necessary
            if existing_doc and existing_doc.project_id != project_id:
                 self.logger.warning(f"Document path {metadata.path} found but belongs to different project ({existing_doc.project_id}). Treating as new for project {project_id}.")
                 existing_doc = None # Treat as non-existent for this project

            if existing_doc:
                # --- Update Existing Document ---
                self.logger.debug(f"Document exists (ID: {existing_doc.id}). Updating record.")
                # Prepare update data dictionary
                update_data = {
                    "language": metadata.language,
                    "size_bytes": metadata.size_bytes,
                    "md5_digest": metadata.md5_digest,
                    "last_modified": metadata.last_modified,
                    # Update header sections (assuming repo handles nested update or takes dict)
                    "header_data": metadata.header_sections.dict() if metadata.header_sections else {}
                    # Add other top-level fields from FileMetadata if needed
                }
                success = self.doc_repo.update(existing_doc.id, update_data)
                if not success:
                     raise DatabaseWriteError(f"Failed to update document record for {metadata.path}")

                doc_id = existing_doc.id
                # Update/replace nested structures (functions, classes, etc.)
                # Repositories handle the bulk create/update logic (delete old, add new)
                self.func_repo.bulk_create_or_update(doc_id, [f.dict() for f in metadata.functions or []])
                self.class_repo.bulk_create_or_update(doc_id, [c.dict() for c in metadata.classes or []])
                # Assuming header sections contain change history and design decisions
                if metadata.header_sections:
                     self.change_repo.bulk_create(doc_id, [cr.dict() for cr in metadata.header_sections.change_history or []])
                     # How are design decisions stored/linked? Assuming they are part of header for now.
                     # self.design_repo.bulk_create_or_update(doc_id, ...) # Needs clarification

            else:
                # --- Create New Document ---
                self.logger.debug(f"Document does not exist. Creating new record for project {project_id}.")
                # Prepare header data dict
                header_data_dict = metadata.header_sections.dict() if metadata.header_sections else {}

                new_doc = self.doc_repo.create(
                    path=metadata.path,
                    document_type="Code", # Assuming default, might need refinement
                    project_id=project_id,
                    last_modified=metadata.last_modified or datetime.now(timezone.utc),
                    file_size=metadata.size_bytes or 0,
                    md5_digest=metadata.md5_digest or "",
                    header_data=header_data_dict
                )
                if not new_doc:
                    raise DatabaseWriteError(f"Failed to create document record for {metadata.path}")

                doc_id = new_doc.id
                # Create nested structures
                self.func_repo.bulk_create_or_update(doc_id, [f.dict() for f in metadata.functions or []])
                self.class_repo.bulk_create_or_update(doc_id, [c.dict() for c in metadata.classes or []])
                if metadata.header_sections:
                     self.change_repo.bulk_create(doc_id, [cr.dict() for cr in metadata.header_sections.change_history or []])
                     # self.design_repo.bulk_create_or_update(doc_id, ...)

            self.logger.info(f"Successfully wrote metadata for {metadata.path} (Doc ID: {doc_id})")
            return True

        except Exception as e:
            self.logger.error(f"Database write failed for {metadata.path}: {e}", exc_info=True)
            # Don't raise DatabaseWriteError from here, let the service handle it
            # raise DatabaseWriteError(f"Failed to write metadata for {metadata.path}: {e}") from e
            return False
