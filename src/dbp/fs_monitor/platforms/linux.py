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
# This file implements the Linux-specific file system monitor using the inotify API.
# It detects file system events at the OS level, converts inotify-specific events
# to our uniform event model, and forwards them to the event dispatcher.
###############################################################################
# [Source file design principles]
# - Direct use of Linux inotify API through ctypes
# - Efficient event translation and handling
# - Proper resource management for inotify file descriptors
# - Thread-safe operations
# - Non-blocking event processing to prevent resource hogging
###############################################################################
# [Source file constraints]
# - Must only be used on Linux systems with inotify support
# - Must handle inotify file descriptor and watch descriptor resources properly
# - Must translate platform-specific events to our uniform model
# - Must provide proper error handling for system call failures
# - Must not block the main thread during event processing
###############################################################################
# [Dependencies]
# system:os
# system:threading
# system:logging
# system:select
# system:time
# system:typing
# system:ctypes
# system:ctypes.util
# codebase:src/dbp/fs_monitor/monitor_base.py
# codebase:src/dbp/fs_monitor/event_types.py
# codebase:src/dbp/fs_monitor/exceptions.py
# codebase:src/dbp/fs_monitor/watch_manager.py
# codebase:src/dbp/fs_monitor/event_dispatcher.py
###############################################################################
# [GenAI tool change history]
# 2025-04-30T05:58:00Z : Updated EventDispatcher import path by CodeAssistant
# * Changed import from ..event_dispatcher to ..dispatch.event_dispatcher
# * Fixed "No module named 'dbp.fs_monitor.event_dispatcher'" error
# 2025-04-29T09:03:00Z : Fixed import path for WatchManager and EventDispatcher by CodeAssistant
# * Changed import from .watch_manager to ..watch_manager
# * Changed import from .event_dispatcher to ..event_dispatcher
# * Fixed another import error that caused server startup failure
# 2025-04-29T09:01:00Z : Fixed import path for exceptions by CodeAssistant
# * Changed import from .exceptions to ..core for WatchCreationError
# * Added import for FileSystemMonitorError
# * Fixed another import error that caused server startup failure
# 2025-04-29T08:58:00Z : Fixed import path for event types by CodeAssistant
# * Changed import from .event_types to ..core for EventType and FileSystemEvent
# * Fixed import error that caused server startup failure
# 2025-04-29T00:20:00Z : Initial implementation of Linux monitor for fs_monitor redesign by CodeAssistant
# * Created LinuxMonitor class using inotify API
# * Implemented event translation from inotify to uniform model
# * Added resource management for inotify file descriptors
###############################################################################

import os
import threading
import logging
import select
import time
from typing import Dict, Set, List, Optional, Callable, Any
import ctypes
import ctypes.util

from .monitor_base import MonitorBase
from ..core import EventType, FileSystemEvent
from ..core import FileSystemMonitorError, WatchCreationError
from ..watch_manager import WatchManager
from ..dispatch.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

# Define inotify constants
# These are from linux/inotify.h
IN_ACCESS = 0x00000001  # File was accessed
IN_MODIFY = 0x00000002  # File was modified
IN_ATTRIB = 0x00000004  # Metadata changed
IN_CLOSE_WRITE = 0x00000008  # Writable file was closed
IN_CLOSE_NOWRITE = 0x00000010  # Unwritable file was closed
IN_OPEN = 0x00000020  # File was opened
IN_MOVED_FROM = 0x00000040  # File was moved from X
IN_MOVED_TO = 0x00000080  # File was moved to Y
IN_CREATE = 0x00000100  # Subfile was created
IN_DELETE = 0x00000200  # Subfile was deleted
IN_DELETE_SELF = 0x00000400  # Self was deleted
IN_MOVE_SELF = 0x00000800  # Self was moved
IN_UNMOUNT = 0x00002000  # Backing fs was unmounted
IN_Q_OVERFLOW = 0x00004000  # Event queue overflowed
IN_IGNORED = 0x00008000  # File was ignored
IN_ISDIR = 0x40000000  # Event occurred against dir


