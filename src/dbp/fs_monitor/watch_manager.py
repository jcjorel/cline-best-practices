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
# This file implements the watch manager for the file system monitor component.
# It coordinates file system event listeners, handles watch creation and resource
# management, and provides a mechanism for efficient event dispatching.
###############################################################################
# [Source file design principles]
# - Thread-safe operations for concurrent access
# - Efficient resource management through reference counting
# - Support for wildcard pattern matching
# - Path resolution and normalization
# - Clear separation of concerns between registration and event handling
###############################################################################
# [Source file constraints]
# - Must maintain thread safety for concurrent access
# - Must handle multiple listeners watching the same resource
# - Must ensure proper resource cleanup
# - Must support path patterns with wildcards
# - Must provide efficient event routing to interested listeners
###############################################################################
# [Dependencies]
# system:os
# system:threading
# system:logging
# system:typing
# system:re
# system:uuid
# system:weakref
# codebase:src/dbp/fs_monitor/core/listener.py
# codebase:src/dbp/fs_monitor/core/handle.py
# codebase:src/dbp/fs_monitor/core/exceptions.py
# codebase:src/dbp/fs_monitor/dispatch/resource_tracker.py
# codebase:src/dbp/fs_monitor/core/path_utils.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T01:01:00Z : Updated import paths for module reorganization by CodeAssistant
# * Updated imports to use the new module structure with core/ and dispatch/ submodules
# * Updated dependencies section to reflect the new file locations
# 2025-04-29T00:02:30Z : Initial implementation of watch manager for fs_monitor redesign by CodeAssistant
# * Created WatchManager class for managing file system event listeners
# * Implemented registration and unregistration APIs
# * Added support for pattern matching and resource tracking
###############################################################################

import os
import threading
import logging
import re
from typing import Dict, Set, List, Optional, Callable, Tuple, Any

from .core.listener import FileSystemEventListener
from .core.handle import WatchHandle
from .core.exceptions import WatchNotActiveError, PatternError, PathResolutionError
from .dispatch.resource_tracker import ResourceTracker
from .core.path_utils import (
    resolve_path, 
    pattern_to_regex, 
    matches_pattern, 
    find_matching_files, 
    get_git_root
)

logger = logging.getLogger(__name__)


