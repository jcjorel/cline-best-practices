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
# Defines the base components for the file system monitoring system, including
# event types, event data structure, and the abstract base class for platform-specific
# file system monitors.
###############################################################################
# [Source file design principles]
# - Uses Enum for clear definition of change types.
# - Defines a structured ChangeEvent class for consistent event data.
# - Employs an Abstract Base Class (ABC) to enforce a common interface for all
#   monitor implementations.
# - Includes basic thread safety considerations (RLock).
# - Design Decision: Abstract Base Class for Monitors (2025-04-14)
#   * Rationale: Ensures all platform-specific monitors adhere to a consistent API, simplifying the factory and usage.
#   * Alternatives considered: Duck typing (less explicit contract).
###############################################################################
# [Source file constraints]
# - Requires Python 3's `abc` and `enum` modules.
# - Platform-specific implementations must inherit from FileSystemMonitor and
#   implement the abstract methods.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-05-01T11:42:00Z : Fixed MonitorBase initialization by CodeAssistant
# * Fixed variable reference errors in __init__ method
# * Replaced references to undefined 'config' and 'change_queue' variables
# * Used proper '_watch_manager' and '_event_dispatcher' variables
# * Fixed "name 'config' is not defined" error
# 2025-04-29T08:33:30Z : Centralized log file filtering logic by CodeAssistant
# * Removed local _is_log_file() method in favor of centralized implementation
# * Updated import to use shared path_utils.is_log_file function
# * Updated dispatch_event to use centralized is_log_file implementation
# 2025-04-15T09:40:40Z : Initial creation of base monitor components by CodeAssistant
# * Defined ChangeType, ChangeEvent, and FileSystemMonitor ABC.
###############################################################################

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Set, Callable, Optional, Dict, Any
from pathlib import Path
import logging
import threading
import time

from ..core.path_utils import is_log_file

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    """Enumeration of possible file system change types."""
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    RENAMED = auto() # Represents a move operation within the monitored scope
    UNKNOWN = auto() # Fallback for unrecognized events

class ChangeEvent:
    """
    Represents a single detected file system change event.
    Includes information about the path, type of change, and timestamp.
    For rename events, it also includes the original path.
    """

    def __init__(self, path: str, change_type: ChangeType, old_path: Optional[str] = None):
        """
        Initializes a ChangeEvent instance.

        Args:
            path: The path of the file or directory that changed. For RENAMED, this is the new path.
            change_type: The type of change detected (from ChangeType enum).
            old_path: The original path of the file or directory before a rename.
                      Only relevant for RENAMED change type.
        """
        if not isinstance(change_type, ChangeType):
            raise TypeError("change_type must be an instance of ChangeType Enum")

        self.path = str(Path(path).resolve()) # Normalize and store absolute path
        self.change_type = change_type
        self.old_path = str(Path(old_path).resolve()) if old_path else None # Normalize old path too
        self.timestamp = time.time() # Record event detection time

        if self.change_type == ChangeType.RENAMED and not self.old_path:
            logger.warning(f"ChangeEvent created with type RENAMED but no old_path provided for path: {self.path}")

    def __eq__(self, other):
        """Checks equality based on path, type, and old_path."""
        if not isinstance(other, ChangeEvent):
            return NotImplemented
        # Timestamps are ignored for equality comparison as they represent detection time
        return (self.path == other.path and
                self.change_type == other.change_type and
                self.old_path == other.old_path)

    def __hash__(self):
        """Generates a hash based on path, type, and old_path for use in sets/dicts."""
        # Timestamps are ignored for hashing
        return hash((self.path, self.change_type, self.old_path))

    def __repr__(self):
        """Provides a developer-friendly string representation."""
        if self.change_type == ChangeType.RENAMED and self.old_path:
            return f"ChangeEvent(type={self.change_type.name}, old='{self.old_path}', new='{self.path}')"
        else:
            return f"ChangeEvent(type={self.change_type.name}, path='{self.path}')"

