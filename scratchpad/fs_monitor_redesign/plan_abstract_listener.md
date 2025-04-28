# File System Monitor Redesign: Abstract Listener Implementation Plan

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the abstract listener class for the fs_monitor component, which forms the foundation of the listener-based architecture. The abstract listener class defines the interface for objects that can receive notifications when filesystem events occur for files matching specific patterns.

## Implementation Details

### File Structure

The implementation will involve creating or modifying the following files:

1. `src/dbp/fs_monitor/event_types.py` - Event type definitions
2. `src/dbp/fs_monitor/listener.py` - Abstract listener class and related interfaces
3. `src/dbp/fs_monitor/exceptions.py` - Custom exception classes
4. `src/dbp/fs_monitor/handle.py` - Watch handle implementation

### Event Types

First, we need to define event types that the filesystem monitor will detect and dispatch to listeners:

```python
# src/dbp/fs_monitor/event_types.py

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class EventType(Enum):
    """
    [Class intent]
    Defines the types of file system events that can be detected and dispatched.
    
    [Design principles]
    - Comprehensive coverage of all filesystem event types
    - Clear separation between file and directory events
    - Support for symlink events
    
    [Implementation details]
    - Uses Python's Enum for type safety
    - Each event type has a specific semantic meaning
    """
    
    FILE_CREATED = auto()
    FILE_MODIFIED = auto()
    FILE_DELETED = auto()
    
    DIRECTORY_CREATED = auto()
    DIRECTORY_DELETED = auto()
    
    SYMLINK_CREATED = auto()
    SYMLINK_DELETED = auto()
    SYMLINK_TARGET_CHANGED = auto()
    
    @classmethod
    def is_file_event(cls, event_type) -> bool:
        """
        [Function intent]
        Determines if the event type is related to a file.
        
        [Design principles]
        - Simple categorization of events
        
        [Implementation details]
        - Checks if the event type is one of the file-related events
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if the event is file-related, False otherwise
        """
        return event_type in (cls.FILE_CREATED, cls.FILE_MODIFIED, cls.FILE_DELETED)
    
    @classmethod
    def is_directory_event(cls, event_type) -> bool:
        """
        [Function intent]
        Determines if the event type is related to a directory.
        
        [Design principles]
        - Simple categorization of events
        
        [Implementation details]
        - Checks if the event type is one of the directory-related events
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if the event is directory-related, False otherwise
        """
        return event_type in (cls.DIRECTORY_CREATED, cls.DIRECTORY_DELETED)
    
    @classmethod
    def is_symlink_event(cls, event_type) -> bool:
        """
        [Function intent]
        Determines if the event type is related to a symlink.
        
        [Design principles]
        - Simple categorization of events
        
        [Implementation details]
        - Checks if the event type is one of the symlink-related events
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if the event is symlink-related, False otherwise
        """
        return event_type in (cls.SYMLINK_CREATED, cls.SYMLINK_DELETED, cls.SYMLINK_TARGET_CHANGED)


@dataclass
class FileSystemEvent:
    """
    [Class intent]
    Represents a file system event with all relevant information.
    
    [Design principles]
    - Complete event information
    - Immutable data structure
    - Support for all event types
    
    [Implementation details]
    - Uses dataclass for concise representation
    - Includes specific fields for symlink target information
    
    Attributes:
        event_type: The type of the event
        path: Absolute path to the affected file or directory
        old_target: Previous target path for symlink target change events (None for other events)
        new_target: New target path for symlink target change events (None for other events)
    """
    
    event_type: EventType
    path: str
    old_target: Optional[str] = None  # Only for SYMLINK_TARGET_CHANGED
    new_target: Optional[str] = None  # Only for SYMLINK_CREATED or SYMLINK_TARGET_CHANGED
```

### Abstract Listener Class

Next, we'll define the abstract listener class as the main interface for receiving filesystem events:

