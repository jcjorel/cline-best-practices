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
# Implements the IndexManager class, responsible for creating and maintaining
# various in-memory indexes over the cached FileMetadata objects. These indexes
# allow for efficient querying based on attributes like programming language,
# referenced documentation, function names, and class names.
###############################################################################
# [Source file design principles]
# - Maintains multiple inverted indexes (attribute value -> set of file paths).
# - Provides methods to add metadata to indexes, remove metadata from indexes, and clear all indexes.
# - Offers query methods to retrieve sets of file paths based on specific index keys.
# - Uses dictionaries and sets for efficient index lookups and storage.
# - Ensures thread safety for index modifications and queries using RLock.
# - Design Decision: Multiple Specific Indexes (2025-04-15)
#   * Rationale: Provides fast lookups for common query patterns (language, references, names) without requiring full scans.
#   * Alternatives considered: Single generic search index (more complex, potentially slower for specific lookups), No indexes (requires iterating through all cached items for queries).
###############################################################################
# [Source file constraints]
# - Memory usage grows with the number of unique index keys and the number of files associated with each key.
# - Index updates must be kept consistent with the main CacheStorage.
# - Assumes FileMetadata objects contain the necessary attributes for indexing.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/metadata_extraction/data_structures.py (Defines FileMetadata)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:57:25Z : Initial creation of IndexManager class by CodeAssistant
# * Implemented indexing logic for path, language, references, functions, and classes. Added query methods.
###############################################################################

import logging
import threading
from typing import Dict, Set, Optional, List

# Assuming FileMetadata is defined elsewhere
try:
    from ..metadata_extraction.data_structures import FileMetadata
except ImportError:
    logging.getLogger(__name__).error("Failed to import FileMetadata for IndexManager.")
    FileMetadata = object # Placeholder

logger = logging.getLogger(__name__)

