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
# This file defines the abstract listener interface for receiving file system events.
# It provides a structured way for client code to subscribe to and handle file system
# changes through specialized methods for different event types.
###############################################################################
# [Source file design principles]
# - Separation of event specification from event handling
# - Flexible path matching with wildcards
# - Optional programmatic filtering for fine-grained control
# - Configurable debounce delay to prevent notification storms
# - Complete coverage of all filesystem event types (files, directories, symlinks)
# - Clear interface definition to simplify implementation by clients
###############################################################################
# [Source file constraints]
# - Must provide specific methods for all event types
# - Must maintain backward compatibility with existing file system event handlers
# - Abstract class must be easy to implement by client code
# - Path pattern property is mandatory for all implementations
# - Filter function and debounce delay are optional with reasonable defaults
###############################################################################
# [Dependencies]
# system:abc
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-04-28T23:50:00Z : Initial implementation of abstract listener class for fs_monitor redesign by CodeAssistant
# * Created FileSystemEventListener abstract base class
# * Implemented BaseFileSystemEventListener with default no-op methods
# * Added comprehensive docstrings for all methods
###############################################################################

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
