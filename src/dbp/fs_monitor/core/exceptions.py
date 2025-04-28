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
# This file defines custom exceptions for the file system monitoring component.
# It provides a hierarchy of exception classes that help identify and handle
# various error conditions that may occur during file system monitoring operations.
###############################################################################
# [Source file design principles]
# - Hierarchical exception structure for clear error categorization
# - Specific exception types for different error conditions
# - Meaningful error messages for easier debugging
# - Consistent implementation of the "throw on error" approach
# - No silent error handling or fallbacks
###############################################################################
# [Source file constraints]
# - All exceptions must derive from the base FileSystemMonitorError class
# - Exception messages must be descriptive and include context information
# - No generic exceptions (like ValueError) should be raised directly
###############################################################################
# [Dependencies]
# None
###############################################################################
# [GenAI tool change history]
# 2025-04-28T23:49:00Z : Initial implementation of exception classes for fs_monitor redesign by CodeAssistant
# * Created base FileSystemMonitorError class
# * Implemented specific exception classes for various error conditions
# * Added detailed docstrings for all exception classes
###############################################################################


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


class WatchLimitExceededError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when the maximum number of watches is exceeded.
    
    [Design principles]
    - Resource limit enforcement
    - Clear feedback on system constraints
    
    [Implementation details]
    - Raised when the system cannot create more watches due to resource limits
    """
    pass


class ListenerRegistrationError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a listener cannot be registered.
    
    [Design principles]
    - Specific error type for registration failures
    
    [Implementation details]
    - Raised when there's a problem registering a listener
    """
    pass


class NotASymlinkError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a path expected to be a symlink is not.
    
    [Design principles]
    - Type validation for symlink operations
    
    [Implementation details]
    - Raised when get_symlink_target is called on a non-symlink path
    """
    pass


class DirectoryAccessError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when a directory cannot be accessed.
    
    [Design principles]
    - Permission and access control error handling
    
    [Implementation details]
    - Raised when there's a problem accessing a directory due to permissions
    """
    pass


class ResourceExhaustedError(FileSystemMonitorError):
    """
    [Class intent]
    Exception raised when system resources are exhausted.
    
    [Design principles]
    - Resource management
    
    [Implementation details]
    - Raised when system resources (like file handles) are exhausted
    """
    pass