class IndexManager:
    """
    Manages various in-memory indexes over cached FileMetadata objects
    to facilitate efficient querying based on different attributes.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the IndexManager with empty indexes."""
        self.logger = logger_override or logger
        self._lock = threading.RLock() # Thread safety for index access

        # --- Index Structures ---
        # Primary index (optional, storage might handle this)
        # self._path_index: Dict[str, FileMetadata] = {} # Path -> Metadata (redundant with CacheStorage?)

        # Secondary indexes: Attribute Value -> Set[File Path]
        self._language_index: Dict[str, Set[str]] = {}
        self._reference_doc_index: Dict[str, Set[str]] = {}
        self._function_index: Dict[str, Set[str]] = {}
        self._class_index: Dict[str, Set[str]] = {}
        # Add more indexes as needed (e.g., by dependency, by tag)

        self.logger.debug("IndexManager initialized.")

    def index_metadata(self, metadata: FileMetadata):
        """
        Adds or updates the indexes for a given FileMetadata object.
        If the path already exists in indexes, it's typically removed first
        (implicitly handled by removing then adding, or explicitly if needed).

        Args:
            metadata: The FileMetadata object to index.
        """
        if not isinstance(metadata, FileMetadata) or not metadata.path:
            self.logger.warning(f"Attempted to index invalid metadata object: {metadata}")
            return

        path = metadata.path
        with self._lock:
            self.logger.debug(f"Indexing metadata for path: {path}")
            # --- Remove existing index entries for this path first ---
            # This ensures indexes are updated correctly if metadata changes.
            # It's slightly less efficient than targeted updates but simpler.
            self.remove_from_indexes(path) # Use the removal logic

            # --- Add new index entries ---
            # Language Index
            if metadata.language:
                lang = metadata.language.lower() # Normalize language
                self._language_index.setdefault(lang, set()).add(path)

            # Reference Documentation Index
            if metadata.header_sections and metadata.header_sections.reference_documentation:
                for ref_doc in metadata.header_sections.reference_documentation:
                    if ref_doc: # Ensure not empty string
                         # Normalize ref_doc path? Assuming it's stored consistently.
                         self._reference_doc_index.setdefault(ref_doc, set()).add(path)

            # Function Index
            if metadata.functions:
                for func in metadata.functions:
                    if func.name: # Ensure function has a name
                         self._function_index.setdefault(func.name, set()).add(path)

            # Class Index (including methods within classes)
            if metadata.classes:
                for cls in metadata.classes:
                    if cls.name: # Ensure class has a name
                         self._class_index.setdefault(cls.name, set()).add(path)
                    # Index methods within the class as well?
                    if cls.methods:
                         for method in cls.methods:
                              if method.name:
                                   # Optionally prefix method name with class? e.g., "ClassName.methodName"
                                   # Or just index the method name directly? Let's index directly for now.
                                   self._function_index.setdefault(method.name, set()).add(path)

            self.logger.debug(f"Finished indexing metadata for path: {path}")


    def remove_from_indexes(self, path: str):
        """
        Removes all index entries associated with a specific file path.

        Args:
            path: The file path to remove from all indexes.
        """
        if not path: return

        with self._lock:
            self.logger.debug(f"Removing path from indexes: {path}")
            # Create a temporary list of keys to modify to avoid changing dict size during iteration
            keys_to_check = []

            # Language Index
            keys_to_check = list(self._language_index.keys())
            for lang in keys_to_check:
                if path in self._language_index.get(lang, set()):
                    self._language_index[lang].discard(path)
                    if not self._language_index[lang]: # Remove empty set
                        del self._language_index[lang]

            # Reference Doc Index
            keys_to_check = list(self._reference_doc_index.keys())
            for ref_doc in keys_to_check:
                if path in self._reference_doc_index.get(ref_doc, set()):
                    self._reference_doc_index[ref_doc].discard(path)
                    if not self._reference_doc_index[ref_doc]:
                        del self._reference_doc_index[ref_doc]

            # Function Index
            keys_to_check = list(self._function_index.keys())
            for func_name in keys_to_check:
                if path in self._function_index.get(func_name, set()):
                    self._function_index[func_name].discard(path)
                    if not self._function_index[func_name]:
                        del self._function_index[func_name]

            # Class Index
            keys_to_check = list(self._class_index.keys())
            for class_name in keys_to_check:
                if path in self._class_index.get(class_name, set()):
                    self._class_index[class_name].discard(path)
                    if not self._class_index[class_name]:
                        del self._class_index[class_name]

            self.logger.debug(f"Finished removing path from indexes: {path}")


    def clear_indexes(self):
        """Removes all entries from all indexes."""
        with self._lock:
            self._language_index.clear()
            self._reference_doc_index.clear()
            self._function_index.clear()
            self._class_index.clear()
            self.logger.info("All metadata indexes cleared.")

    # --- Query Methods ---

    def get_paths_by_language(self, language: str) -> Set[str]:
        """Retrieves the set of file paths associated with a given language."""
        with self._lock:
            # Normalize query language
            return self._language_index.get(language.lower(), set()).copy()

    def get_paths_by_reference_doc(self, reference_doc: str) -> Set[str]:
        """Retrieves the set of file paths that reference a specific documentation file."""
        with self._lock:
            # Normalize reference_doc path?
            return self._reference_doc_index.get(reference_doc, set()).copy()

    def get_paths_by_function(self, function_name: str) -> Set[str]:
        """Retrieves the set of file paths containing a function with the given name."""
        with self._lock:
            return self._function_index.get(function_name, set()).copy()

    def get_paths_by_class(self, class_name: str) -> Set[str]:
        """Retrieves the set of file paths containing a class with the given name."""
        with self._lock:
            return self._class_index.get(class_name, set()).copy()

    def get_index_stats(self) -> Dict[str, int]:
         """Returns statistics about the current state of the indexes."""
         with self._lock:
              return {
                   "language_keys": len(self._language_index),
                   "reference_doc_keys": len(self._reference_doc_index),
                   "function_keys": len(self._function_index),
                   "class_keys": len(self._class_index),
                   # Could add total number of path entries per index if needed
              }
