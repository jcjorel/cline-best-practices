# src/dbp/memory_cache/__init__.py

"""
In-Memory Cache package for the Documentation-Based Programming system.

Provides a fast, thread-safe cache for storing and retrieving processed
FileMetadata objects, reducing the need for repeated database lookups or
LLM extractions. Includes indexing, querying, and eviction mechanisms.

Key components:
- MemoryCacheComponent: The main component conforming to the core framework.
- MetadataCacheInterface: Facade providing the primary API for cache interaction.
- CacheStorage: Basic dictionary-based storage.
- IndexManager: Manages various indexes for efficient querying.
- QueryEngine: Executes queries against the indexes.
- EvictionStrategy: Base class for eviction logic (LRU, LFU implementations).
- DatabaseSynchronizer: Handles keeping the cache consistent with the database.
"""

# Expose key classes for easier import from the package level
from .storage import CacheStorage
from .index_manager import IndexManager
from .eviction import EvictionStrategy, LRUEvictionStrategy, LFUEvictionStrategy
from .query import QueryEngine, MetadataQuery
from .synchronizer import DatabaseSynchronizer, DatabaseSyncError
from .interface import MetadataCacheInterface
from .component import MemoryCacheComponent, ComponentNotInitializedError

__all__ = [
    "MemoryCacheComponent",
    "MetadataCacheInterface",
    "MetadataQuery",
    "CacheStorage",
    "IndexManager",
    "QueryEngine",
    "EvictionStrategy",
    "LRUEvictionStrategy",
    "LFUEvictionStrategy",
    "DatabaseSynchronizer",
    "DatabaseSyncError",
    "ComponentNotInitializedError",
]
