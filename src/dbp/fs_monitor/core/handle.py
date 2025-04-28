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
# This file defines the watch handle class that provides methods to interact with
# and manage a registered file system watch. It encapsulates watch management operations
# and provides information about watched resources.
###############################################################################
# [Source file design principles]
# - Clean API for managing watch registrations
# - Encapsulation of internal watch state
# - Reference management for resource cleanup
# - Clear delineation between active and inactive watches
# - Transparency into watched resources
###############################################################################
# [Source file constraints]
# - Must maintain reference integrity with the watch manager
# - Must handle watch deactivation gracefully
# - Must prevent operations on inactive watches
# - Must provide accurate information about watched paths
###############################################################################
# [Dependencies]
# system:typing
# codebase:src/dbp/fs_monitor/listener.py
# codebase:src/dbp/fs_monitor/exceptions.py
###############################################################################
# [GenAI tool change history]
# 2025-04-28T23:51:30Z : Initial implementation of watch handle class for fs_monitor redesign by CodeAssistant
# * Created WatchHandle class for managing watch registrations
# * Implemented methods for listing watched paths, checking active status, and unregistering
###############################################################################

from typing import List, Set, Callable
from .listener import FileSystemEventListener
from .exceptions import WatchNotActiveError


class WatchHandle:
    """
    [Class intent]
    Provides methods to interact with and manage a registered watch.
    
    [Design principles]
    - Encapsulates watch management operations
    - Provides information about watched resources
    - Ensures proper resource cleanup
    
    [Implementation details]
    - Maintains reference to internal watch data
    - Delegates unregistration to the watch manager
    - Tracks active state to prevent operations on inactive watches
    """
    
    def __init__(self, listener: FileSystemEventListener, 
                 watched_paths: Set[str], 
                 unregister_callback: Callable[[], None]) -> None:
        """
        [Function intent]
        Creates a new watch handle for a registered listener.
        
        [Design principles]
        - Simple initialization with necessary references
        - Immutable internal state
        
        [Implementation details]
        - Stores the listener and watched paths
        - Takes a callback for unregistration
        - Sets initial active state to True
        
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
        Lists all paths currently being watched by this handle.
        
        [Design principles]
        - Provide transparency into watched resources
        - Return immutable copy to prevent external modification
        
        [Implementation details]
        - Returns a new list to avoid external modification
        - Paths are returned in sorted order for consistent results
        
        Returns:
            List of absolute paths being watched
            
        Raises:
            WatchNotActiveError: If the watch is not active
        """
        if not self._active:
            raise WatchNotActiveError("Cannot list paths for inactive watch")
        return sorted(list(self._watched_paths))
    
    def is_active(self) -> bool:
        """
        [Function intent]
        Checks if this watch is still active.
        
        [Design principles]
        - Allow state verification
        - Simple status query
        
        [Implementation details]
        - Returns the current active state
        
        Returns:
            True if the watch is active, False if it has been unregistered
        """
        return self._active
    
    def unregister(self) -> None:
        """
        [Function intent]
        Unregisters this watch and releases associated resources.
        
        [Design principles]
        - Clean resource management
        - Prevent duplicate unregistration
        
        [Implementation details]
        - Calls the unregister callback
        - Sets the active flag to False
        - Clears the watched paths
        
        Raises:
            WatchNotActiveError: If the watch is already inactive
        """
        if not self._active:
            raise WatchNotActiveError("Watch is not active")
            
        self._unregister_callback()
        self._active = False
        self._watched_paths.clear()
        
    @property
    def listener(self) -> FileSystemEventListener:
        """
        [Function intent]
        Gets the registered listener associated with this handle.
        
        [Design principles]
        - Provide access to the associated listener
        - Read-only property to prevent modification
        
        [Implementation details]
        - Returns the listener instance provided at initialization
        
        Returns:
            The associated FileSystemEventListener
            
        Raises:
            WatchNotActiveError: If the watch is not active
        """
        if not self._active:
            raise WatchNotActiveError("Cannot access listener for inactive watch")
        return self._listener
