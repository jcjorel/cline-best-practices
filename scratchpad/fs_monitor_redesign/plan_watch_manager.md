# File System Monitor Redesign: Watch Manager Implementation Plan

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the watch manager for the fs_monitor component. The watch manager is responsible for:

1. Maintaining a registry of file system event listeners
2. Managing path patterns and filter functions
3. Handling watch creation and resource management
4. Supporting wildcard pattern matching
5. Coordinating with platform-specific monitor implementations

## Implementation Details

### File Structure

The implementation will involve creating or modifying the following files:

1. `src/dbp/fs_monitor/watch_manager.py` - Watch manager implementation
2. `src/dbp/fs_monitor/path_utils.py` - Path resolution and pattern matching utilities
3. `src/dbp/fs_monitor/resource_tracker.py` - Resource reference counting system
4. `src/dbp/fs_monitor/__init__.py` - Public API exposure

### Resource Tracker

First, we'll implement a resource tracker to efficiently manage OS-level watches:

```python
# src/dbp/fs_monitor/resource_tracker.py

import os
from typing import Dict, Set, Optional, Callable, Any
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ResourceData:
    """
    [Class intent]
    Stores data for a watched resource with reference counting.
    
    [Design principles]
    - Efficient resource management
    - Support for reference counting
    - Association with OS-specific handlers
    
    [Implementation details]
    - Maintains a reference count for each watched path
    - Stores platform-specific watch descriptor or handle
    - Tracks the listeners interested in this resource
    
    Attributes:
        ref_count: Number of watches for this resource
        os_descriptor: Platform-specific watch descriptor (e.g., inotify watch descriptor)
        platform_data: Additional platform-specific data needed for this watch
        path: Absolute path of the watched resource
        listeners: Set of listener IDs interested in this resource
    """
    path: str
    ref_count: int = 1
    os_descriptor: Optional[int] = None
    platform_data: Any = None
    listeners: Set[int] = field(default_factory=set)


class ResourceTracker:
    """
    [Class intent]
    Manages resource reference counting for efficient OS-level watches.
    
    [Design principles]
    - Minimize OS-level watches through reference counting
    - Track resource usage across listeners
    - Support for OS-specific watch descriptors
    
    [Implementation details]
    - Maps absolute paths to ResourceData objects
    - Maps OS watch descriptors back to paths for event handling
    - Provides methods for incrementing and decrementing references
    - Automatically cleans up resources when reference count reaches zero
    """
    
    def __init__(self, resource_cleanup_callback: Callable[[str, Any], None]) -> None:
        """
        [Function intent]
        Initialize a new resource tracker.
        
        [Design principles]
        - Clean initialization
        - Support for resource cleanup
        
        [Implementation details]
        - Initializes empty data structures
        - Stores callback for resource cleanup
        
        Args:
            resource_cleanup_callback: Function to call when a resource's reference count reaches zero
        """
        self._resources: Dict[str, ResourceData] = {}
        self._descriptor_to_path: Dict[int, str] = {}
        self._cleanup_callback = resource_cleanup_callback
    
    def add_resource(self, path: str, listener_id: int) -> ResourceData:
        """
        [Function intent]
        Add a resource or increment its reference count.
        
        [Design principles]
        - Efficient resource reuse
        - Automatic reference counting
        
        [Implementation details]
        - Increments reference count if resource already exists
        - Creates new ResourceData if not
        - Associates listener with resource
        
        Args:
            path: Absolute path to the resource
            listener_id: ID of the listener interested in this resource
            
        Returns:
            The ResourceData object for the resource
        """
        path = os.path.abspath(path)
        
        if path in self._resources:
            resource = self._resources[path]
            resource.ref_count += 1
            resource.listeners.add(listener_id)
            logger.debug(f"Incremented reference count for {path} to {resource.ref_count}")
            return resource
        
        resource = ResourceData(path=path)
        resource.listeners.add(listener_id)
        self._resources[path] = resource
        logger.debug(f"Added new resource {path}")
        return resource
    
    def remove_resource(self, path: str, listener_id: int) -> bool:
        """
        [Function intent]
        Remove a resource or decrement its reference count.
        
        [Design principles]
        - Clean resource management
        - Automatic cleanup when no longer needed
        
        [Implementation details]
        - Decrements reference count
        - Removes listener association
        - Calls cleanup callback when reference count reaches zero
        - Removes from internal tracking when no longer referenced
        
        Args:
            path: Absolute path to the resource
            listener_id: ID of the listener to remove
            
        Returns:
            True if the resource was removed completely, False if only the reference count was decremented
        """
        path = os.path.abspath(path)
        
        if path not in self._resources:
            logger.warning(f"Attempted to remove non-existent resource {path}")
            return False
        
        resource = self._resources[path]
        resource.listeners.discard(listener_id)
        resource.ref_count -= 1
        logger.debug(f"Decremented reference count for {path} to {resource.ref_count}")
        
        if resource.ref_count <= 0:
            # Clean up the resource
            if resource.os_descriptor is not None:
                self._descriptor_to_path.pop(resource.os_descriptor, None)
                self._cleanup_callback(path, resource.os_descriptor)
                
            del self._resources[path]
            logger.debug(f"Removed resource {path} completely")
            return True
        
        return False
    
    def get_resource(self, path: str) -> Optional[ResourceData]:
        """
        [Function intent]
        Get the ResourceData for a path.
        
        [Design principles]
        - Simple data access
        
        [Implementation details]
        - Returns ResourceData if it exists, None otherwise
        
        Args:
            path: Absolute path to the resource
            
        Returns:
            ResourceData object if found, None otherwise
        """
        path = os.path.abspath(path)
        return self._resources.get(path)
    
    def get_resource_by_descriptor(self, descriptor: int) -> Optional[ResourceData]:
        """
        [Function intent]
        Get the ResourceData for an OS descriptor.
        
        [Design principles]
        - Support for platform-specific event handling
        
        [Implementation details]
        - Maps OS descriptor back to path, then gets resource
        
        Args:
            descriptor: OS-specific watch descriptor
            
        Returns:
            ResourceData object if found, None otherwise
        """
        path = self._descriptor_to_path.get(descriptor)
        if path:
            return self._resources.get(path)
        return None
    
    def set_os_descriptor(self, path: str, descriptor: int, platform_data: Any = None) -> None:
        """
        [Function intent]
        Set the OS descriptor for a watched resource.
        
        [Design principles]
        - Support for platform-specific watch management
        
        [Implementation details]
        - Updates ResourceData with OS descriptor
        - Updates reverse mapping
        
        Args:
            path: Absolute path to the resource
            descriptor: OS-specific watch descriptor
            platform_data: Optional platform-specific data
        """
        path = os.path.abspath(path)
        if path not in self._resources:
            logger.warning(f"Attempted to set descriptor for non-existent resource {path}")
            return
        
        resource = self._resources[path]
        resource.os_descriptor = descriptor
        resource.platform_data = platform_data
        self._descriptor_to_path[descriptor] = path
    
    def get_all_paths(self) -> Set[str]:
        """
        [Function intent]
        Get all currently watched paths.
        
        [Design principles]
        - Support for debugging and diagnostic information
        
        [Implementation details]
        - Returns a copy of all keys in the resources dictionary
        
        Returns:
            Set of all absolute paths being watched
        """
        return set(self._resources.keys())
    
    def get_listeners_for_path(self, path: str) -> Set[int]:
        """
        [Function intent]
        Get all listeners interested in a path.
        
        [Design principles]
        - Support for event dispatching
        
        [Implementation details]
        - Returns set of listener IDs for a path
        
        Args:
            path: Absolute path to the resource
            
        Returns:
            Set of listener IDs interested in this path
        """
        path = os.path.abspath(path)
        if path in self._resources:
            return set(self._resources[path].listeners)
        return set()
```

