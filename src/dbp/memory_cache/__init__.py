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
# Memory Cache package for the Documentation-Based Programming system.
# Implements in-memory caching for metadata and analysis results.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


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
