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
# Exports dispatch functionality for the fs_monitor module, providing access to 
# the event dispatching, debouncing, and thread management components used to process
# file system change events.
###############################################################################
# [Source file design principles]
# - Explicit exports of all public APIs from dispatch submodules
# - Simplified import paths for commonly used dispatch classes
# - Maintains clean separation between public API and implementation details
###############################################################################
# [Source file constraints]
# - Should not include implementation code, only re-exports from submodules
# - Must maintain backwards compatibility for public APIs
###############################################################################
# [Dependencies]
# codebase:src/dbp/fs_monitor/dispatch/event_dispatcher.py
# codebase:src/dbp/fs_monitor/dispatch/debouncer.py
# codebase:src/dbp/fs_monitor/dispatch/thread_manager.py
# codebase:src/dbp/fs_monitor/dispatch/resource_tracker.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:50:00Z : Created dispatch/__init__.py as part of fs_monitor reorganization by CodeAssistant
# * Added exports for dispatch module components
# * Added header documentation
###############################################################################

"""
Event dispatching functionality for the file system monitoring system.

This module provides components for processing and dispatching file system 
change events, including debouncing, thread management, and resource tracking.
"""

# Re-export key types from dispatch modules for easier access
from .event_dispatcher import EventDispatcher
from .debouncer import EventDebouncer
from .thread_manager import ThreadManager
from .resource_tracker import ResourceTracker

# Define what's available when doing "from fs_monitor.dispatch import *"
__all__ = [
    # From event_dispatcher
    'EventDispatcher',
    
    # From debouncer
    'EventDebouncer',
    
    # From thread_manager
    'ThreadManager',
    
    # From resource_tracker
    'ResourceTracker',
]
