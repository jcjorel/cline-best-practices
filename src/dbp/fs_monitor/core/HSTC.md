# Hierarchical Semantic Tree Context: core

## Directory Purpose
This directory contains the core abstractions and interfaces for the file system monitoring system in the DBP project. It defines fundamental concepts including event types, exception hierarchies, listener interfaces, and path utilities that are used throughout the fs_monitor component. These abstractions provide a consistent foundation that allows other modules to implement platform-specific monitoring, event dispatching, and client interaction while maintaining a clean separation of concerns.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports core functionality for the fs_monitor module, providing access to 
  the fundamental classes and interfaces needed by other parts of the system.
  
source_file_design_principles: |
  - Explicit exports of all public APIs from core submodules
  - Simplified import paths for commonly used core classes
  - Maintains clean separation between public API and implementation details
  
source_file_constraints: |
  - Should not include implementation code, only re-exports from submodules
  - Must maintain backwards compatibility for public APIs
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/listener.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/handle.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/event_types.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/exceptions.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/path_utils.py
  
change_history:
  - timestamp: "2025-04-29T08:51:00Z"
    summary: "Fixed path_utils imports to match actual functions"
    details: "Updated path_utils imports to use functions that actually exist in the module, changed imports like normalize_path to resolve_path, updated __all__ list with correct path_utils function names"
  - timestamp: "2025-04-29T08:49:00Z"
    summary: "Fixed listener class name mismatches"
    details: "Updated listener import from FileSystemListener to FileSystemEventListener, added import for BaseFileSystemEventListener, updated __all__ list with correct listener class names"
  - timestamp: "2025-04-29T08:47:00Z"
    summary: "Fixed exception class name mismatches"
    details: "Updated exception imports to match actual class names in exceptions.py, changed FSMonitorError to FileSystemMonitorError, updated __all__ list with correct exception class names"
  - timestamp: "2025-04-29T00:49:00Z"
    summary: "Created core/__init__.py as part of fs_monitor reorganization"
    details: "Added exports for core module components, added header documentation"
```

### `event_types.py`
```yaml
source_file_intent: |
  This file defines the event types and data structures for the file system monitoring system.
  It provides enumerations for different types of file system events and a data class
  for representing event instances with all relevant information.
  
source_file_design_principles: |
  - Comprehensive coverage of all filesystem event types (files, directories, symlinks)
  - Clear separation between different event categories
  - Type-safe event representation using Python's enum system
  - Immutable data structures for event information
  - Support for specialized event attributes like symlink targets
  
source_file_constraints: |
  - Must maintain backward compatibility with existing event consumers
  - Event types must be distinguishable for proper dispatch to listener methods
  - Event data must include all information needed by event handlers
  
dependencies:
  - kind: system
    dependency: enum
  - kind: system
    dependency: dataclasses
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-04-28T23:48:00Z"
    summary: "Initial implementation of event types for fs_monitor redesign"
    details: "Created EventType enum for all filesystem event types, implemented FileSystemEvent dataclass for event representation, added helper methods to categorize event types"
```

### `exceptions.py`
```yaml
source_file_intent: |
  This file defines custom exceptions for the file system monitoring component.
  It provides a hierarchy of exception classes that help identify and handle
  various error conditions that may occur during file system monitoring operations.
  
source_file_design_principles: |
  - Hierarchical exception structure for clear error categorization
  - Specific exception types for different error conditions
  - Meaningful error messages for easier debugging
  - Consistent implementation of the "throw on error" approach
  - No silent error handling or fallbacks
  
source_file_constraints: |
  - All exceptions must derive from the base FileSystemMonitorError class
  - Exception messages must be descriptive and include context information
  - No generic exceptions (like ValueError) should be raised directly
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-28T23:49:00Z"
    summary: "Initial implementation of exception classes for fs_monitor redesign"
    details: "Created base FileSystemMonitorError class, implemented specific exception classes for various error conditions, added detailed docstrings for all exception classes"
```

### `listener.py`
```yaml
source_file_intent: |
  This file defines the abstract listener interface for receiving file system events.
  It provides a structured way for client code to subscribe to and handle file system
  changes through specialized methods for different event types.
  
source_file_design_principles: |
  - Separation of event specification from event handling
  - Flexible path matching with wildcards
  - Optional programmatic filtering for fine-grained control
  - Configurable debounce delay to prevent notification storms
  - Complete coverage of all filesystem event types (files, directories, symlinks)
  - Clear interface definition to simplify implementation by clients
  
source_file_constraints: |
  - Must provide specific methods for all event types
  - Must maintain backward compatibility with existing file system event handlers
  - Abstract class must be easy to implement by client code
  - Path pattern property is mandatory for all implementations
  - Filter function and debounce delay are optional with reasonable defaults
  
dependencies:
  - kind: system
    dependency: abc
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-04-28T23:50:00Z"
    summary: "Initial implementation of abstract listener class for fs_monitor redesign"
    details: "Created FileSystemEventListener abstract base class, implemented BaseFileSystemEventListener with default no-op methods, added comprehensive docstrings for all methods"
```

### `handle.py`
```yaml
source_file_intent: |
  This file defines the WatchHandle class that represents a registered file system watch.
  It provides methods for managing the lifecycle of watches and serves as a token
  that clients use to unregister watches.
  
source_file_design_principles: |
  - Resource lifetime management
  - Clean interface for watch operations
  - Support for safe unregistration
  
source_file_constraints: |
  - Must maintain reference to the watch manager
  - Must provide a unique identifier for each watch
  - Must prevent double unregistration
  
dependencies:
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-04-29T00:35:00Z"
    summary: "Created WatchHandle class for fs_monitor redesign"
    details: "Implemented WatchHandle for managing watch lifecycle, added unregister method, added safeguards against double unregistration"
```

### `path_utils.py`
```yaml
source_file_intent: |
  This file provides utility functions for working with file system paths,
  including pattern matching, path normalization, and directory traversal.
  
source_file_design_principles: |
  - Platform-independent path handling
  - Efficient path matching algorithms
  - Support for wildcard patterns
  - Robust error handling
  
source_file_constraints: |
  - Must handle platform-specific path separators
  - Must provide consistent path normalization
  - Must handle edge cases like symlinks and non-existent paths
  - Pattern matching must be efficient for large directory trees
  
dependencies:
  - kind: system
    dependency: os
  - kind: system
    dependency: pathlib
  - kind: system
    dependency: re
  
change_history:
  - timestamp: "2025-04-29T08:30:00Z"
    summary: "Added is_log_file for centralized log file detection"
    details: "Implemented is_log_file function to prevent monitoring log files and causing infinite recursion"
  - timestamp: "2025-04-28T23:55:00Z"
    summary: "Initial implementation of path utilities for fs_monitor redesign"
    details: "Created path utility functions for resolving paths, converting wildcards to regex, matching patterns, and finding matching files"
```

End of HSTC.md file