### Path Utilities

Next, we'll implement pattern matching and path resolution utilities:

```python
# src/dbp/fs_monitor/path_utils.py

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
                for item in os.listdir(current_dir):
                    item_path = os.path.join(current_dir, item)
                    if os.path.isfile(item_path) and fnmatch.fnmatch(item, part):
                        matching_files.append(item_path)
            else:
                # Directory part
                if "*" in part or "?" in part:
                    # Wildcard in directory, need to check all subdirectories
                    for item in os.listdir(current_dir):
                        item_path = os.path.join(current_dir, item)
                        if os.path.isdir(item_path) and fnmatch.fnmatch(item, part):
                            # Recursively process matching directories
                            subpattern = os.path.sep.join(pattern_parts[i+1:])
                            matching_files.extend(find_matching_files(item_path, subpattern))
                    return matching_files
                else:
                    # No wildcard, just move to the next directory
                    current_dir = os.path.join(current_dir, part)
                    if not os.path.isdir(current_dir):
                        # If directory doesn't exist, no matches
                        return []
    
    return matching_files
```

### Watch Manager

Now, let's implement the watch manager, which is the core of our file system monitoring system:

```python
# src/dbp/fs_monitor/watch_manager.py

import os
import threading
import logging
from typing import Dict, Set, List, Optional, Callable, Tuple, Any
import uuid
import weakref

from .listener import FileSystemEventListener
from .handle import WatchHandle
from .exceptions import WatchNotActiveError, PatternError, PathResolutionError
from .resource_tracker import ResourceTracker
from .path_utils import resolve_path, pattern_to_regex, matches_pattern, find_matching_files

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
                        from .path_utils import get_git_root
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
```

### Public API

Finally, let's update the `__init__.py` file to expose the public API:

```python
# src/dbp/fs_monitor/__init__.py

from .listener import FileSystemEventListener, BaseFileSystemEventListener
from .handle import WatchHandle
from .exceptions import (
    FileSystemMonitorError, 
    WatchNotActiveError, 
    WatchCreationError, 
    PatternError, 
    SymlinkError, 
    PathResolutionError
)
from .event_types import EventType, FileSystemEvent
from .watch_manager import WatchManager

# These will be imported by the component class
__all__ = [
    'FileSystemEventListener',
    'BaseFileSystemEventListener',
    'WatchHandle',
    'FileSystemMonitorError',
    'WatchNotActiveError',
    'WatchCreationError',
    'PatternError',
    'SymlinkError',
    'PathResolutionError',
    'EventType',
    'FileSystemEvent',
    'WatchManager'
]
```

## Testing Strategy

The watch manager implementation should be tested with the following strategies:

1. **Unit Tests**:
   - Test pattern matching with various patterns
   - Test listener registration and unregistration
   - Test resource tracking and reference counting
   - Test path resolution and normalization

2. **Integration Tests**:
   - Test interaction between watch manager and resource tracker
   - Test with multiple listeners watching the same paths

3. **Edge Cases**:
   - Test with overlapping patterns
   - Test with invalid patterns
   - Test with non-existent paths
   - Test with relative and absolute paths

## Key Test Cases

1. **Pattern Matching**:
   - Exact match patterns (no wildcards)
   - Simple wildcard patterns (*.txt)
   - Recursive wildcard patterns (**/*.txt)
   - Multiple wildcards in one pattern (src/*.py)
   - Single character wildcards (file?.txt)

2. **Registration and Unregistration**:
   - Register multiple listeners
   - Register listener with complex pattern
   - Unregister listener
   - Try to unregister non-existent listener

3. **Resource Management**:
   - Multiple listeners
