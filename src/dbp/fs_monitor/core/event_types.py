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
# This file defines the event types and data structures for the file system monitoring system.
# It provides enumerations for different types of file system events and a data class
# for representing event instances with all relevant information.
###############################################################################
# [Source file design principles]
# - Comprehensive coverage of all filesystem event types (files, directories, symlinks)
# - Clear separation between different event categories
# - Type-safe event representation using Python's enum system
# - Immutable data structures for event information
# - Support for specialized event attributes like symlink targets
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with existing event consumers
# - Event types must be distinguishable for proper dispatch to listener methods
# - Event data must include all information needed by event handlers
###############################################################################
# [Dependencies]
# system:enum
# system:dataclasses
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-04-28T23:48:00Z : Initial implementation of event types for fs_monitor redesign by CodeAssistant
# * Created EventType enum for all filesystem event types
# * Implemented FileSystemEvent dataclass for event representation
# * Added helper methods to categorize event types
###############################################################################

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
