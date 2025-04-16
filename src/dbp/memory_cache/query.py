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
# Implements the query mechanism for the in-memory metadata cache. Defines the
# `MetadataQuery` class to represent search criteria and the `QueryEngine` class
# to execute queries against the indexes managed by `IndexManager`.
###############################################################################
# [Source file design principles]
# - `MetadataQuery` provides a structured way to specify search filters.
# - `QueryEngine` leverages the pre-built indexes for efficient lookups.
# - Combines results from multiple index lookups using set intersections.
# - Supports filtering by path pattern using regular expressions.
# - Handles retrieval of actual `FileMetadata` objects from storage based on matched paths.
# - Includes optional result limiting.
# - Design Decision: Index-Based Querying (2025-04-15)
#   * Rationale: Significantly faster than iterating through all cached items, especially for large caches. Enables targeted lookups.
#   * Alternatives considered: Full cache scan (inefficient), External search engine integration (overkill for in-memory cache).
###############################################################################
# [Source file constraints]
# - Depends on `IndexManager` for index lookups and `CacheStorage` for retrieving full metadata.
# - Query performance depends on the selectivity of the index keys used.
# - Path pattern matching uses Python's `re` module; complex patterns could impact performance.
# - Assumes indexes are kept up-to-date by the `IndexManager`.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/memory_cache/index_manager.py
# - src/dbp/memory_cache/storage.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:58:40Z : Initial creation of query classes by CodeAssistant
# * Implemented MetadataQuery and QueryEngine for index-based searching.
###############################################################################

import logging
import re
import threading
from typing import List, Optional, Set, Any

# Assuming necessary imports from sibling modules
try:
    from .index_manager import IndexManager
    from .storage import CacheStorage
    from ..metadata_extraction.data_structures import FileMetadata # Need the actual type
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for QueryEngine.")
    # Placeholders
    IndexManager = object
    CacheStorage = object
    FileMetadata = object

logger = logging.getLogger(__name__)

class MetadataQuery:
    """
    Represents the criteria for querying cached metadata.
    Allows filtering by various indexed attributes.
    """
    def __init__(
        self,
        language: Optional[str] = None,
        reference_doc: Optional[str] = None,
        function_name: Optional[str] = None,
        class_name: Optional[str] = None,
        path_pattern: Optional[str] = None, # Regex pattern for file path
        limit: Optional[int] = None
    ):
        """
        Initializes a metadata query.

        Args:
            language: Filter by programming language (case-insensitive).
            reference_doc: Filter by referenced documentation file path.
            function_name: Filter by function name.
            class_name: Filter by class name.
            path_pattern: Filter by regex pattern applied to the file path.
            limit: Maximum number of results to return.
        """
        self.language = language.lower() if language else None # Normalize language query
        self.reference_doc = reference_doc
        self.function_name = function_name
        self.class_name = class_name
        self.path_pattern = path_pattern
        self.limit = limit
        logger.debug(f"MetadataQuery created with criteria: {self.__dict__}")

    def has_criteria(self) -> bool:
        """Checks if any filter criteria are set."""
        return any([
            self.language,
            self.reference_doc,
            self.function_name,
            self.class_name,
            self.path_pattern
        ])


