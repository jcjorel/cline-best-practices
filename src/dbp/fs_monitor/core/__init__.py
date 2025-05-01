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
# Exports core functionality for the fs_monitor module, providing access to 
# the fundamental classes and interfaces needed by other parts of the system.
###############################################################################
# [Source file design principles]
# - Explicit exports of all public APIs from core submodules
# - Simplified import paths for commonly used core classes
# - Maintains clean separation between public API and implementation details
###############################################################################
# [Source file constraints]
# - Should not include implementation code, only re-exports from submodules
# - Must maintain backwards compatibility for public APIs
###############################################################################
# [Dependencies]
# codebase:src/dbp/fs_monitor/core/listener.py
# codebase:src/dbp/fs_monitor/core/handle.py
# codebase:src/dbp/fs_monitor/core/event_types.py
# codebase:src/dbp/fs_monitor/core/exceptions.py
# codebase:src/dbp/fs_monitor/core/path_utils.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T08:51:00Z : Fixed path_utils imports to match actual functions by CodeAssistant
# * Updated path_utils imports to use functions that actually exist in the module
# * Changed imports like normalize_path to resolve_path
# * Updated __all__ list with correct path_utils function names
# 2025-04-29T08:49:00Z : Fixed listener class name mismatches by CodeAssistant
# * Updated listener import from FileSystemListener to FileSystemEventListener
# * Added import for BaseFileSystemEventListener
# * Updated __all__ list with correct listener class names
# 2025-04-29T08:47:00Z : Fixed exception class name mismatches by CodeAssistant
# * Updated exception imports to match actual class names in exceptions.py
# * Changed FSMonitorError to FileSystemMonitorError
# * Updated __all__ list with correct exception class names
# 2025-04-29T00:49:00Z : Created core/__init__.py as part of fs_monitor reorganization by CodeAssistant
# * Added exports for core module components
# * Added header documentation
###############################################################################

"""
Core functionality for the file system monitoring system.

This module provides the fundamental abstractions and interfaces for the 
file system monitoring system, including event types, exception classes,
and the listener interface.
"""

# Re-export key types from core modules for easier access
from .event_types import EventType, FileSystemEvent
from .exceptions import (
    FileSystemMonitorError, WatchNotActiveError, WatchCreationError, PatternError,
    SymlinkError, PathResolutionError, WatchLimitExceededError, ListenerRegistrationError,
    NotASymlinkError, DirectoryAccessError, ResourceExhaustedError
)
from .listener import FileSystemEventListener, BaseFileSystemEventListener
from .handle import WatchHandle
from .path_utils import (
    resolve_path, pattern_to_regex, matches_pattern, 
    find_matching_files, is_subpath, is_log_file, get_common_parent_dir
)

# Define what's available when doing "from fs_monitor.core import *"
__all__ = [
    # From event_types
    'EventType',
    'FileSystemEvent',
    
    # From exceptions
    'FileSystemMonitorError',
    'WatchNotActiveError',
    'WatchCreationError',
    'PatternError',
    'SymlinkError',
    'PathResolutionError',
    'WatchLimitExceededError',
    'ListenerRegistrationError',
    'NotASymlinkError',
    'DirectoryAccessError',
    'ResourceExhaustedError',
    
    # From listener
    'FileSystemEventListener',
    'BaseFileSystemEventListener',
    
    # From handle
    'WatchHandle',
    
    # From path_utils
    'resolve_path',
    'pattern_to_regex',
    'matches_pattern',
    'find_matching_files',
    'is_subpath',
    'is_log_file',
    'get_common_parent_dir',
]
