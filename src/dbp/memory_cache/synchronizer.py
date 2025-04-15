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
# Implements the DatabaseSynchronizer class, responsible for keeping the
# in-memory metadata cache consistent with the persistent database storage.
# It handles loading data from the database into the cache (full and incremental sync)
# and converting between database ORM objects and in-memory FileMetadata objects.
###############################################################################
# [Source file design principles]
# - Provides methods for full initial cache load and periodic incremental updates.
# - Interacts with database repositories to fetch data.
# - Converts database records (ORM objects) into FileMetadata Pydantic models.
# - Handles potential errors during database interaction or data conversion.
# - Encapsulates database synchronization logic, separating it from core cache operations.
# - Design Decision: Separate Synchronizer Class (2025-04-15)
#   * Rationale: Isolates database interaction logic related to cache consistency, making the cache component itself independent of the specific database implementation details.
#   * Alternatives considered: Embedding sync logic directly in the cache interface or component (mixes concerns).
###############################################################################
# [Source file constraints]
# - Depends heavily on the database component and its repositories.
# - Requires ORM models (e.g., FileMetadataORM) to be defined and accessible.
# - The efficiency of synchronization depends on database query performance and the volume of data.
# - Incremental sync logic requires a mechanism to identify changes in the database (e.g., timestamps, version numbers). Placeholder implementation provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - scratchpad/dbp_implementation_plan/plan_memory_cache.md
# - src/dbp/database/repositories.py
# - src/dbp/database/models.py (Assumed ORM models)
# - src/dbp/metadata_extraction/data_structures.py (FileMetadata)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:59:20Z : Initial creation of DatabaseSynchronizer class by CodeAssistant
# * Implemented basic structure for full/incremental sync and ORM conversion (placeholders).
###############################################################################

import logging
import threading
from typing import Optional, Any, List, Dict, Set
from datetime import datetime, timezone

# Assuming necessary imports
try:
    # Core component framework
    from ..core.component import Component # For type hinting db_component
    # Database access
    from ..database.database import DatabaseManager # For type hinting
    from ..database.repositories import DocumentRepository # Need specific repo
    # ORM Models (adjust import based on actual location)
    from ..database.models import Document as DocumentORM # Assuming ORM model name is Document
    # Metadata structure
    from ..metadata_extraction.data_structures import FileMetadata # Target data structure
    # Cache components for incremental sync interaction
    from .storage import CacheStorage
    from .index_manager import IndexManager
