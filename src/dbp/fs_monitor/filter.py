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
# rules, mandatory system ignores (like scratchpad/), and additional patterns
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
# - scratchpad/dbp_implementation_plan/plan_fs_monitoring.md
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
        self._patterns.append(("scratchpad/", False, base))

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