class QueryEngine:
    """
    Executes metadata queries against the cached data using available indexes.
    """

    def __init__(self, index_manager: IndexManager, storage: CacheStorage, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the QueryEngine.

        Args:
            index_manager: The IndexManager instance providing access to indexes.
            storage: The CacheStorage instance holding the actual metadata objects.
            logger_override: Optional logger instance.
        """
        self.index_manager = index_manager
        self.storage = storage
        self.logger = logger_override or logger
        # Lock might not be strictly needed if IndexManager and CacheStorage are thread-safe,
        # but can provide extra safety around the query execution logic itself.
        self._lock = threading.RLock()
        self.logger.debug("QueryEngine initialized.")

    def execute_query(self, query: MetadataQuery) -> List[FileMetadata]:
        """
        Executes a metadata query using the indexes and retrieves the full metadata objects.

        Args:
            query: A MetadataQuery object specifying the search criteria.

        Returns:
            A list of FileMetadata objects matching the query, up to the specified limit.
        """
        if not isinstance(query, MetadataQuery):
             self.logger.error("Invalid query object provided to execute_query.")
             return []

        with self._lock:
            self.logger.info(f"Executing metadata query: {query.__dict__}")
            try:
                # 1. Find candidate paths using indexes
                candidate_paths = self._find_matching_paths(query)
                if not candidate_paths:
                    self.logger.info("Query yielded no matching paths from indexes.")
                    return []

                self.logger.debug(f"Found {len(candidate_paths)} candidate paths from indexes.")

                # 2. Filter paths by regex pattern (if provided)
                if query.path_pattern:
                    try:
                        pattern = re.compile(query.path_pattern)
                        # Use os.sep for platform-specific matching? Or assume normalized paths?
                        # Assuming paths in index/storage are normalized with '/'
                        filtered_paths = {path for path in candidate_paths if pattern.search(path.replace(os.sep, '/'))}
                        self.logger.debug(f"{len(filtered_paths)} paths remaining after regex filter: '{query.path_pattern}'")
                        candidate_paths = filtered_paths
                        if not candidate_paths:
                             self.logger.info("Query yielded no matching paths after regex filter.")
                             return []
                    except re.error as e:
                        self.logger.error(f"Invalid regex pattern in query '{query.path_pattern}': {e}. Skipping pattern filter.")
                        # Decide whether to return error or proceed without pattern filter
                        # Let's proceed without the filter for now.

                # 3. Retrieve full metadata objects from storage
                results: List[FileMetadata] = []
                paths_to_retrieve = list(candidate_paths) # Convert set to list

                # Apply limit *before* retrieving from storage if possible (more efficient)
                if query.limit is not None and len(paths_to_retrieve) > query.limit:
                     # This simple slicing isn't ideal as the order isn't guaranteed.
                     # A better approach might involve retrieving all and then limiting,
                     # or more complex pagination if needed.
                     paths_to_retrieve = paths_to_retrieve[:query.limit]
                     self.logger.debug(f"Limiting retrieval to {len(paths_to_retrieve)} paths.")


                for path in paths_to_retrieve:
                    metadata = self.storage.get(path)
                    if metadata:
                        results.append(metadata)
                    else:
                        # This indicates inconsistency between index and storage, should be rare
                        self.logger.warning(f"Path '{path}' found in index but not in cache storage.")

                # Re-apply limit after retrieval if slicing wasn't precise or some items were missing
                if query.limit is not None and len(results) > query.limit:
                     results = results[:query.limit]

                self.logger.info(f"Query executed successfully, returning {len(results)} results.")
                return results

            except Exception as e:
                self.logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
                return [] # Return empty list on error

    def _find_matching_paths(self, query: MetadataQuery) -> Set[str]:
        """
        Uses the IndexManager to find the intersection of paths matching
        all specified index-based criteria in the query.
        """
        candidate_sets: List[Set[str]] = []
        applied_index_filters = False

        # Collect path sets from each relevant index
        if query.language:
            candidate_sets.append(self.index_manager.get_paths_by_language(query.language))
            applied_index_filters = True
        if query.reference_doc:
            candidate_sets.append(self.index_manager.get_paths_by_reference_doc(query.reference_doc))
            applied_index_filters = True
        if query.function_name:
            candidate_sets.append(self.index_manager.get_paths_by_function(query.function_name))
            applied_index_filters = True
        if query.class_name:
            candidate_sets.append(self.index_manager.get_paths_by_class(query.class_name))
            applied_index_filters = True

        # If no index filters were applied, start with all known paths
        if not applied_index_filters:
            # Get all keys from storage as the initial set if no index criteria used
            # This is needed if only a path_pattern is provided.
            # Note: This could be inefficient if the cache is very large.
            # Consider requiring at least one indexable field for efficient queries.
            if query.path_pattern:
                 self.logger.debug("No index filters applied, retrieving all keys from storage for path pattern matching.")
                 return self.storage.get_all_keys()
            else:
                 # If no criteria at all, return empty set? Or all keys? Let's return empty.
                 self.logger.debug("Query has no criteria, returning empty result set.")
                 return set()


        # Calculate the intersection of all collected path sets
        if not candidate_sets: # Should not happen if applied_index_filters is True, but safety check
             return set()

        # Start with the first set
        final_paths = candidate_sets[0].copy()
        # Intersect with the rest
        for i in range(1, len(candidate_sets)):
            final_paths.intersection_update(candidate_sets[i])
            if not final_paths: # Stop early if intersection becomes empty
                break

        return final_paths