```python
# src/dbp/fs_monitor/listener.py

from abc import ABC, abstractmethod
from typing import Callable, Optional, List

class FileSystemEventListener(ABC):
    """
    [Class intent]
    Defines the interface for objects that can receive file system change notifications.
    
    [Design principles]
    - Separation of event specification from event handling
    - Flexible path matching with wildcards
    - Optional programmatic filtering
    - Configurable debounce delay
    - Complete coverage of all filesystem event types
    
    [Implementation details]
    - Abstract class that must be inherited by concrete listeners
    - Path patterns use Unix-style wildcards (*, **, ?)
    - Filter function allows for fine-grained control beyond path matching
    - Handles both file and directory events
    - Provides specific methods for symlink operations
    """
    
    @abstractmethod
    def on_file_created(self, path: str) -> None:
        """
        [Function intent]
        Called when a file matching the pattern is created.
        
        [Design principles]
        - Specific event handling for file creation
        
        [Implementation details]
        - Receives the absolute path to the created file
        
        Args:
            path: Absolute path to the created file
        """
        pass
        
    @abstractmethod
    def on_file_modified(self, path: str) -> None:
        """
        [Function intent]
        Called when a file matching the pattern is modified.
        
        [Design principles]
        - Specific event handling for file modification
        
        [Implementation details]
        - Receives the absolute path to the modified file
        
        Args:
            path: Absolute path to the modified file
        """
        pass
        
    @abstractmethod
    def on_file_deleted(self, path: str) -> None:
        """
        [Function intent]
        Called when a file matching the pattern is deleted.
        
        [Design principles]
        - Specific event handling for file deletion
        
        [Implementation details]
        - Receives the absolute path to the deleted file
        
        Args:
            path: Absolute path to the deleted file
        """
        pass
    
    @abstractmethod
    def on_directory_created(self, path: str) -> None:
        """
        [Function intent]
        Called when a directory matching the pattern is created.
        
        [Design principles]
        - Specific event handling for directory creation
        
        [Implementation details]
        - Receives the absolute path to the created directory
        
        Args:
            path: Absolute path to the created directory
        """
        pass
        
    @abstractmethod
    def on_directory_deleted(self, path: str) -> None:
        """
        [Function intent]
        Called when a directory matching the pattern is deleted.
        
        [Design principles]
        - Specific event handling for directory deletion
        
        [Implementation details]
        - Receives the absolute path to the deleted directory
        
        Args:
            path: Absolute path to the deleted directory
        """
        pass
    
    @abstractmethod
    def on_symlink_created(self, path: str, target: str) -> None:
        """
        [Function intent]
        Called when a symbolic link matching the pattern is created.
        
        [Design principles]
        - Specific event handling for symlink creation
        - Includes target path information
        
        [Implementation details]
        - Receives the absolute path to the symlink and its target
        
        Args:
            path: Absolute path to the symbolic link
            target: Absolute path that the symlink points to
        """
        pass
        
    @abstractmethod
    def on_symlink_deleted(self, path: str) -> None:
        """
        [Function intent]
        Called when a symbolic link matching the pattern is deleted.
        
        [Design principles]
        - Specific event handling for symlink deletion
        
        [Implementation details]
        - Receives the absolute path to the deleted symlink
        
        Args:
            path: Absolute path to the deleted symbolic link
        """
        pass
        
    @abstractmethod
    def on_symlink_target_changed(self, path: str, old_target: str, new_target: str) -> None:
        """
        [Function intent]
        Called when a symbolic link's target is changed.
        
        [Design principles]
        - Specific event handling for symlink target changes
        - Includes both old and new target information
        
        [Implementation details]
        - Receives the absolute path to the symlink and its old and new targets
        
        Args:
            path: Absolute path to the symbolic link
            old_target: Previous target path
            new_target: New target path
        """
        pass
    
    @property
    @abstractmethod
    def path_pattern(self) -> str:
        """
        [Function intent]
        Gets the pattern used to match file paths for this listener.
        
        [Design principles]
        - Flexible path matching
        - Support for Unix-style wildcards
        
        [Implementation details]
        - Path patterns can include *, **, and ? wildcards
        - Relative paths are interpreted as relative to the Git root
        
        Returns:
            A string pattern for matching file paths
        """
        pass
    
    @property
    def filter_function(self) -> Optional[Callable[[str], bool]]:
        """
        [Function intent]
        Gets the optional filter function that provides additional filtering beyond path matching.
        
        [Design principles]
        - Programmatic filtering for complex cases
        - Optional component for simple use cases
        
        [Implementation details]
        - Returns None by default (no additional filtering)
        - When provided, filter must return True for paths to be included
        
        Returns:
            A function that takes a path and returns True if the path should be included,
            or None if no additional filtering is needed
        """
        return None
    
    @property
    def debounce_delay_ms(self) -> int:
        """
        [Function intent]
        Gets the delay in milliseconds before dispatching events for this listener.
        
        [Design principles]
        - Configurable performance tuning
        - Protection against notification storms
        
        [Implementation details]
        - Default value is 100ms to prevent notification storms during rapid changes
        - Can be overridden by subclasses for different delay values
        
        Returns:
            Delay in milliseconds
        """
        return 100
```

