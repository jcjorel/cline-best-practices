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
# Fs Monitor package for the Documentation-Based Programming system.
# Implements file system monitoring for detecting changes to documentation and code.
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


# src/dbp/fs_monitor/__init__.py

"""
File System Monitoring package for the Documentation-Based Programming system.

Provides platform-specific and fallback mechanisms for detecting file changes
and queuing them for processing.

Key components:
- FileSystemMonitorFactory: Creates the appropriate monitor for the OS.
- FileSystemMonitor: Abstract base class for monitors.
- ChangeEvent: Data class for change events.
- ChangeDetectionQueue: Thread-safe queue with debouncing.
- GitIgnoreFilter: Filters paths based on .gitignore rules.
"""

from .base import FileSystemMonitor, ChangeEvent, ChangeType
from .queue import ChangeDetectionQueue
from .filter import GitIgnoreFilter
from .factory import FileSystemMonitorFactory

# Platform-specific monitors (importing them might raise errors if deps are missing)
try:
    from .linux import LinuxFileSystemMonitor
except ImportError:
    LinuxFileSystemMonitor = None # type: ignore
try:
    from .macos import MacOSFileSystemMonitor
except ImportError:
    MacOSFileSystemMonitor = None # type: ignore
try:
    from .windows import WindowsFileSystemMonitor
except ImportError:
    WindowsFileSystemMonitor = None # type: ignore
from .fallback import FallbackFileSystemMonitor


__all__ = [
    "FileSystemMonitorFactory",
    "FileSystemMonitor",
    "ChangeEvent",
    "ChangeType",
    "ChangeDetectionQueue",
    "GitIgnoreFilter",
    # Expose specific monitors only if they are likely available
    "LinuxFileSystemMonitor",
    "MacOSFileSystemMonitor",
    "WindowsFileSystemMonitor",
    "FallbackFileSystemMonitor",
]
