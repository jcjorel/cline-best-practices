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
# Provides the public API for the fs_monitor module, exposing the core
# functionality for file system event monitoring. This file acts as the main
# entry point for interacting with the fs_monitor subsystem.
###############################################################################
# [Source file design principles]
# - Expose only stable public APIs
# - Hide implementation details from consumers
# - Provide convenient imports for commonly used classes
# - Support backward compatibility for existing code
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility
# - Should avoid exposing implementation details
###############################################################################
# [Dependencies]
# codebase:src/dbp/fs_monitor/core/__init__.py
# codebase:src/dbp/fs_monitor/dispatch/__init__.py
# codebase:src/dbp/fs_monitor/platforms/__init__.py
# codebase:src/dbp/fs_monitor/platforms/factory.py
# codebase:src/dbp/fs_monitor/component.py
# codebase:src/dbp/fs_monitor/git_filter.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:54:00Z : Updated __init__.py for fs_monitor reorganization by CodeAssistant
# * Updated imports to use new module structure
# * Reorganized exports to maintain backward compatibility
###############################################################################

"""
File system monitoring module for the DBP system.

This module provides functionality for monitoring file system events such as
file creation, modification, deletion, and moves.
"""

# Re-export core types
from .core import (
    ChangeType, ChangeEvent, FileSystemListener, WatchHandle,
    FSMonitorError, WatchError, WatchLimitError, WatchExistsError,
    WatchNotFoundError, PlatformNotSupportedError
)

# Re-export top-level component and factory
from .component import FSMonitorComponent
from .platforms.factory import FileSystemMonitorFactory
from .git_filter import FilterComponent, GitIgnoreFilter

# Backward compatibility exports from platforms
from .platforms import (
    MonitorBase, LinuxMonitor, PollingMonitor
)

# Define public exports
__all__ = [
    # Core exports
    'ChangeType',
    'ChangeEvent',
    'FileSystemListener',
    'WatchHandle',
    
    # Error types
    'FSMonitorError',
    'WatchError',
    'WatchLimitError',
    'WatchExistsError',
    'WatchNotFoundError',
    'PlatformNotSupportedError',
    
    # Components
    'FSMonitorComponent',
    'FilterComponent',
    
    # Factory
    'FileSystemMonitorFactory',
    
    # Monitor implementations
    'MonitorBase',
    'LinuxMonitor',
    'PollingMonitor',
    
    # Utilities
    'GitIgnoreFilter',
]
