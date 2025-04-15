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
# Implements the MetadataCacheInterface class, which serves as the primary public
# interface for interacting with the in-memory metadata cache. It coordinates the
# underlying storage, indexing, querying, eviction, and database synchronization
# components to provide a unified caching service.
###############################################################################
# [Source file design principles]
# - Facade pattern: Provides a simplified interface to the complex cache subsystem.
# - Coordinates interactions between storage, indexer, querier, evictor, and synchronizer.
# - Handles cache logic like hit/miss processing, triggering eviction, and recording access.
# - Exposes methods for getting, querying, updating, removing, clearing, and syncing data.
# - Includes basic statistics tracking (hits, misses, counts, etc.).
# - Ensures thread safety for all cache operations using an RLock.
# - Design Decision: Facade Interface (2025-04-15)
#   * Rationale: Simplifies usage for other components by hiding the internal complexity of the cache subsystem (storage, indexing, eviction, sync).
#   * Alternatives considered: Exposing individual cache components (increases coupling).
###############################################################################
# [Source file constraints]
# - Depends on all other components within the `memory_cache` package.
# - Requires instances of its dependencies (storage, indexer, etc.) to be injected.
# - Assumes configuration is provided for underlying components (like eviction).
# - Performance relies on the efficiency of the underlying components.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_memory_cache.md
# - All other files in src/dbp/memory_cache/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:00:00Z : Initial creation of MetadataCacheInterface by CodeAssistant
# * Implemented facade methods coordinating storage, indexing, querying, eviction, and sync. Added stats tracking.
###############################################################################

import logging
import threading
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone

# Assuming necessary imports from sibling modules and other packages
try:
    from .storage import CacheStorage
    from .index_manager import IndexManager
    from .eviction import EvictionStrategy # Base class, specific strategy injected
    from .query import QueryEngine, MetadataQuery
    from .synchronizer import DatabaseSynchronizer, DatabaseSyncError
    from ..metadata_extraction.data_structures import FileMetadata
    # Import config type if defined, else use Any
    # from ..config import AppConfig # Example
    Config = Any