class InotifyEvent(ctypes.Structure):
    """
    [Class intent]
    Represents the inotify_event structure from inotify.h.
    
    [Design principles]
    - Direct mapping to C structure
    - Efficient binary parsing
    
    [Implementation details]
    - Uses ctypes to define the structure
    - Matches the memory layout of the C structure
    """
    _fields_ = [
        ('wd', ctypes.c_int),
        ('mask', ctypes.c_uint32),
        ('cookie', ctypes.c_uint32),
        ('len', ctypes.c_uint32),
    ]


class LinuxMonitor(MonitorBase):
    """
    [Class intent]
    Linux-specific file system monitor using inotify.
    
    [Design principles]
    - Direct use of Linux inotify API
    - Efficient event translation
    - Resource management
    - No generation of logs for log file events to prevent infinite loops
    
    [Implementation details]
    - Uses inotify for file system monitoring
    - Translates inotify events to our event model
    - Manages inotify watch descriptors
    - Silently skips log file events without generating logs
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the Linux monitor.
        
        [Design principles]
        - Clean initialization
        - Resource initialization
        
        [Implementation details]
        - Calls parent constructor
        - Initializes inotify file descriptor
        - Sets up data structures for watch mapping
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        super().__init__(watch_manager, event_dispatcher)
        self._inotify_fd = None
        self._watch_to_path = {}
        self._path_to_watch = {}
        self._monitor_thread = None
    
    def start(self) -> None:
        """
        [Function intent]
        Start the Linux monitor.
        
        [Design principles]
        - Clean startup sequence
        - Error handling
        
        [Implementation details]
        - Initializes inotify
        - Starts the monitoring thread
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("Linux monitor already running")
                return
            
            try:
                # Initialize inotify
                self._inotify_fd = self._init_inotify()
                if self._inotify_fd < 0:
                    raise WatchCreationError("Failed to initialize inotify")
                
                # Start the monitoring thread
                self._running = True
                self._monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    daemon=True,
                    name="FSMonitor-Linux"
                )
                self._monitor_thread.start()
                
                logger.debug("Started Linux monitor")
            except Exception as e:
                self._running = False
                logger.error(f"Error starting Linux monitor: {e}")
                raise
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the Linux monitor.
        
        [Design principles]
        - Clean shutdown sequence
        - Resource cleanup
        
        [Implementation details]
        - Sets running flag to false
        - Closes inotify file descriptor
        - Waits for monitoring thread to terminate
        """
        with self._lock:
            if not self._running:
                logger.debug("Linux monitor already stopped")
                return
            
            # Set running flag to false
            self._running = False
            
            # Close inotify file descriptor
            if self._inotify_fd is not None:
                try:
                    os.close(self._inotify_fd)
                except Exception as e:
                    logger.warning(f"Error closing inotify file descriptor: {e}")
                self._inotify_fd = None
            
            # Wait for monitoring thread to terminate
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            
            # Clear mappings
            self._watch_to_path.clear()
            self._path_to_watch.clear()
            
            logger.debug("Stopped Linux monitor")
    
    def add_watch(self, path: str) -> int:
        """
        [Function intent]
        Add an inotify watch for a path.
        
        [Design principles]
        - Platform-specific watch creation
        - Resource tracking
        
        [Implementation details]
        - Calls inotify_add_watch
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path to watch
            
        Returns:
            Inotify watch descriptor
            
        Raises:
            WatchCreationError: If the watch cannot be added
        """
        with self._lock:
            if not self._running:
                logger.warning("Linux monitor not running, watch will not be added")
                raise WatchCreationError("Monitor not running")
            
            if path in self._path_to_watch:
                return self._path_to_watch[path]
            
            try:
                # Define the events we want to watch for
                mask = (IN_CREATE | IN_DELETE | IN_MODIFY | IN_MOVED_FROM | IN_MOVED_TO |
                        IN_DELETE_SELF | IN_MOVE_SELF)
                
                # Add the watch
                wd = self._add_inotify_watch(self._inotify_fd, path.encode('utf-8'), mask)
                if wd < 0:
                    raise WatchCreationError(f"Failed to add watch for {path}")
                
                # Update mappings
                self._watch_to_path[wd] = path
                self._path_to_watch[path] = wd
                
                logger.debug(f"Added watch for {path} with descriptor {wd}")
                return wd
            except Exception as e:
                logger.error(f"Error adding watch for {path}: {e}")
                raise WatchCreationError(f"Failed to add watch for {path}: {e}")
    
    def remove_watch(self, path: str, descriptor: int) -> None:
        """
        [Function intent]
        Remove an inotify watch.
        
        [Design principles]
        - Platform-specific watch removal
        - Resource cleanup
        
        [Implementation details]
        - Calls inotify_rm_watch
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path that was being watched
            descriptor: Inotify watch descriptor
        """
        with self._lock:
            if not self._running:
                logger.debug("Linux monitor not running, watch will not be removed")
                return
            
            try:
                # Remove the watch
                self._remove_inotify_watch(self._inotify_fd, descriptor)
                
                # Update mappings
                self._watch_to_path.pop(descriptor, None)
                self._path_to_watch.pop(path, None)
                
                logger.debug(f"Removed watch for {path} with descriptor {descriptor}")
            except Exception as e:
                logger.warning(f"Error removing watch for {path}: {e}")
    
    def _init_inotify(self) -> int:
        """
        [Function intent]
        Initialize the inotify instance.
        
        [Design principles]
        - Direct interface to inotify API
        
        [Implementation details]
        - Uses ctypes to call libc.inotify_init
        
        Returns:
            Inotify file descriptor
        """
        try:
            libc_path = ctypes.util.find_library('c')
            libc = ctypes.CDLL(libc_path)
            
            # Get the inotify_init function
            inotify_init = libc.inotify_init
            inotify_init.argtypes = []
            inotify_init.restype = ctypes.c_int
            
            # Call inotify_init
            return inotify_init()
        except Exception as e:
            logger.error(f"Error initializing inotify: {e}")
            return -1
    
    def _add_inotify_watch(self, fd: int, path: bytes, mask: int) -> int:
        """
        [Function intent]
        Add an inotify watch for a path.
        
        [Design principles]
        - Direct interface to inotify API
        
        [Implementation details]
        - Uses ctypes to call libc.inotify_add_watch
        
        Args:
            fd: Inotify file descriptor
            path: Path to watch (as bytes)
            mask: Events to watch for
            
        Returns:
            Inotify watch descriptor
        """
        try:
            libc_path = ctypes.util.find_library('c')
            libc = ctypes.CDLL(libc_path)
            
            # Get the inotify_add_watch function
            inotify_add_watch = libc.inotify_add_watch
            inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            inotify_add_watch.restype = ctypes.c_int
            
            # Call inotify_add_watch
            return inotify_add_watch(fd, path, mask)
        except Exception as e:
            logger.error(f"Error adding inotify watch: {e}")
            return -1
    
    def _remove_inotify_watch(self, fd: int, wd: int) -> int:
        """
        [Function intent]
        Remove an inotify watch.
        
        [Design principles]
        - Direct interface to inotify API
        
        [Implementation details]
        - Uses ctypes to call libc.inotify_rm_watch
        
        Args:
            fd: Inotify file descriptor
            wd: Inotify watch descriptor
            
        Returns:
            0 on success, -1 on error
        """
        try:
            libc_path = ctypes.util.find_library('c')
            libc = ctypes.CDLL(libc_path)
            
            # Get the inotify_rm_watch function
            inotify_rm_watch = libc.inotify_rm_watch
            inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
            inotify_rm_watch.restype = ctypes.c_int
            
            # Call inotify_rm_watch
            return inotify_rm_watch(fd, wd)
        except Exception as e:
            logger.error(f"Error removing inotify watch: {e}")
            return -1
    
    def _read_events(self) -> List[tuple]:
        """
        [Function intent]
        Read available inotify events.
        
        [Design principles]
        - Efficient event reading
        - Binary data parsing
        
        [Implementation details]
        - Uses select to wait for events
        - Parses binary event data
        - Returns list of (watch_descriptor, event_mask, filename) tuples
        
        Returns:
            List of event tuples
        """
        # Use select to wait for events (with a timeout)
        try:
            r, _, _ = select.select([self._inotify_fd], [], [], 1)
            if not r:
                return []
            
            # Read from the inotify file descriptor
            # Read the available events
            # The buffer should be large enough to hold multiple events
            # 4096 is a reasonable size
            buffer = os.read(self._inotify_fd, 4096)
            
            events = []
            offset = 0
            
            # Process all events in the buffer
            while offset < len(buffer):
                # Parse the event header
                event = InotifyEvent.from_buffer_copy(buffer[offset:offset + 16])
                
                # Get the name if present
                name = None
                if event.len > 0:
                    # The name is a null-terminated string
                    name_offset = offset + 16
                    name = buffer[name_offset:name_offset + event.len].split(b'\0', 1)[0].decode('utf-8')
                
                # Add the event to the list
                events.append((event.wd, event.mask, name))
                
                # Move to the next event
                offset += 16 + event.len
            
            return events
        except Exception as e:
            if self._running:
                logger.error(f"Error reading inotify events: {e}")
            return []
    
    def _monitor_loop(self) -> None:
        """
        [Function intent]
        Main loop for the monitoring thread.
        
        [Design principles]
        - Continuous event processing
        - Event translation
        
        [Implementation details]
        - Continuously reads inotify events
        - Translates them to our event model
        - Dispatches events to the event dispatcher
        """
        while self._running:
            try:
                # Read events
                events = self._read_events()
                
                # Process events
                for wd, mask, name in events:
                    # Get the path for this watch descriptor
                    path = self._watch_to_path.get(wd)
                    if not path:
                        continue
                    
                    # If this event is for a file in a directory, construct the full path
                    if name:
                        full_path = os.path.join(path, name)
                    else:
                        full_path = path
                    
                    # Check if this is a directory event
                    is_dir = bool(mask & IN_ISDIR)
                    
                    # Translate inotify event to our event model
                    if mask & IN_CREATE:
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_CREATED, full_path)
                        else:
                            # Check if it's a symlink
                            try:
                                if os.path.islink(full_path):
                                    target = os.readlink(full_path)
                                    self.dispatch_event(EventType.SYMLINK_CREATED, full_path, None, target)
                                else:
                                    self.dispatch_event(EventType.FILE_CREATED, full_path)
                            except (FileNotFoundError, PermissionError):
                                # The file might have been deleted before we checked it
                                self.dispatch_event(EventType.FILE_CREATED, full_path)
                    
                    if mask & IN_DELETE:
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_DELETED, full_path)
                        else:
                            # We don't know if it was a symlink because it's already gone
                            # For now, assume it was a file
                            self.dispatch_event(EventType.FILE_DELETED, full_path)
                    
                    if mask & IN_MODIFY and not is_dir:
                        self.dispatch_event(EventType.FILE_MODIFIED, full_path)
                    
                    if mask & IN_MOVED_FROM:
                        # This is part of a move operation
                        # We need to keep track of this event and wait for the corresponding IN_MOVED_TO
                        # For now, we'll just report it as a deletion
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_DELETED, full_path)
                        else:
                            self.dispatch_event(EventType.FILE_DELETED, full_path)
                    
                    if mask & IN_MOVED_TO:
                        # This is part of a move operation
                        # For now, we'll just report it as a creation
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_CREATED, full_path)
                        else:
                            # Check if it's a symlink
                            try:
                                if os.path.islink(full_path):
                                    target = os.readlink(full_path)
                                    self.dispatch_event(EventType.SYMLINK_CREATED, full_path, None, target)
                                else:
                                    self.dispatch_event(EventType.FILE_CREATED, full_path)
                            except (FileNotFoundError, PermissionError):
                                # The file might have been deleted before we checked it
                                self.dispatch_event(EventType.FILE_CREATED, full_path)
                    
                    if mask & IN_DELETE_SELF:
                        # The watched directory itself was deleted
                        if path == full_path:  # This is the watch itself
                            self.dispatch_event(EventType.DIRECTORY_DELETED, full_path)
                    
                    if mask & IN_MOVE_SELF:
                        # The watched directory itself was moved
                        # For now, we'll just report it as a deletion
                        if path == full_path:  # This is the watch itself
                            self.dispatch_event(EventType.DIRECTORY_DELETED, full_path)
                    
                    if mask & IN_IGNORED:
                        # The watch was removed, either explicitly or automatically
                        # Remove it from our mappings
                        with self._lock:
                            self._watch_to_path.pop(wd, None)
                            self._path_to_watch.pop(path, None)
                
                # Sleep a bit to avoid high CPU usage when no events
                if not events:
                    time.sleep(0.01)
            
            except Exception as e:
                if self._running:
                    logger.error(f"Error in Linux monitor loop: {e}")
                    time.sleep(1)  # Sleep to avoid tight loop on error
