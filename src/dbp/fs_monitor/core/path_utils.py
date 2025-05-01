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
# This file provides utilities for path resolution and pattern matching for the
# file system monitor component. It handles wildcard patterns, Git root-relative paths,
# and efficient file matching operations.
###############################################################################
# [Source file design principles]
# - Support for Unix-style wildcards (*, **, ?)
# - Efficient path resolution and pattern matching
# - Support for both absolute and Git root-relative paths
# - Clear separation between pattern creation and pattern matching
# - Robust error handling for invalid patterns and paths
###############################################################################
# [Source file constraints]
# - Must handle path differences across operating systems
# - Must provide consistent behavior for pattern matching
# - Must be performant for frequent file matching operations
# - Must properly handle Git root resolution failures
# - Must support recursive and non-recursive pattern matching
###############################################################################
# [Dependencies]
# system:os
# system:re
# system:fnmatch
# system:typing
# codebase:src/dbp/fs_monitor/exceptions.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T08:29:00Z : Added centralized log file filtering function by CodeAssistant
# * Implemented is_log_file() function for detecting log files
# * Standardized log file detection across all fs_monitor components
# * Prevents infinite monitoring loops from log file changes
# 2025-04-29T00:00:00Z : Initial implementation of path utilities for fs_monitor redesign by CodeAssistant
# * Created path resolution functions for absolute and Git-root relative paths
# * Implemented pattern matching utilities with support for wildcards
# * Added file finding functions for pattern-based file discovery
###############################################################################

import os
import re
from typing import Optional, List, Tuple
import fnmatch
from .exceptions import PatternError, PathResolutionError


def get_git_root() -> str:
    """
    [Function intent]
    Find the Git root directory for the current project.
    
    [Design principles]
    - Support for Git root-relative paths
    - Fail-fast error detection
    
    [Implementation details]
    - Walks up the directory tree looking for .git directory
    - Raises PathResolutionError if not found
    
    Returns:
        Absolute path to the Git root directory
        
    Raises:
        PathResolutionError: If Git root cannot be found
    """
    # Start from the current working directory
    current_dir = os.path.abspath(os.getcwd())
    
    # Walk up the directory tree looking for .git directory
    while current_dir != os.path.dirname(current_dir):  # Stop at the file system root
        if os.path.isdir(os.path.join(current_dir, ".git")):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # If we reach here, we couldn't find the Git root
    raise PathResolutionError("Could not find Git root directory")


def resolve_path(path: str) -> str:
    """
    [Function intent]
    Convert a path to an absolute path, handling Git root-relative paths.
    
    [Design principles]
    - Consistent path resolution
    - Support for both absolute and Git root-relative paths
    
    [Implementation details]
    - Expands ~/ to user's home directory
    - Handles Git root-relative paths
    - Converts to absolute path
    
    Args:
        path: Path to resolve (absolute, relative to CWD, or Git root-relative)
        
    Returns:
        Absolute path
        
    Raises:
        PathResolutionError: If path cannot be resolved
    """
    # Expand ~/ to user's home directory
    if path.startswith("~"):
        path = os.path.expanduser(path)
    
    # If already absolute, just normalize it
    if os.path.isabs(path):
        return os.path.normpath(path)
    
    # Try to interpret as Git root-relative
    try:
        git_root = get_git_root()
        return os.path.normpath(os.path.join(git_root, path))
    except PathResolutionError:
        # Fall back to CWD-relative if Git root not found
        return os.path.abspath(path)