class MonitorBase(ABC):
    """
    [Class intent]
    Abstract base class for platform-specific file system monitors.
    
    [Design principles]
    - Common interface for all platform monitors
    - Log file filtering to prevent infinite event loops
    - Thread safety for concurrent access
    
    [Implementation details]
    - Provides methods for starting, stopping, and managing watches
    - Includes log file detection to prevent monitoring log files
    - Implements thread-safe operations
    """

    def __init__(self, watch_manager: Any, event_dispatcher: Any):
        """
        [Function intent]
        Initialize the file system monitor.
        
        [Design principles]
        - Clean initialization
        - Resource management
        
        [Implementation details]
        - Sets up references to watch manager and event dispatcher
        - Initializes internal state
        
        Args:
            watch_manager: The watch manager instance
            event_dispatcher: The event dispatcher instance
        """
        self._watch_manager = watch_manager
        self._event_dispatcher = event_dispatcher
        self._watched_directories: Set[str] = set() # Store normalized absolute paths
        self._running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock() # Lock for managing watched_directories and running state
        logger.debug(f"{self.__class__.__name__} initialized.")

    @property
    def running(self) -> bool:
        """Returns True if the monitor is currently running."""
        with self._lock:
            return self._running

    @abstractmethod
    def start(self):
        """
        Starts the file system monitoring process.
        This typically involves setting up watchers and starting a background thread.
        """
        logger.info(f"Starting {self.__class__.__name__}...")
        with self._lock:
            if self._running:
                logger.warning(f"{self.__class__.__name__} is already running.")
                return
            self._running = True

    @abstractmethod
    def stop(self):
        """
        Stops the file system monitoring process gracefully.
        This should clean up resources and stop any background threads.
        """
        logger.info(f"Stopping {self.__class__.__name__}...")
        with self._lock:
            if not self._running:
                logger.warning(f"{self.__class__.__name__} is not running.")
                return
            self._running = False
        # Joining the thread should happen outside the lock if the thread needs the lock
        if self.monitor_thread and self.monitor_thread.is_alive():
             logger.debug(f"Waiting for {self.__class__.__name__} thread to join...")
             self.monitor_thread.join(timeout=5.0) # Add a timeout
             if self.monitor_thread.is_alive():
                  logger.warning(f"{self.__class__.__name__} thread did not exit cleanly.")
        logger.info(f"{self.__class__.__name__} stopped.")


    def add_directory(self, directory: str):
        """
        Adds a directory to the set of monitored paths.
        The path will be normalized and resolved to an absolute path.

        Args:
            directory: The path to the directory to monitor.
        """
        try:
            abs_path = str(Path(directory).resolve())
            if not Path(abs_path).is_dir():
                 logger.warning(f"Cannot add watch for non-existent or non-directory path: {abs_path}")
                 return
        except Exception as e:
             logger.error(f"Error resolving path '{directory}': {e}")
             return

        with self._lock:
            if abs_path not in self._watched_directories:
                self._watched_directories.add(abs_path)
                logger.info(f"Directory added to watch list: {abs_path}")
                # Concrete implementations should handle adding the actual OS watch here
                # if the monitor is already running.
            else:
                 logger.debug(f"Directory already being watched: {abs_path}")


    def remove_directory(self, directory: str):
        """
        Removes a directory from the set of monitored paths.

        Args:
            directory: The path to the directory to stop monitoring.
        """
        try:
            abs_path = str(Path(directory).resolve())
        except Exception as e:
             logger.error(f"Error resolving path '{directory}' for removal: {e}")
             return

        with self._lock:
            if abs_path in self._watched_directories:
                self._watched_directories.remove(abs_path)
                logger.info(f"Directory removed from watch list: {abs_path}")
                # Concrete implementations should handle removing the actual OS watch here
                # if the monitor is running.
            else:
                 logger.debug(f"Directory not found in watch list for removal: {abs_path}")

    def get_watched_directories(self) -> List[str]:
        """Returns a copy of the set of currently watched directories."""
        with self._lock:
            return list(self._watched_directories)
            
        
    def dispatch_event(self, event_type: Any, path: str, old_path: Optional[str] = None, extra_data: Optional[Any] = None) -> None:
        """
        [Function intent]
        Dispatch a file system event.
        
        [Design principles]
        - Central event dispatch
        - Log file filtering
        
        [Implementation details]
        - Filters out events for log files
        - Delegates to event dispatcher for actual dispatch
        - Handles additional event data
        
        Args:
            event_type: Type of the event
            path: Path of the changed file
            old_path: Original path for rename events
            extra_data: Any additional event data
        """
        # Skip events for log files to prevent infinite event loops
        if is_log_file(path) or (old_path and is_log_file(old_path)):
            # Intentionally not logging anything here to prevent log file changes
            return
            
        # Dispatch the event to the event dispatcher
        self._event_dispatcher.dispatch_event(event_type, path, old_path, extra_data)
