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
# Exports platform-specific file system monitor implementations, providing access to
# the concrete monitor implementations for different operating systems and a fallback
# polling monitor. Serves as the central access point for all platform-specific code.
###############################################################################
# [Source file design principles]
# - Explicit exports of all public platform-specific monitor implementations
# - Simplified import paths for commonly used monitor classes
# - Maintains clean separation between public API and implementation details
# - Abstracts platform-specific implementation details from consumers
###############################################################################
# [Source file constraints]
# - Should not include implementation code, only re-exports from submodules
# - Must maintain backwards compatibility for public APIs
###############################################################################
# [Dependencies]
# codebase:src/dbp/fs_monitor/platforms/monitor_base.py
# codebase:src/dbp/fs_monitor/platforms/linux.py
# codebase:src/dbp/fs_monitor/platforms/macos.py
# codebase:src/dbp/fs_monitor/platforms/windows.py
# codebase:src/dbp/fs_monitor/platforms/fallback.py
###############################################################################
# [GenAI tool change history]
# 2025-04-30T06:00:00Z : Updated fallback monitor import by CodeAssistant
# * Changed import from "from .fallback import PollingMonitor" 
# * To "from .fallback import FallbackMonitor as PollingMonitor"
# * Fixed "cannot import name 'PollingMonitor'" error
# 2025-04-29T00:51:00Z : Created platforms/__init__.py as part of fs_monitor reorganization by CodeAssistant
# * Added exports for platform-specific monitor implementations
# * Added header documentation
###############################################################################

"""
Platform-specific file system monitor implementations.

This module provides concrete implementations of file system monitors for
different operating systems as well as a fallback polling monitor. Each
monitor implementation follows the common interface defined by MonitorBase.
"""

# Re-export key types from platform modules for easier access
from .monitor_base import MonitorBase
from .linux import LinuxMonitor
from .fallback import FallbackMonitor as PollingMonitor

# Conditionally import platform-specific monitors if they exist
# These are placeholders for future implementations
try:
    from .macos import MacOSMonitor
    _has_macos = True
except ImportError:
    _has_macos = False

try:
    from .windows import WindowsMonitor
    _has_windows = True
except ImportError:
    _has_windows = False

# Define what's available when doing "from fs_monitor.platforms import *"
__all__ = [
    # From monitor_base
    'MonitorBase',
    
    # Always available platforms
    'LinuxMonitor',
    'PollingMonitor',
]

# Add platform-specific monitors to __all__ if they exist
if _has_macos:
    __all__.append('MacOSMonitor')
if _has_windows:
    __all__.append('WindowsMonitor')