def pattern_to_regex(pattern: str) -> Tuple[re.Pattern, bool]:
    """
    [Function intent]
    Convert a Unix-style wildcard pattern to a regular expression.
    
    [Design principles]
    - Support for Unix-style wildcards (*, **, ?)
    - Efficient pattern matching
    
    [Implementation details]
    - Converts * to match any character except path separator
    - Converts ** to match any character including path separator
    - Converts ? to match any single character
    - Returns whether pattern has wildcards
    
    Args:
        pattern: Unix-style wildcard pattern
        
    Returns:
        Tuple of compiled regex pattern and whether the pattern contained wildcards
        
    Raises:
        PatternError: If pattern is invalid
    """
    # Check if pattern is valid
    if not pattern:
        raise PatternError("Pattern cannot be empty")
    
    # Check if pattern has wildcards
    has_wildcards = any(c in pattern for c in "*?")
    
    # Replace special pattern characters with regex equivalents
    # First, escape all regex special characters
    regex = re.escape(pattern)
    
    # Replace ** with a special marker
    regex = regex.replace(r'\*\*', '###DOUBLE_STAR###')
    
    # Replace * with regex to match any character except path separator
    regex = regex.replace(r'\*', '[^/\\\\]*')
    
    # Replace ? with regex to match any single character except path separator
    regex = regex.replace(r'\?', '[^/\\\\]')
    
    # Replace the special marker with regex to match any character including path separator
    regex = regex.replace('###DOUBLE_STAR###', '.*')
    
    # Ensure the pattern matches the entire string
    regex = f"^{regex}$"
    
    try:
        compiled_regex = re.compile(regex)
        return compiled_regex, has_wildcards
    except re.error as e:
        raise PatternError(f"Invalid pattern: {pattern}, error: {str(e)}")


def matches_pattern(path: str, pattern: str) -> bool:
    """
    [Function intent]
    Check if a path matches a pattern.
    
    [Design principles]
    - Simplified pattern matching API
    - Support for wildcards
    
    [Implementation details]
    - Uses pattern_to_regex for wildcard handling
    - Falls back to string equality for patterns without wildcards
    
    Args:
        path: Path to check
        pattern: Pattern to match against
        
    Returns:
        True if the path matches the pattern, False otherwise
    """
    regex, has_wildcards = pattern_to_regex(pattern)
    
    # If no wildcards, just check for equality
    if not has_wildcards:
        return path == pattern
    
    return regex.match(path) is not None


def find_matching_files(base_dir: str, pattern: str) -> List[str]:
    """
    [Function intent]
    Find all files in a directory that match a pattern.
    
    [Design principles]
    - Efficient file system traversal
    - Support for wildcards
    
    [Implementation details]
    - Handles patterns with and without ** (recursive)
    - Returns absolute paths
    
    Args:
        base_dir: Directory to search in
        pattern: Pattern to match against
        
    Returns:
        List of absolute paths to matching files
    """
    regex, has_wildcards = pattern_to_regex(pattern)
    
    # If no wildcards and pattern is absolute, just check if the file exists
    if not has_wildcards and os.path.isabs(pattern):
        return [pattern] if os.path.exists(pattern) else []
    
    # Normalize base directory
    base_dir = os.path.abspath(base_dir)
    
    # Check if we need recursive traversal
    is_recursive = "**" in pattern
    
    matching_files = []
    
    if is_recursive:
        # Walk the directory tree
        for root, _, files in os.walk(base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, base_dir)
                if regex.match(rel_path):
                    matching_files.append(file_path)
    else:
        # Non-recursive search
        pattern_parts = pattern.split(os.path.sep)
        current_dir = base_dir
        
        # Process each part of the pattern
        for i, part in enumerate(pattern_parts):
            if i == len(pattern_parts) - 1:
                # Last part, match files
                try:
                    for item in os.listdir(current_dir):
                        item_path = os.path.join(current_dir, item)
                        if os.path.isfile(item_path) and fnmatch.fnmatch(item, part):
                            matching_files.append(item_path)
                except (FileNotFoundError, PermissionError) as e:
                    # Directory doesn't exist or can't be accessed
                    return []
            else:
                # Directory part
                if "*" in part or "?" in part:
                    # Wildcard in directory, need to check all subdirectories
                    try:
                        for item in os.listdir(current_dir):
                            item_path = os.path.join(current_dir, item)
                            if os.path.isdir(item_path) and fnmatch.fnmatch(item, part):
                                # Recursively process matching directories
                                subpattern = os.path.sep.join(pattern_parts[i+1:])
                                matching_files.extend(find_matching_files(item_path, subpattern))
                    except (FileNotFoundError, PermissionError) as e:
                        # Directory doesn't exist or can't be accessed
                        pass
                    return matching_files
                else:
                    # No wildcard, just move to the next directory
                    current_dir = os.path.join(current_dir, part)
                    if not os.path.isdir(current_dir):
                        # If directory doesn't exist, no matches
                        return []
    
    return matching_files


