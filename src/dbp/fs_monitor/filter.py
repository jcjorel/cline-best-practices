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
# Implements the GitIgnoreFilter class, which is responsible for determining
# whether a given file path should be ignored based on standard .gitignore
# specified in the configuration.
###############################################################################
# [Source file design principles]
# - Parses .gitignore files according to standard rules (comments, negation, directory patterns).
# - Handles patterns relative to the location of the .gitignore file.
# - Includes mandatory ignore patterns defined by the system design.
# - Incorporates additional ignore patterns from the application configuration.
# - Uses fnmatch for glob pattern matching.
# - Caches results for previously checked paths to improve performance.
# - Design Decision: Centralized Filter Logic (2025-04-14)
#   * Rationale: Consolidates all ignore logic into one place, making it easier to manage and ensuring consistent filtering across the system.
#   * Alternatives considered: Applying filters at multiple points (harder to maintain consistency).
###############################################################################
# [Source file constraints]
# - Requires access to the application configuration for additional patterns.
# - Assumes standard .gitignore syntax.
# - Performance might degrade if extremely large numbers of patterns or paths are checked frequently without cache hits.
# - Path normalization (e.g., using forward slashes) is important for consistent matching.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md (Dynamic File Exclusion Strategy)
# - doc/CONFIGURATION.md (monitor.ignore_patterns)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:45:10Z : Initial creation of GitIgnoreFilter class by CodeAssistant
# * Implemented loading of gitignore files, config patterns, mandatory ignores, and path matching logic.
###############################################################################

import os
import re
import logging
from typing import List, Set, Dict, Any, Optional, Tuple
import fnmatch
from pathlib import Path
import threading
from ..core.component import Component

logger = logging.getLogger(__name__)