### Base Implementation

To make it easier for clients to implement listeners, we'll provide a base implementation that allows them to override only the methods they need:

```python
# src/dbp/fs_monitor/listener.py (continued)

class BaseFileSystemEventListener(FileSystemEventListener):
    """
    [Class intent]
    Provides a base implementation of FileSystemEventListener that clients can extend.
    
    [Design principles]
    - Simplify implementation for clients
    - Allow selective override of event handlers
    
    [Implementation details]
    - Implements all methods with default no-op implementations
    - Requires only path_pattern to be implemented by subclasses
    """
    
    def on_file_created(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for file creation events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
        
    def on_file_modified(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for file modification events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
        
    def on_file_deleted(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for file deletion events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
    
    def on_directory_created(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for directory creation events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
        
    def on_directory_deleted(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for directory deletion events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
    
    def on_symlink_created(self, path: str, target: str) -> None:
        """
        [Function intent]
        Default no-op implementation for symlink creation events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
        
    def on_symlink_deleted(self, path: str) -> None:
        """
        [Function intent]
        Default no-op implementation for symlink deletion events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
        
    def on_symlink_target_changed(self, path: str, old_target: str, new_target: str) -> None:
        """
        [Function intent]
        Default no-op implementation for symlink target change events.
        
        [Design principles]
        - Allow selective override of event handlers
        
        [Implementation details]
        - Does nothing by default
        """
        pass
```

### Watch Handle

Next, we'll implement the watch handle class that provides methods to interact with and manage a registered watch:

```python
# src/dbp/fs_monitor/handle.py

from typing import List, Set, Callable
from .listener import FileSystemEventListener

class WatchHandle:
    """
    [Class intent]
    Provides methods to interact with and manage a registered watch.
    
    [Design principles]
    - Encapsulates watch management operations
    - Provides information about watched resources
    
    [Implementation details]
    - Maintains reference to internal watch data
    - Delegates unregistration to the watch manager
    """
    
    def __init__(self, listener: FileSystemEventListener, 
                 watched_paths: Set[str], 
                 unregister_callback: Callable[[], None]) -> None:
        """
        [Function intent]
        Creates a new watch handle.
        
        [Design principles]
        - Simple initialization with necessary references
        
        [Implementation details]
        - Stores the listener and watched paths
        - Takes a callback for unregistration
        
        Args:
            listener: The registered listener
            watched_paths: Set of absolute paths being watched
            unregister_callback: Function to call to unregister the watch
        """
        self._listener = listener
        self._watched_paths = watched_paths.copy()  # Make a copy to avoid external modification
        self._unregister_callback = unregister_callback
        self._active = True
    
    def list_watched_paths(self) -> List[str]:
        """
        [Function intent]
        List all paths currently being watched by this handle.
        
        [Design principles]
        - Provide transparency into watched resources
        
        [Implementation details]
        - Returns a new list to avoid external modification
        
        Returns:
            List of absolute paths being watched
        """
        return list(self._watched_paths)
    
    def is_active(self) -> bool:
        """
        [Function intent]
        Check if this watch is still active.
        
        [Design principles]
        - Allow state verification
        
        [Implementation details]
        - Returns the current active state
        
        Returns:
            True if the watch is active, False if it has been unregistered
        """
        return self._active
    
    def unregister(self) -> None:
        """
        [Function intent]
        Unregister this watch.
        
        [Design principles]
        - Clean resource management
        
        [Implementation details]
        - Calls the unregister callback
        - Sets the active flag to False
        - Clears the watched paths
        
        Raises:
            WatchNotActiveError: If the watch is already inactive
        """
        if not self._active:
            from .exceptions import WatchNotActiveError
            raise WatchNotActiveError("Watch is not active")
            
        self._unregister_callback()
        self._active = False
        self._watched_paths.clear()
```