def is_subpath(path: str, potential_parent: str) -> bool:
    """
    [Function intent]
    Check if a path is a subpath of another path.
    
    [Design principles]
    - Path hierarchy validation
    - Normalization for consistent comparison
    
    [Implementation details]
    - Normalizes both paths for comparison
    - Checks if potential_parent is a prefix of path
    
    Args:
        path: Path to check
        potential_parent: Path that might be a parent of the first path
        
    Returns:
        True if path is a subpath of potential_parent, False otherwise
    """
    path = os.path.normpath(os.path.abspath(path))
    potential_parent = os.path.normpath(os.path.abspath(potential_parent))
    
    # Add trailing separator to avoid false positives (e.g., /foo/bar vs /foo/baz)
    if not potential_parent.endswith(os.path.sep):
        potential_parent += os.path.sep
    
    return path.startswith(potential_parent)


def is_log_file(path: str) -> bool:
    """
    [Function intent]
    Determine if a file is a log file that should be excluded from monitoring.
    
    [Design principles]
    - Prevent infinite event loops caused by watching log files
    - Centralized log file detection logic for consistent behavior
    
    [Implementation details]
    - Checks file extensions and path patterns
    - Platform-agnostic implementation
    - Covers common log file naming conventions
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a log file that should be excluded, False otherwise
    """
    # Check for common log file extensions
    if path.endswith('.log'):
        return True
        
    # Check for log directories
    log_dir_patterns = [
        r'/logs/',
        r'[\\/]logs[\\/]',
        r'[\\/]log[\\/]',
    ]
    
    for pattern in log_dir_patterns:
        if re.search(pattern, path):
            return True
            
    # Check for other common log file patterns
    log_file_patterns = [
        r'\.log\.\d+$',  # log.1, log.2, etc.
        r'\.log\.\d{8}$',  # log.20250429, etc.
        r'\.log\.\d{6}$',  # log.202504, etc.
        r'\.log\.\w+$',    # log.bak, log.old, etc.
    ]
    
    for pattern in log_file_patterns:
        if re.search(pattern, path):
            return True
            
    return False


def get_common_parent_dir(paths: List[str]) -> Optional[str]:
    """
    [Function intent]
    Find the common parent directory of a list of paths.
    
    [Design principles]
    - Efficient path hierarchy analysis
    
    [Implementation details]
    - Handles empty lists
    - Normalizes paths for comparison
    - Finds longest common prefix
    
    Args:
        paths: List of paths to analyze
        
    Returns:
        Common parent directory if found, None if no common parent exists or paths is empty
    """
    if not paths:
        return None
    
    if len(paths) == 1:
        return os.path.dirname(os.path.abspath(paths[0]))
    
    # Normalize all paths
    normalized_paths = [os.path.normpath(os.path.abspath(p)) for p in paths]
    
    # Split into components
    path_components = [p.split(os.path.sep) for p in normalized_paths]
    
    # Find the minimum length
    min_length = min(len(c) for c in path_components)
    
    # Find the common prefix
    common_components = []
    for i in range(min_length):
        if all(c[i] == path_components[0][i] for c in path_components):
            common_components.append(path_components[0][i])
        else:
            break
    
    if not common_components:
        return None
    
    return os.path.sep.join(common_components)