class GitIgnoreFilter:
    """
    Filters file paths based on .gitignore rules, mandatory system ignores,
    and configuration patterns.
    """

    def __init__(self, config: Any, project_root: Optional[str] = None):
        """
        Initializes the GitIgnoreFilter.

        Args:
            config: Configuration object providing 'monitor.ignore_patterns'.
            project_root: The absolute path to the project's root directory.
                          Used to find and process .gitignore files.
        """
        self.config = config
        self.project_root = Path(project_root).resolve() if project_root else None
        # List of tuples: (pattern_string, is_negative_pattern, base_directory_path)
        self._patterns: List[Tuple[str, bool, Path]] = []
        self._lock = threading.RLock() # Lock for modifying patterns and cache
        self._cached_results: Dict[str, bool] = {} # Cache path -> should_ignore result

        self._initialize_patterns()

    def _initialize_patterns(self):
        """Loads mandatory, configured, and .gitignore patterns."""
        with self._lock:
            self._patterns = [] # Reset patterns
            self._cached_results = {} # Clear cache

            # 1. Add mandatory patterns (relative to project root if available, else global)
            self._add_mandatory_patterns()

            # 2. Add patterns from configuration
            self._add_config_patterns()

            # 3. Scan for and load .gitignore files within the project root
            if self.project_root:
                self._load_all_gitignore_files(self.project_root)

            logger.info(f"GitIgnoreFilter initialized with {len(self._patterns)} patterns.")

    def update_project_root(self, project_root: str):
        """Updates the project root and re-initializes patterns."""
        logger.info(f"Updating project root for GitIgnoreFilter to: {project_root}")
        new_root = Path(project_root).resolve()
        if new_root != self.project_root:
             self.project_root = new_root
             self._initialize_patterns() # Reload all patterns for the new root

    def _add_mandatory_patterns(self):
        """Adds system-defined mandatory ignore patterns."""
        logger.debug("Adding mandatory ignore patterns.")
        # Use project_root as base if available, otherwise treat as global patterns
        base = self.project_root if self.project_root else Path('.')

        # Scratchpad directory (relative to project root)
        # Ensure it ends with / to match only directories

        # Files or directories containing "deprecated" anywhere in their path components
        # This is harder to express perfectly with gitignore patterns alone.
        # We might need a custom check in should_ignore or rely on simpler patterns.
        # Simple approach: ignore if 'deprecated' is in the name itself.
        # More complex requires path component checking.
        # Let's use a glob pattern that might catch most cases.
        self._patterns.append(("*deprecated*", False, base)) # Matches if 'deprecated' is in the final component name
        # Note: A pattern like '**/deprecated/**' is closer but fnmatch might not support '**' fully depending on version/OS.
        # We'll add a specific check in should_ignore for path components.

    def _add_config_patterns(self):
        """Adds ignore patterns specified in the configuration."""
        patterns = self.config.get('monitor.ignore_patterns', [])
        logger.debug(f"Adding {len(patterns)} patterns from configuration.")
        base = self.project_root if self.project_root else Path('.')
        for pattern in patterns:
            if isinstance(pattern, str) and pattern.strip():
                # Assume config patterns are global unless explicitly relative?
                # For now, treat them as relative to project root if available.
                self._patterns.append((pattern.strip(), False, base))
            else:
                 logger.warning(f"Ignoring invalid pattern from config: {pattern}")

    def _load_all_gitignore_files(self, start_dir: Path):
        """Recursively finds and loads all .gitignore files from start_dir downwards."""
        logger.debug(f"Scanning for .gitignore files starting from: {start_dir}")
        gitignore_paths = list(start_dir.rglob('.gitignore'))
        logger.info(f"Found {len(gitignore_paths)} .gitignore files.")

        # Sort paths by depth (shortest first) so parent rules are processed first
        gitignore_paths.sort(key=lambda p: len(p.parts))

        for path in gitignore_paths:
            self.add_gitignore_file(str(path))

    def add_gitignore_file(self, gitignore_path_str: str) -> bool:
        """
        Parses a .gitignore file and adds its rules to the filter patterns.

        Args:
            gitignore_path_str: The absolute path to the .gitignore file.

        Returns:
            True if the file was loaded and parsed successfully, False otherwise.
        """
        gitignore_path = Path(gitignore_path_str).resolve()
        if not gitignore_path.is_file():
            logger.warning(f".gitignore file not found or not a file: {gitignore_path}")
            return False

        # Patterns in a .gitignore are relative to the directory containing the file
        base_dir = gitignore_path.parent
        logger.debug(f"Loading patterns from: {gitignore_path} (relative to: {base_dir})")

        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                count = 0
                for line_num, line in enumerate(f, 1):
                    pattern = line.strip()

                    # Skip comments and empty lines
                    if not pattern or pattern.startswith('#'):
                        continue

                    # Handle negation (!)
                    is_negative = pattern.startswith('!')
                    if is_negative:
                        pattern = pattern[1:].strip()
                        if not pattern: continue # Ignore '!' on its own

                    # Handle directory-only patterns (ending with /)
                    # We store the pattern as is, and check is_dir in should_ignore
                    # is_dir_only = pattern.endswith('/')
                    # if is_dir_only:
                    #     pattern = pattern[:-1].strip()
                    #     if not pattern: continue

                    # Store the pattern, its negation status, and its base directory
                    self._patterns.append((pattern, is_negative, base_dir))
                    count += 1
                logger.debug(f"Added {count} patterns from {gitignore_path}")

            # Clear cache as patterns have changed
            self._cached_results = {}
            return True

        except Exception as e:
            logger.error(f"Failed to read or parse .gitignore file {gitignore_path}: {e}", exc_info=True)
            return False

    def should_ignore(self, file_path_str: str) -> bool:
        """
        Checks if a given file path should be ignored based on the loaded patterns.
        Patterns are evaluated in order, with later patterns overriding earlier ones.
        Negation patterns (`!pattern`) override previous ignore rules for that pattern.

        Args:
            file_path_str: The absolute path to the file or directory to check.

        Returns:
            True if the path should be ignored, False otherwise.
        """
        try:
            abs_path = Path(file_path_str).resolve()
            path_str_norm = str(abs_path).replace(os.sep, '/') # Normalize to forward slashes
        except Exception as e:
             logger.warning(f"Could not resolve path '{file_path_str}' for ignore check: {e}")
             return True # Ignore paths that cannot be resolved

        with self._lock:
            # 1. Check cache
            if path_str_norm in self._cached_results:
                return self._cached_results[path_str_norm]

            # 2. Check mandatory 'deprecated' in path components
            if 'deprecated' in abs_path.parts:
                 logger.debug(f"Ignoring path due to 'deprecated' component: {path_str_norm}")
                 self._cached_results[path_str_norm] = True
                 return True

            # 3. Evaluate patterns
            ignored = False # Default: not ignored
            matched_pattern = None # Keep track of the last matching pattern

            for pattern_str, is_negative, base_dir in self._patterns:
                # Make path relative to the pattern's base directory for matching
                try:
                    relative_path = abs_path.relative_to(base_dir)
                    relative_path_str = str(relative_path).replace(os.sep, '/')
                except ValueError:
                    # Path is not relative to this pattern's base_dir, skip pattern
                    continue
                except Exception as e:
                     logger.warning(f"Error making path relative: {abs_path} to {base_dir}: {e}")
                     continue


                if self._match_single_pattern(relative_path_str, pattern_str, abs_path.is_dir()):
                    matched_pattern = (pattern_str, is_negative, base_dir)
                    ignored = not is_negative # If negative pattern matches, it's NOT ignored (overrides previous ignore)

            if matched_pattern:
                 logger.debug(f"Path '{path_str_norm}' matched pattern '{matched_pattern[0]}' (negative={matched_pattern[1]}) from base '{matched_pattern[2]}'. Ignored={ignored}")
            else:
                 logger.debug(f"Path '{path_str_norm}' did not match any relevant patterns. Ignored={ignored}")


            # Cache and return result
            self._cached_results[path_str_norm] = ignored
            return ignored

    def _match_single_pattern(self, relative_path: str, pattern: str, path_is_dir: bool) -> bool:
        """
        Checks if a relative path matches a single gitignore pattern.
        Handles directory patterns, leading slashes, and globbing.
        """

        # Handle directory-only patterns (ending with /)
        is_dir_pattern = pattern.endswith('/')
        if is_dir_pattern:
            if not path_is_dir:
                return False # Dir pattern cannot match a file
            pattern = pattern.rstrip('/') # Remove trailing slash for matching

        # Handle patterns starting with / (match only from base directory)
        if pattern.startswith('/'):
             pattern = pattern.lstrip('/')
             # Check if relative_path directly matches or is within a matching dir
             # fnmatch doesn't handle leading slash logic directly, we do it via relative path check
             return fnmatch.fnmatch(relative_path, pattern) or \
                    (path_is_dir and relative_path.startswith(pattern + '/'))

        # Handle patterns without / (match anywhere)
        if '/' not in pattern:
            # Match against the basename or any component
            basename = relative_path.split('/')[-1]
            return fnmatch.fnmatch(basename, pattern)

        # Handle patterns with / (match relative to base_dir)
        # This matches if the relative path itself matches, or if it's a file
        # within a directory matched by the pattern.
        return fnmatch.fnmatch(relative_path, pattern) or \
               fnmatch.fnmatch(relative_path, pattern + '/*')


    def clear_cache(self):
        """Clears the internal cache of checked paths."""
        with self._lock:
            self._cached_results = {}
            logger.debug("GitIgnoreFilter cache cleared.")


