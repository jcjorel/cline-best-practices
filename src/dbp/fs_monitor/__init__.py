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
