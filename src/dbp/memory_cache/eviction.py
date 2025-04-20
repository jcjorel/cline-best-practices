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
# Defines cache eviction strategies (LRU - Least Recently Used, LFU - Least
# Frequently Used) for the in-memory metadata cache. Provides an abstract base
# class and concrete implementations to manage cache size when the maximum
# number of items is reached.
###############################################################################
# [Source file design principles]
# - Uses an Abstract Base Class (ABC) for the eviction strategy interface.
# - Implements standard LRU and LFU algorithms.
# - Tracks access times (LRU) or frequencies (LFU) for cached items.
# - Provides a method to select items for eviction based on the chosen strategy.
# - Ensures thread safety for accessing tracking data structures.
# - Design Decision: Pluggable Eviction Strategies (2025-04-15)
#   * Rationale: Allows easy configuration and extension with different eviction algorithms in the future without changing the core cache logic.
#   * Alternatives considered: Hardcoding a single strategy (less flexible).
###############################################################################
# [Source file constraints]
# - Requires accurate tracking of cache item access via `record_access`.
# - Performance of eviction selection depends on the number of items and the chosen strategy (sorting can be O(N log N)).
# - LFU might require handling frequency ties (e.g., using LRU as a tie-breaker, not implemented here for simplicity).
# - Assumes keys (file paths) are strings.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:58:10Z : Initial creation of eviction strategy classes by CodeAssistant
# * Implemented EvictionStrategy ABC, LRUEvictionStrategy, and LFUEvictionStrategy.
###############################################################################

import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class EvictionStrategy(ABC):
    """
    Abstract base class for cache eviction strategies. Defines the interface
    for recording item access and selecting items to evict when the cache is full.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the eviction strategy.

        Args:
            config: Configuration object (may contain strategy-specific settings).
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.logger = logger_override or logger
        self.logger.debug(f"{self.__class__.__name__} initialized.")

    @abstractmethod
    def record_access(self, key: str):
        """
        Records that a cache item with the given key has been accessed.
        This method is called by the cache whenever an item is retrieved (cache hit)
        or potentially when it's added/updated.

        Args:
            key: The key (file path) of the accessed cache item.
        """
        pass

    @abstractmethod
    def select_for_eviction(self, count: int) -> List[str]:
        """
        Selects a specified number of cache keys to be evicted based on the strategy.

        Args:
            count: The maximum number of keys to select for eviction.

        Returns:
            A list of keys (file paths) recommended for eviction.
            The list may contain fewer items than requested if the cache is smaller.
        """
        pass

    @abstractmethod
    def remove_key(self, key: str):
        """
        Removes tracking information for a key that has been explicitly removed
        from the cache (not via eviction).

        Args:
            key: The key (file path) that was removed.
        """
        pass

    @abstractmethod
    def clear(self):
        """Clears all tracking information held by the eviction strategy."""
        pass


class LRUEvictionStrategy(EvictionStrategy):
    """
    Implements the Least Recently Used (LRU) cache eviction strategy.
    Evicts items that haven't been accessed for the longest time.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        super().__init__(config, logger_override)
        # Dictionary storing the last access timestamp for each key
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock() # Protect access to _access_times

    def record_access(self, key: str):
        """Updates the last access time for the given key."""
        with self._lock:
            self._access_times[key] = time.monotonic() # Use monotonic clock for recency
            # self.logger.debug(f"LRU access recorded for key: {key}")

    def select_for_eviction(self, count: int) -> List[str]:
        """Selects the `count` least recently used keys for eviction."""
        with self._lock:
            if not self._access_times or count <= 0:
                return []

            # Sort keys based on their access time (ascending order - oldest first)
            # This is O(N log N) where N is the number of items tracked.
            # For very large caches, more efficient LRU implementations exist (e.g., using OrderedDict or doubly linked list).
            sorted_keys = sorted(
                self._access_times.keys(),
                key=lambda k: self._access_times.get(k, 0.0) # Use get with default for safety
            )

            # Select the items to evict
            num_to_evict = min(count, len(sorted_keys))
            keys_to_evict = sorted_keys[:num_to_evict]

            self.logger.info(f"LRU selecting {len(keys_to_evict)} items for eviction: {keys_to_evict[:5]}...") # Log first few

            # Remove the evicted keys from our tracking
            for key in keys_to_evict:
                if key in self._access_times:
                    del self._access_times[key]

            return keys_to_evict

    def remove_key(self, key: str):
        """Removes tracking for an explicitly removed key."""
        with self._lock:
            if key in self._access_times:
                del self._access_times[key]
                # self.logger.debug(f"LRU tracking removed for key: {key}")

    def clear(self):
        """Clears all LRU tracking data."""
        with self._lock:
            self._access_times.clear()
            self.logger.debug("LRU tracking cleared.")


class LFUEvictionStrategy(EvictionStrategy):
    """
    Implements the Least Frequently Used (LFU) cache eviction strategy.
    Evicts items that have been accessed the fewest number of times.
    Note: This simple implementation doesn't handle frequency ties (e.g., using LRU as tie-breaker).
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        super().__init__(config, logger_override)
        # Dictionary storing the access frequency count for each key
        self._access_counts: Dict[str, int] = {}
        self._lock = threading.RLock() # Protect access to _access_counts

    def record_access(self, key: str):
        """Increments the access count for the given key."""
        with self._lock:
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            # self.logger.debug(f"LFU access recorded for key: {key}, count: {self._access_counts[key]}")

    def select_for_eviction(self, count: int) -> List[str]:
        """Selects the `count` least frequently used keys for eviction."""
        with self._lock:
            if not self._access_counts or count <= 0:
                return []

            # Sort keys based on their access count (ascending order - least frequent first)
            # This is O(N log N). More complex LFU implementations offer better performance.
            sorted_keys = sorted(
                self._access_counts.keys(),
                key=lambda k: self._access_counts.get(k, 0) # Use get with default for safety
            )

            # Select the items to evict
            num_to_evict = min(count, len(sorted_keys))
            keys_to_evict = sorted_keys[:num_to_evict]

            self.logger.info(f"LFU selecting {len(keys_to_evict)} items for eviction: {keys_to_evict[:5]}...") # Log first few

            # Remove the evicted keys from our tracking
            for key in keys_to_evict:
                if key in self._access_counts:
                    del self._access_counts[key]

            return keys_to_evict

    def remove_key(self, key: str):
        """Removes tracking for an explicitly removed key."""
        with self._lock:
            if key in self._access_counts:
                del self._access_counts[key]
                # self.logger.debug(f"LFU tracking removed for key: {key}")

    def clear(self):
        """Clears all LFU tracking data."""
        with self._lock:
            self._access_counts.clear()
            self.logger.debug("LFU tracking cleared.")
