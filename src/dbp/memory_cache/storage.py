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
# Implements the CacheStorage class, providing the basic thread-safe dictionary-like
# storage mechanism for the in-memory metadata cache. It handles direct storage
# and retrieval of FileMetadata objects keyed by their file path.
###############################################################################
# [Source file design principles]
# - Simple dictionary-based storage (`path -> FileMetadata`).
# - Thread-safe operations using RLock.
# - Provides basic CRUD-like operations (get, put, remove, clear, contains).
# - Tracks the number of items currently stored.
# - Design Decision: Dictionary for Core Storage (2025-04-15)
#   * Rationale: Provides O(1) average time complexity for key-based lookups, suitable for path-based retrieval.
#   * Alternatives considered: More complex data structures (unnecessary for basic storage).
###############################################################################
# [Source file constraints]
# - Memory usage scales directly with the number and size of cached FileMetadata objects.
# - Does not handle indexing or eviction logic; those are delegated to other components.
# - Assumes keys (file paths) are unique strings.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- src/dbp/metadata_extraction/data_structures.py (Defines FileMetadata)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:57:00Z : Initial creation of CacheStorage class by CodeAssistant
# * Implemented basic thread-safe dictionary storage for metadata.
###############################################################################

import logging
import threading
from typing import Dict, Optional, Set, Any

# Assuming FileMetadata is defined elsewhere
try:
    from ..metadata_extraction.data_structures import FileMetadata
except ImportError:
    logging.getLogger(__name__).error("Failed to import FileMetadata for CacheStorage.")
    FileMetadata = object # Placeholder

logger = logging.getLogger(__name__)

class CacheStorage:
    """
    Provides thread-safe, dictionary-based storage for FileMetadata objects,
    keyed by their file path.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the CacheStorage.

        Args:
            config: Configuration object (currently unused by storage itself, but kept for consistency).
            logger_override: Optional logger instance.
        """
        self.config = config # May be used for future storage-related config
        self.logger = logger_override or logger
        self._cache: Dict[str, FileMetadata] = {}
        self._lock = threading.RLock() # Use RLock for thread safety
        self.logger.debug("CacheStorage initialized.")

    def get(self, key: str) -> Optional[FileMetadata]:
        """
        Retrieves a FileMetadata object from the cache by its path (key).

        Args:
            key: The file path.

        Returns:
            The cached FileMetadata object, or None if the key is not found.
        """
        with self._lock:
            return self._cache.get(key)

    def put(self, key: str, value: FileMetadata):
        """
        Stores or updates a FileMetadata object in the cache.

        Args:
            key: The file path.
            value: The FileMetadata object to store.
        """
        if not isinstance(value, FileMetadata):
             # Basic type check, relies on placeholder if import failed
             if FileMetadata is not object:
                  self.logger.warning(f"Attempted to store non-FileMetadata object for key '{key}'. Type: {type(value)}")
                  # Decide whether to raise error or just log and skip
                  return # Skip storing invalid type
             # else: pass if placeholder

        with self._lock:
            self.logger.debug(f"Storing metadata in cache for key: {key}")
            self._cache[key] = value

    def remove(self, key: str) -> bool:
        """
        Removes a FileMetadata object from the cache by its path (key).

        Args:
            key: The file path to remove.

        Returns:
            True if an item was removed, False if the key was not found.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Removed metadata from cache for key: {key}")
                return True
            else:
                self.logger.debug(f"Key not found in cache for removal: {key}")
                return False

    def clear(self):
        """Removes all items from the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cache storage cleared ({count} items removed).")

    def contains(self, key: str) -> bool:
        """
        Checks if a key (file path) exists in the cache.

        Args:
            key: The file path to check.

        Returns:
            True if the key exists, False otherwise.
        """
        with self._lock:
            return key in self._cache

    def count(self) -> int:
        """Returns the total number of items currently stored in the cache."""
        with self._lock:
            return len(self._cache)

    def get_all_keys(self) -> Set[str]:
        """Returns a set of all keys (file paths) currently in the cache."""
        with self._lock:
            return set(self._cache.keys())

    def get_all_items(self) -> Dict[str, FileMetadata]:
        """
        Returns a shallow copy of the entire cache dictionary.
        Use with caution on large caches due to memory implications.
        """
        with self._lock:
            return self._cache.copy()