except ImportError as e:
    logging.getLogger(__name__).error(f"DatabaseSynchronizer ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    Component = object
    DatabaseManager = object
    DocumentRepository = object
    DocumentORM = object
    FileMetadata = object
    CacheStorage = object
    IndexManager = object

logger = logging.getLogger(__name__)

class DatabaseSyncError(Exception):
    """Custom exception for errors during database synchronization."""
    pass

class DatabaseSynchronizer:
    """
    Handles synchronization between the persistent database storage and the
    in-memory metadata cache.
    """

    def __init__(self, db_manager: DatabaseManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the DatabaseSynchronizer.

        Args:
            db_manager: An initialized DatabaseManager instance.
            logger_override: Optional logger instance.
        """
        self.db_manager = db_manager
        self.logger = logger_override or logger
        # Instantiate repositories needed for fetching data
        self.doc_repo = DocumentRepository(self.db_manager)
        # Add other repositories if needed for related data (functions, classes, etc.)
        self._lock = threading.RLock() # Lock for sync operations if needed
        self.logger.debug("DatabaseSynchronizer initialized.")

    def get_metadata_from_db(self, file_path: str, project_id: int) -> Optional[FileMetadata]:
        """
        Retrieves metadata for a specific file directly from the database.

        Args:
            file_path: The absolute path of the file.
            project_id: The ID of the project the file belongs to.

        Returns:
            A FileMetadata object if found, otherwise None.
        """
        self.logger.debug(f"Fetching metadata from DB for: {file_path} (Project: {project_id})")
        with self._lock:
            try:
                # Use the repository to get the ORM object
                # Assuming get_by_path needs project_id or handles context
                # doc_orm = self.doc_repo.get_by_path(file_path, project_id=project_id) # Ideal
                doc_orm = self.doc_repo.get_by_path(file_path) # Current repo implementation

                # Filter by project ID if necessary
                if doc_orm and doc_orm.project_id == project_id:
                    # Convert ORM object to FileMetadata Pydantic model
                    metadata = self._convert_orm_to_file_metadata(doc_orm)
                    self.logger.debug(f"Found metadata in DB for: {file_path}")
                    return metadata
                else:
                    if doc_orm:
                         self.logger.debug(f"Path {file_path} found in DB but for wrong project ({doc_orm.project_id})")
                    else:
                         self.logger.debug(f"Metadata not found in DB for: {file_path}")
                    return None
            except Exception as e:
                self.logger.error(f"Error fetching metadata from database for {file_path}: {e}", exc_info=True)
                # Raise a specific error or return None? Returning None for now.
                # raise DatabaseSyncError(f"Failed to fetch metadata for {file_path}") from e
                return None

    def perform_full_sync(self, project_id: int) -> List[FileMetadata]:
        """
        Performs a full load of all metadata for a given project from the database.
        Intended for initial cache population.

        Args:
            project_id: The ID of the project to load metadata for.

        Returns:
            A list of FileMetadata objects loaded from the database.
        """
        self.logger.info(f"Performing full metadata sync from database for project ID: {project_id}...")
        with self._lock:
            all_metadata = []
            try:
                # Use repository to get all documents for the project
                # Assuming list_by_project exists and works correctly
                all_docs_orm = self.doc_repo.list_by_project(project_id=project_id)
                self.logger.info(f"Retrieved {len(all_docs_orm)} document records from database.")

                for doc_orm in all_docs_orm:
                    try:
                        metadata = self._convert_orm_to_file_metadata(doc_orm)
                        if metadata:
                            all_metadata.append(metadata)
                    except Exception as e:
                        self.logger.error(f"Failed to convert ORM object for path {getattr(doc_orm, 'path', 'unknown')} to FileMetadata: {e}", exc_info=True)
                        # Continue processing other records

                self.logger.info(f"Successfully converted {len(all_metadata)} records for full sync.")
                return all_metadata

            except Exception as e:
                self.logger.error(f"Error during full database sync for project {project_id}: {e}", exc_info=True)
                raise DatabaseSyncError(f"Full database sync failed for project {project_id}") from e


    def perform_incremental_sync(self, storage: CacheStorage, index_manager: IndexManager, project_id: int, since: Optional[datetime] = None):
        """
        Performs an incremental synchronization, updating the cache with changes
        from the database since the last sync time.

        Args:
            storage: The CacheStorage instance to update.
            index_manager: The IndexManager instance to update.
            project_id: The ID of the project to sync.
            since: The timestamp of the last sync (optional). If None, might perform full sync or use a default cutoff.
        """
        self.logger.info(f"Performing incremental metadata sync from database for project {project_id} (since: {since})...")
        with self._lock:
            try:
                # --- Placeholder Logic ---
                # A real implementation would:
                # 1. Query the database for records created/updated since the 'since' timestamp for the given project_id.
                #    - This requires 'created_at' and 'updated_at' columns in the ORM models/tables.
                # 2. Query the database for records deleted since the 'since' timestamp (if using soft deletes or a deletion log).
                # 3. Convert updated/new ORM records to FileMetadata objects.
                # 4. Update the CacheStorage and IndexManager:
                #    - Add/update new/modified items.
                #    - Remove deleted items.

                self.logger.warning("Incremental sync logic is currently a placeholder.")

                # Example: Simulate fetching updated records (replace with actual DB query)
                # updated_docs_orm = self.doc_repo.get_updated_since(since, project_id=project_id)
                updated_docs_orm = [] # Placeholder

                updated_count = 0
                for doc_orm in updated_docs_orm:
                     try:
                          metadata = self._convert_orm_to_file_metadata(doc_orm)
                          if metadata:
                               storage.put(metadata.path, metadata)
                               index_manager.index_metadata(metadata) # Re-index updated item
                               updated_count += 1
                     except Exception as e:
                          self.logger.error(f"Failed to process updated record {getattr(doc_orm, 'path', 'unknown')} during sync: {e}")

                # Example: Simulate fetching deleted records (replace with actual DB query/logic)
                # deleted_paths = self.doc_repo.get_deleted_paths_since(since, project_id=project_id)
                deleted_paths = [] # Placeholder
                deleted_count = 0
                for path in deleted_paths:
                     if storage.contains(path):
                          storage.remove(path)
                          index_manager.remove_from_indexes(path)
                          deleted_count += 1

                self.logger.info(f"Incremental sync complete: {updated_count} items updated/added, {deleted_count} items removed.")
                # --- End Placeholder Logic ---

            except Exception as e:
                self.logger.error(f"Error during incremental database sync for project {project_id}: {e}", exc_info=True)
                # Don't raise, just log the error for incremental sync failure


    def _convert_orm_to_file_metadata(self, doc_orm: DocumentORM) -> Optional[FileMetadata]:
        """
        Converts a database ORM object (DocumentORM) into a FileMetadata Pydantic model.
        This requires knowledge of the ORM model's structure.

        Args:
            doc_orm: The SQLAlchemy ORM object representing a document.

        Returns:
            A corresponding FileMetadata object, or None if conversion fails.
        """
        if not doc_orm:
            return None

        self.logger.debug(f"Converting ORM object for path: {doc_orm.path}")
        try:
            # --- Placeholder Conversion Logic ---
            # This needs to map fields from the ORM model (doc_orm) defined in
            # src/dbp/database/models.py to the FileMetadata Pydantic model defined in
            # src/dbp/metadata_extraction/data_structures.py.
            # This includes handling nested structures like header sections, functions, classes.

            # Example (assuming ORM fields match Pydantic fields closely):
            header_sections = None # Placeholder - need to parse from ORM fields
            functions = [] # Placeholder - need to query/load related function ORM objects and convert
            classes = [] # Placeholder - need to query/load related class ORM objects and convert

            metadata = FileMetadata(
                path=doc_orm.path,
                language=getattr(doc_orm, 'language', None), # Use getattr for safety
                header_sections=header_sections, # Replace with actual conversion
                functions=functions,             # Replace with actual conversion
                classes=classes,               # Replace with actual conversion
                size_bytes=getattr(doc_orm, 'file_size', None),
                md5_digest=getattr(doc_orm, 'md5_digest', None),
                last_modified=getattr(doc_orm, 'last_modified', None),
                extraction_timestamp=getattr(doc_orm, 'updated_at', None) # Use updated_at as proxy?
            )
            # --- End Placeholder Conversion Logic ---

            return metadata
        except Exception as e:
            self.logger.error(f"Failed to convert ORM object for path {getattr(doc_orm, 'path', 'unknown')} to FileMetadata: {e}", exc_info=True)
            return None