except ImportError as e:
    logging.getLogger(__name__).error(f"MetadataCacheInterface ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    CacheStorage = object
    IndexManager = object
    EvictionStrategy = object
    QueryEngine = object
    MetadataQuery = object
    DatabaseSynchronizer = object
    FileMetadata = object
    Config = object
    DatabaseSyncError = Exception


logger = logging.getLogger(__name__)

class MetadataCacheInterface:
    """
    Provides the main public interface for interacting with the in-memory metadata cache.
    Coordinates storage, indexing, querying, eviction, and database synchronization.
    """

    def __init__(
        self,
        index_manager: IndexManager,
        storage: CacheStorage,
        query_engine: QueryEngine,
        db_sync: DatabaseSynchronizer,
        eviction_strategy: EvictionStrategy,
        config: Config, # Expecting the cache-specific part of the config
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initializes the MetadataCacheInterface.

        Args:
            index_manager: Instance of IndexManager.
            storage: Instance of CacheStorage.
            query_engine: Instance of QueryEngine.
            db_sync: Instance of DatabaseSynchronizer.
            eviction_strategy: Instance of a concrete EvictionStrategy (e.g., LRU, LFU).
            config: Configuration object for the memory cache component.
            logger_override: Optional logger instance.
        """
        self.index_manager = index_manager
        self.storage = storage
        self.query_engine = query_engine
        self.db_sync = db_sync
        self.eviction_strategy = eviction_strategy
        self.config = config # Store relevant config section
        self.logger = logger_override or logger
        self._lock = threading.RLock() # Lock for coordinating operations

        # Statistics tracking
        self._stats: Dict[str, Any] = {
            "hits": 0,
            "misses": 0,
            "updates": 0, # Includes additions
            "removals": 0, # Explicit removals
            "evictions": 0,
            "db_lookups": 0, # Cache misses that required DB lookup
            "db_lookup_hits": 0, # DB lookups that found data
            "last_sync_time": None,
            "last_sync_duration": None,
            "items_count": 0, # Current item count
        }
        self.logger.debug("MetadataCacheInterface initialized.")

    def get_metadata(self, file_path: str, project_id: int) -> Optional[FileMetadata]:
        """
        Retrieves metadata for a specific file path.
        Checks the cache first, then falls back to the database if not found.

        Args:
            file_path: The absolute path of the file.
            project_id: The ID of the project the file belongs to (for DB lookup).

        Returns:
            The FileMetadata object if found in cache or database, otherwise None.
        """
        with self._lock:
            self.logger.debug(f"Attempting to get metadata for: {file_path}")
            # 1. Check cache
            metadata = self.storage.get(file_path)

            if metadata:
                # Cache hit
                self._stats["hits"] += 1
                self.eviction_strategy.record_access(file_path)
                self.logger.debug(f"Cache hit for: {file_path}")
                return metadata
            else:
                # Cache miss
                self.logger.debug(f"Cache miss for: {file_path}. Checking database.")
                self._stats["misses"] += 1
                self._stats["db_lookups"] += 1

                # 2. Fallback to database
                try:
                    metadata_from_db = self.db_sync.get_metadata_from_db(file_path, project_id)
                except Exception as e:
                     # Log error but don't let DB error break cache get operation
                     self.logger.error(f"Error during database fallback lookup for {file_path}: {e}", exc_info=True)
                     return None # Return None if DB lookup fails

                if metadata_from_db:
                    # Found in DB, add to cache
                    self.logger.info(f"Metadata found in database for {file_path}. Adding to cache.")
                    self._stats["db_lookup_hits"] += 1
                    # Use internal method to store and handle eviction if needed
                    self._store_metadata(metadata_from_db)
                    return metadata_from_db
                else:
                    # Not found in DB either
                    self.logger.debug(f"Metadata not found in database for: {file_path}")
                    return None

    def query(self, query: MetadataQuery) -> List[FileMetadata]:
        """
        Executes a query against the cached metadata using the QueryEngine.

        Args:
            query: A MetadataQuery object specifying search criteria.

        Returns:
            A list of matching FileMetadata objects found in the cache.
        """
        with self._lock:
            self.logger.debug(f"Executing cache query: {query.__dict__}")
            # Delegate to QueryEngine
            results = self.query_engine.execute_query(query)
            # Record access for all returned items to update eviction strategy
            for metadata in results:
                 self.eviction_strategy.record_access(metadata.path)
            return results

    def update(self, metadata: FileMetadata):
        """
        Adds or updates a FileMetadata object in the cache and its indexes.
        Also triggers eviction if the cache exceeds its maximum size.

        Args:
            metadata: The FileMetadata object to add or update.
        """
        if not isinstance(metadata, FileMetadata) or not metadata.path:
             self.logger.warning(f"Attempted to update cache with invalid metadata: {metadata}")
             return
        with self._lock:
            self.logger.debug(f"Updating cache with metadata for: {metadata.path}")
            self._stats["updates"] += 1
            # Use internal method to handle storage, indexing, and eviction
            self._store_metadata(metadata)

    def remove(self, file_path: str):
        """
        Removes metadata for a specific file path from the cache and indexes.

        Args:
            file_path: The absolute path of the file to remove.
        """
        with self._lock:
            self.logger.debug(f"Removing metadata from cache for: {file_path}")
            if self.storage.contains(file_path):
                self.storage.remove(file_path)
                self.index_manager.remove_from_indexes(file_path)
                self.eviction_strategy.remove_key(file_path) # Notify eviction strategy
                self._stats["removals"] += 1
                self._update_item_count_stat() # Update count stat
                self.logger.info(f"Removed metadata for {file_path} from cache.")
            else:
                 self.logger.debug(f"Path not found in cache for removal: {file_path}")

    def clear(self):
        """Clears all items from the cache, indexes, and eviction tracking."""
        with self._lock:
            self.logger.info("Clearing all cache data...")
            self.storage.clear()
            self.index_manager.clear_indexes()
            self.eviction_strategy.clear()
            self._update_item_count_stat() # Reset count
            # Reset relevant stats
            self._stats["hits"] = 0
            self._stats["misses"] = 0
            self._stats["updates"] = 0
            self._stats["removals"] = 0
            self._stats["evictions"] = 0
            self._stats["db_lookups"] = 0
            self._stats["db_lookup_hits"] = 0
            self.logger.info("Cache cleared successfully.")

    def synchronize_with_database(self, project_id: int, full_sync: bool = False):
        """
        Triggers synchronization between the cache and the database.

        Args:
            project_id: The ID of the project to synchronize.
            full_sync: If True, performs a full reload from the database, clearing
                       the cache first. If False (default), performs an incremental sync.
        """
        with self._lock:
            start_time = time.monotonic()
            self.logger.info(f"Starting database synchronization (Full sync: {full_sync})...")
            try:
                if full_sync:
                    self.clear() # Clear cache before full sync
                    all_metadata = self.db_sync.perform_full_sync(project_id)
                    count = 0
                    for metadata in all_metadata:
                         self._store_metadata(metadata) # Add items back, handles eviction
                         count += 1
                    self.logger.info(f"Full sync complete. Loaded {count} items.")
                else:
                    # Perform incremental sync (logic is placeholder in synchronizer)
                    self.db_sync.perform_incremental_sync(self.storage, self.index_manager, project_id, self._stats["last_sync_time"])
                    self.logger.info("Incremental sync attempt complete.")

                self._stats["last_sync_time"] = datetime.now(timezone.utc)
                self._stats["last_sync_duration"] = time.monotonic() - start_time
                self._update_item_count_stat()

            except DatabaseSyncError as e:
                 self.logger.error(f"Database synchronization failed: {e}", exc_info=True)
            except Exception as e:
                 self.logger.error(f"Unexpected error during database synchronization: {e}", exc_info=True)


    def get_stats(self) -> Dict[str, Any]:
        """Returns a dictionary containing current cache statistics."""
        with self._lock:
            # Ensure item count is up-to-date
            self._update_item_count_stat()
            # Add index stats
            stats = self._stats.copy()
            stats["index_stats"] = self.index_manager.get_index_stats()
            return stats

    def _store_metadata(self, metadata: FileMetadata):
        """Internal helper to store metadata, manage indexes, and handle eviction."""
        # 1. Check if eviction is needed *before* adding the new item
        # Get max_items from config, provide a default
        max_items = int(self.config.get('memory_cache.max_items', 10000))
        current_count = self.storage.count()
        if current_count >= max_items:
            # Determine how many items to evict (at least 1)
            # Get batch size from config, provide a default
            batch_size = int(self.config.get('memory_cache.eviction_batch_size', 100))
            num_to_evict = max(1, min(batch_size, current_count // 10)) # Evict up to 10% or batch size
            self.logger.info(f"Cache limit ({max_items}) reached. Attempting to evict {num_to_evict} items.")

            evicted_keys = self.eviction_strategy.select_for_eviction(num_to_evict)
            self.logger.info(f"Evicting {len(evicted_keys)} items based on {type(self.eviction_strategy).__name__} strategy.")

            for key in evicted_keys:
                if self.storage.contains(key):
                    self.storage.remove(key)
                    self.index_manager.remove_from_indexes(key)
                    # No need to call eviction_strategy.remove_key here, as select_for_eviction handles it
                    self._stats["evictions"] += 1
                else:
                     self.logger.warning(f"Attempted to evict key '{key}' which was not found in storage.")


        # 2. Store the new/updated item in storage
        self.storage.put(metadata.path, metadata)

        # 3. Update indexes for the new/updated item
        self.index_manager.index_metadata(metadata)

        # 4. Record access for the newly added/updated item for eviction strategy
        self.eviction_strategy.record_access(metadata.path)

        # 5. Update item count statistic
        self._update_item_count_stat()

    def _update_item_count_stat(self):
         """Updates the item count statistic based on storage."""
         self._stats["items_count"] = self.storage.count()


    def shutdown(self):
        """Performs any necessary cleanup for the cache interface."""
        self.logger.info("Shutting down MetadataCacheInterface.")
        # Currently no specific actions needed here, as state is in memory
        # and dependencies are managed by the orchestrator.
        pass