class WatchManager:
    """
    [Class intent]
    Manages file system event listeners and watches.
    
    [Design principles]
    - Efficient resource management
    - Thread-safe operations
    - Support for wildcard patterns
    - Path resolution and normalization
    
    [Implementation details]
    - Maintains registry of listeners
    - Uses ResourceTracker for reference counting
    - Provides registration and unregistration API
    - Handles pattern matching
    """
    
    def __init__(self) -> None:
        """
        [Function intent]
        Initialize a new watch manager.
        
        [Design principles]
        - Clean initialization
        - Thread safety
        
        [Implementation details]
        - Initializes empty registry
        - Creates a resource tracker for watch handles
        - Initializes thread lock
        """
        self._lock = threading.RLock()
        self._listeners: Dict[int, FileSystemEventListener] = {}
        self._listener_patterns: Dict[int, Tuple[str, re.Pattern, bool]] = {}
        self._listener_watches: Dict[int, Set[str]] = {}
        self._next_listener_id = 1
        self._resource_tracker = ResourceTracker(self._cleanup_resource)
    
    def register_listener(self, listener: FileSystemEventListener) -> WatchHandle:
        """
        [Function intent]
        Register a new file system event listener.
        
        [Design principles]
        - Simple API for listener registration
        - Pattern resolution and validation
        - Watch resource management
        
        [Implementation details]
        - Assigns unique ID to listener
        - Resolves and compiles pattern
        - Finds matching files
        - Creates watch handle
        
        Args:
            listener: The listener to register
            
        Returns:
            A watch handle for managing the registration
            
        Raises:
            PatternError: If the pattern is invalid
            PathResolutionError: If paths cannot be resolved
        """
        with self._lock:
            pattern = listener.path_pattern
            
            if not pattern:
                raise PatternError("Pattern cannot be empty")
            
            # Assign a unique ID to the listener
            listener_id = self._next_listener_id
            self._next_listener_id += 1
            
            # Compile the pattern to a regex
            try:
                regex, has_wildcards = pattern_to_regex(pattern)
            except Exception as e:
                raise PatternError(f"Invalid pattern: {pattern}, error: {str(e)}")
            
            # Store the listener and its pattern
            self._listeners[listener_id] = listener
            self._listener_patterns[listener_id] = (pattern, regex, has_wildcards)
            self._listener_watches[listener_id] = set()
            
            # Find all existing files that match the pattern
            try:
                matching_files = []
                
                if os.path.isabs(pattern):
                    # Absolute pattern
                    base_dir = os.path.dirname(pattern)
                    if os.path.isdir(base_dir):
                        matching_files = find_matching_files(base_dir, pattern)
                else:
                    # Try to interpret as Git root-relative
                    try:
                        git_root = get_git_root()
                        full_pattern = os.path.join(git_root, pattern)
                        base_dir = os.path.dirname(full_pattern)
                        if os.path.isdir(base_dir):
                            matching_files = find_matching_files(base_dir, full_pattern)
                    except PathResolutionError:
                        # Fall back to CWD-relative
                        base_dir = os.path.dirname(os.path.abspath(pattern))
                        if os.path.isdir(base_dir):
                            matching_files = find_matching_files(base_dir, os.path.abspath(pattern))
            except Exception as e:
                logger.error(f"Error finding matching files for pattern {pattern}: {e}")
                matching_files = []
            
            # Add resources for each matching file
            watched_paths = set()
            for file_path in matching_files:
                # Apply additional filter if provided
                if listener.filter_function and not listener.filter_function(file_path):
                    continue
                
                # Add the resource
                self._resource_tracker.add_resource(file_path, listener_id)
                watched_paths.add(file_path)
                self._listener_watches[listener_id].add(file_path)
            
            # Create a watch handle
            unregister_callback = lambda: self.unregister_listener(listener_id)
            handle = WatchHandle(listener, watched_paths, unregister_callback)
            
            logger.debug(f"Registered listener {listener_id} with pattern {pattern}")
            
            return handle
    
    def unregister_listener(self, listener_id: int) -> None:
        """
        [Function intent]
        Unregister a previously registered listener.
        
        [Design principles]
        - Clean resource management
        - Error handling
        
        [Implementation details]
        - Removes listener from registry
        - Decrements reference counts for resources
        - Cleans up watches
        
        Args:
            listener_id: ID of the listener to unregister
            
        Raises:
            WatchNotActiveError: If the listener is not registered
        """
        with self._lock:
            if listener_id not in self._listeners:
                raise WatchNotActiveError(f"Listener {listener_id} is not registered")
            
            # Get the paths being watched by this listener
            watched_paths = self._listener_watches.get(listener_id, set()).copy()
            
            # Remove resources
            for path in watched_paths:
                self._resource_tracker.remove_resource(path, listener_id)
            
            # Remove the listener from our registry
            self._listeners.pop(listener_id, None)
            self._listener_patterns.pop(listener_id, None)
            self._listener_watches.pop(listener_id, None)
            
            logger.debug(f"Unregistered listener {listener_id}")
    
    def _cleanup_resource(self, path: str, os_descriptor: Any) -> None:
        """
        [Function intent]
        Clean up resources when they are no longer needed.
        
        [Design principles]
        - Resource cleanup
        
        [Implementation details]
        - Called by ResourceTracker when reference count reaches zero
        - Placeholder for platform-specific cleanup
        
        Args:
            path: Path to the resource
            os_descriptor: OS-specific watch descriptor
        """
        # This is a placeholder - actual implementation depends on the platform
        logger.debug(f"Cleaning up resource {path} with descriptor {os_descriptor}")
        # Will be overridden by platform-specific implementations
    
    def get_matching_listeners(self, path: str) -> List[int]:
        """
        [Function intent]
        Find all listeners that should receive events for a path.
        
        [Design principles]
        - Efficient event routing
        
        [Implementation details]
        - Checks path against all registered patterns
        - Applies additional filters if provided
        
        Args:
            path: Path to check
            
        Returns:
            List of listener IDs that match the path
        """
        with self._lock:
            matching_listeners = []
            
            for listener_id, (pattern, regex, has_wildcards) in self._listener_patterns.items():
                # If no wildcards, just check for equality
                if not has_wildcards:
                    if path == pattern:
                        listener = self._listeners.get(listener_id)
                        if listener and (not listener.filter_function or listener.filter_function(path)):
                            matching_listeners.append(listener_id)
                else:
                    # Check if path matches the regex
                    if regex.match(path):
                        listener = self._listeners.get(listener_id)
                        if listener and (not listener.filter_function or listener.filter_function(path)):
                            matching_listeners.append(listener_id)
            
            return matching_listeners
    
    def add_watch(self, path: str, listener_id: int) -> None:
        """
        [Function intent]
        Add a new watch for a specific path and listener.
        
        [Design principles]
        - Support for dynamically discovered paths
        - Reference counting
        
        [Implementation details]
        - Adds resource to tracker
        - Updates listener watches
        
        Args:
            path: Absolute path to watch
            listener_id: ID of the listener to associate with this watch
        """
        with self._lock:
            if listener_id not in self._listeners:
                logger.warning(f"Attempted to add watch for non-existent listener {listener_id}")
                return
            
            path = os.path.abspath(path)
            self._resource_tracker.add_resource(path, listener_id)
            self._listener_watches[listener_id].add(path)
    
    def remove_watch(self, path: str, listener_id: int) -> None:
        """
        [Function intent]
        Remove a watch for a specific path and listener.
        
        [Design principles]
        - Support for watch cleanup
        - Reference counting
        
        [Implementation details]
        - Removes resource from tracker
        - Updates listener watches
        
        Args:
            path: Absolute path to unwatch
            listener_id: ID of the listener to disassociate from this watch
        """
        with self._lock:
            if listener_id not in self._listeners:
                logger.warning(f"Attempted to remove watch for non-existent listener {listener_id}")
                return
            
            path = os.path.abspath(path)
            self._resource_tracker.remove_resource(path, listener_id)
            self._listener_watches[listener_id].discard(path)
    
    def set_os_descriptor(self, path: str, descriptor: int, platform_data: Any = None) -> None:
        """
        [Function intent]
        Set the OS descriptor for a watched path.
        
        [Design principles]
        - Platform integration
        - Resource management
        
        [Implementation details]
        - Delegates to resource tracker
        
        Args:
            path: Absolute path
            descriptor: OS-specific watch descriptor
            platform_data: Optional platform-specific data
        """
        with self._lock:
            self._resource_tracker.set_os_descriptor(path, descriptor, platform_data)
    
    def get_listener(self, listener_id: int) -> Optional[FileSystemEventListener]:
        """
        [Function intent]
        Get a listener by ID.
        
        [Design principles]
        - Simple data access
        
        [Implementation details]
        - Retrieves listener from registry
        
        Args:
            listener_id: ID of the listener
            
        Returns:
            The listener if found, None otherwise
        """
        with self._lock:
            return self._listeners.get(listener_id)
    
    def get_all_watched_paths(self) -> Set[str]:
        """
        [Function intent]
        Get all paths being watched by any listener.
        
        [Design principles]
        - Support for debugging and diagnostics
        
        [Implementation details]
        - Delegates to resource tracker
        
        Returns:
            Set of all absolute paths being watched
        """
        with self._lock:
            return self._resource_tracker.get_all_paths()