class FilterComponent(Component):
    """
    [Class intent]
    Component wrapper for the GitIgnoreFilter class following the KISS component pattern.
    Provides path filtering services to determine if files or directories should be ignored.
    
    [Implementation details]
    Wraps the GitIgnoreFilter class, initializing it during component initialization
    and providing access to the filter functionality through methods.
    
    [Design principles]
    Single responsibility for file path filtering within the component system.
    Centralizes the filtering logic to ensure consistent rules application.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes the FilterComponent with minimal setup.
        
        [Implementation details]
        Sets the initialized flag to False and prepares for filter creation.
        
        [Design principles]
        Minimal initialization with explicit state tracking.
        """
        super().__init__()
        self._initialized = False
        self._filter = None
        self.logger = None
        self.project_root = None
    
    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component, used for registration and dependency references.
        
        [Implementation details]
        Returns a simple string constant.
        
        [Design principles]
        Explicit naming for clear component identification.
        
        Returns:
            str: The component name "filter"
        """
        return "filter"
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns the component names that this component depends on.
        
        [Implementation details]
        Filter depends on config_manager for filter patterns.
        
        [Design principles]
        Explicit dependency declaration for clear initialization order.
        
        Returns:
            List[str]: List of component dependencies
        """
        return ["config_manager"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the filter with the provided configuration.
        
        [Implementation details]
        Creates a GitIgnoreFilter instance and initializes it with the project root path.
        
        [Design principles]
        Explicit initialization with clear success/failure indication.
        
        Args:
            config: Configuration object with filter settings
            
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            self.logger.warning(f"Component '{self.name}' already initialized.")
            return
        
        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get component-specific configuration through config_manager
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            config_manager = system.get_component("config_manager")
            
            # Get project root from configuration
            self.project_root = config_manager.get('project.root_path')
            
            # Create and initialize the filter
            self._filter = GitIgnoreFilter(config_manager, self.project_root)
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize filter component: {e}", exc_info=True)
            self._filter = None
            self._initialized = False
            raise RuntimeError(f"Failed to initialize filter component: {e}") from e
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the filter and releases resources.
        
        [Implementation details]
        Clears the filter's cache and resets state.
        
        [Design principles]
        Clean resource release with clear state reset.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        if self._filter:
            try:
                self._filter.clear_cache()
            except Exception as e:
                self.logger.error(f"Error during filter shutdown: {e}", exc_info=True)
            finally:
                self._filter = None
        
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")
    
    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Indicates if the component is successfully initialized.
        
        [Implementation details]
        Returns the value of the internal _initialized flag.
        
        [Design principles]
        Simple boolean flag for clear initialization status.
        
        Returns:
            bool: True if component is initialized, False otherwise
        """
        return self._initialized
    
    def should_ignore(self, path: str) -> bool:
        """
        [Function intent]
        Checks if a given path should be ignored based on filter rules.
        
        [Implementation details]
        Delegates to the GitIgnoreFilter's should_ignore method.
        
        [Design principles]
        Convenience method to simplify access to filter functionality.
        
        Args:
            path: File or directory path to check
            
        Returns:
            bool: True if the path should be ignored, False otherwise
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._filter:
            raise RuntimeError("FilterComponent not initialized")
        return self._filter.should_ignore(path)
    
    def update_project_root(self, new_root: str) -> None:
        """
        [Function intent]
        Updates the project root path and reinitializes filter patterns.
        
        [Implementation details]
        Delegates to the GitIgnoreFilter's update_project_root method.
        
        [Design principles]
        Provides ability to adapt to project path changes at runtime.
        
        Args:
            new_root: New project root path
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._filter:
            raise RuntimeError("FilterComponent not initialized")
        self.project_root = new_root
        self._filter.update_project_root(new_root)
        self.logger.info(f"Updated project root to: {new_root}")
    
    def add_gitignore_file(self, gitignore_path: str) -> bool:
        """
        [Function intent]
        Adds patterns from a specified gitignore file.
        
        [Implementation details]
        Delegates to the GitIgnoreFilter's add_gitignore_file method.
        
        [Design principles]
        Allows dynamic addition of ignore patterns at runtime.
        
        Args:
            gitignore_path: Path to the gitignore file to load
            
        Returns:
            bool: True if the file was loaded successfully, False otherwise
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._filter:
            raise RuntimeError("FilterComponent not initialized")
        return self._filter.add_gitignore_file(gitignore_path)
