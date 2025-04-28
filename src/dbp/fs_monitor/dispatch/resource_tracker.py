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
# This file implements a resource tracking system for the file system monitor component.
# It provides a mechanism to efficiently manage OS-level watches through reference counting,
# ensuring that only one OS-level watch is created per resource regardless of how many
# listeners are registered for that resource.
###############################################################################
# [Source file design principles]
# - Minimize OS-level watches through efficient reference counting
# - Automatic resource cleanup when no longer needed
# - Thread-safe operations
# - Support for OS-specific watch descriptors
# - Clear association between resources and their listeners
###############################################################################
# [Source file constraints]
# - Must handle concurrent access to resource data
# - Must ensure proper cleanup of resources
# - Must maintain correct reference counts
# - Must support many-to-many relationships between paths and listeners
###############################################################################
# [Dependencies]
# system:os
# system:typing
# system:dataclasses
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-04-28T23:58:30Z : Initial implementation of resource tracker for fs_monitor redesign by CodeAssistant
# * Created ResourceData class to store information about watched resources
# * Implemented ResourceTracker for reference counting and resource management
###############################################################################

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
        path: Absolute path of the watched resource
        ref_count: Number of watches for this resource
        os_descriptor: Platform-specific watch descriptor (e.g., inotify watch descriptor)
        platform_data: Additional platform-specific data needed for this watch
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