### Custom Exceptions

Finally, we'll define custom exception classes for file system monitor operations:

```python
# src/dbp/fs_monitor/exceptions.py

class FileSystemMonitorError(Exception):
    """
    [Class intent]
    Base class for all file system monitor exceptions.
    
    [Design principles]
    - Hierarchical exception structure
    - Clear error categorization
    
    [Implementation details]
    - Inherits from the standard Exception class
    - Parent class for all fs_monitor-specific exceptions
    """
    pass

class WatchNotActiveError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when operations are attempted on an inactive watch.
    
    [Design principles]
    - Specific error type for inactive watch operations
    
    [Implementation details]
    - Raised when unregister() is called on an already unregistered watch
    """
    pass

class WatchCreationError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a watch cannot be created.
    
    [Design principles]
    - Specific error type for watch creation failures
    
    [Implementation details]
    - Raised when there's a problem creating an OS-level watch
    """
    pass

class PatternError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a path pattern is invalid.
    
    [Design principles]
    - Validation of user input
    
    [Implementation details]
    - Raised when a path pattern contains invalid wildcard usage
    """
    pass

class SymlinkError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised for symlink-related errors.
    
    [Design principles]
    - Specific error type for symlink operations
    
    [Implementation details]
    - Raised for symlink resolution or recursion errors
    """
    pass

class PathResolutionError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a path cannot be resolved.
    
    [Design principles]
    - Specific error type for path resolution failures
    
    [Implementation details]
    - Raised when Git root cannot be found or paths are invalid
    """
    pass
```

## Testing Strategy

The abstract listener implementation should be tested with the following strategies:

1. **Unit Tests**: Test each class and method in isolation
2. **Type Checking**: Use mypy to ensure type safety
3. **Documentation Verification**: Ensure all methods are properly documented

Specific test cases should include:

1. **EventType Tests**:
   - Verify that event type classification methods work correctly
   - Test all enum values

2. **FileSystemEvent Tests**:
   - Create instances with different event types
   - Verify field values

3. **FileSystemEventListener Tests**:
   - Create mock implementations
   - Verify abstract methods are properly defined

4. **BaseFileSystemEventListener Tests**:
   - Create concrete subclasses
   - Verify default implementations do nothing

5. **WatchHandle Tests**:
   - Test list_watched_paths returns correct paths
   - Test is_active returns correct state
   - Test unregister calls callback and updates state
   - Test unregister raises exception when inactive

## Integration with Other Components

The abstract listener implementation will be used by:

1. **Watch Manager**: To store and track registered listeners
2. **Event Dispatcher**: To dispatch events to the appropriate listeners
3. **Platform-Specific Implementations**: To generate the events

## Migration Considerations

When migrating from the old change_queue implementation, developers will need to:

1. Create a concrete implementation of FileSystemEventListener
2. Override the methods they need (possibly using BaseFileSystemEventListener)
3. Define a path pattern
4. Register the listener with the fs_monitor component

Example migration code should be provided in the documentation.

## Next Steps

After implementing the abstract listener class:

1. Update plan_progress.md to mark this task as completed
2. Move on to implementing the watch manager
3. Create the event dispatcher
4. Implement platform-specific monitors
