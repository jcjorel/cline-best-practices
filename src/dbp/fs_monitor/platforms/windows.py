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
# Implements the Windows-specific file system monitor using the Win32 API
# function ReadDirectoryChangesW via the 'pywin32' Python library. This provides
# an efficient, native mechanism for detecting file changes on Windows systems.
###############################################################################
# [Source file design principles]
# - Inherits from the FileSystemMonitor base class.
# - Uses the 'pywin32' library to interact with the Windows API.
# - Employs overlapped I/O for asynchronous monitoring of each directory.
# - Runs monitoring logic for each watched directory in separate background threads.
# - Maps Windows file action flags to the standardized ChangeEvent structure.
# - Handles adding and removing watches dynamically by managing directory handles.
# - Supports recursive monitoring via the ReadDirectoryChangesW flag.
# - Includes error handling for Win32 API calls.
# - Design Decision: Use 'pywin32' and ReadDirectoryChangesW (2025-04-14)
#   * Rationale: Provides direct access to the native Windows file change notification system, offering efficiency over polling.
#   * Alternatives considered: Polling (inefficient), .NET FileSystemWatcher via pythonnet (more complex dependencies).
###############################################################################
# [Source file constraints]
# - Requires the 'pywin32' Python library (`pip install pywin32`).
# - Only functional on Windows operating systems.
# - Requires appropriate permissions to monitor directories.
# - Managing multiple threads for watches can add complexity.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# other:- src/dbp/fs_monitor/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:42:55Z : Initial creation of WindowsFileSystemMonitor by CodeAssistant
# * Implemented start, stop, add/remove directory, and event handling loop using pywin32.
###############################################################################

import os
import threading
import logging
import time
from typing import Dict, Set, Optional, Any
from pathlib import Path
import ctypes
from ctypes import wintypes

# Try to import necessary pywin32 modules
try:
    import win32file
    import win32con
    import pywintypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.getLogger(__name__).warning("The 'pywin32' library is required for WindowsFileSystemMonitor but was not found. Install it using 'pip install pywin32'.")
except Exception as e:
    # Catch other potential import errors
    HAS_WIN32 = False
    logging.getLogger(__name__).error(f"Failed to import 'pywin32' library: {e}", exc_info=True)


# Import from monitor_base instead of base
try:
    from .monitor_base import MonitorBase as FileSystemMonitor
    from ..core.event_types import ChangeEvent, ChangeType
except ImportError:
    from monitor_base import MonitorBase as FileSystemMonitor
    from ..core.event_types import ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

# Define constants if pywin32 is not available, to allow class definition
if not HAS_WIN32:
    class win32con:
        FILE_LIST_DIRECTORY = 1
        FILE_SHARE_READ = 1
        FILE_SHARE_WRITE = 2
        FILE_SHARE_DELETE = 4
        OPEN_EXISTING = 3
        FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
        FILE_FLAG_OVERLAPPED = 0x40000000
        FILE_NOTIFY_CHANGE_FILE_NAME = 1
        FILE_NOTIFY_CHANGE_DIR_NAME = 2
        FILE_NOTIFY_CHANGE_ATTRIBUTES = 4
        FILE_NOTIFY_CHANGE_SIZE = 8
        FILE_NOTIFY_CHANGE_LAST_WRITE = 16
        FILE_NOTIFY_CHANGE_CREATION = 64
        FILE_ACTION_ADDED = 1
        FILE_ACTION_REMOVED = 2
        FILE_ACTION_MODIFIED = 3
        FILE_ACTION_RENAMED_OLD_NAME = 4
        FILE_ACTION_RENAMED_NEW_NAME = 5
        ERROR_OPERATION_ABORTED = 995

    class pywintypes:
        OVERLAPPED = None # Placeholder
        error = Exception # Placeholder

    class win32file:
        # Placeholder methods/classes
        @staticmethod
        def CreateFile(*args, **kwargs): raise NotImplementedError
        @staticmethod
        def CreateEvent(*args, **kwargs): raise NotImplementedError
        @staticmethod
        def AllocateReadBuffer(*args, **kwargs): raise NotImplementedError
        @staticmethod
        def ReadDirectoryChangesW(*args, **kwargs): raise NotImplementedError
        @staticmethod
        def GetOverlappedResult(*args, **kwargs): raise NotImplementedError
        @staticmethod
        def FILE_NOTIFY_INFORMATION(*args, **kwargs): return [] # Return empty list
        @staticmethod
        def CancelIo(*args, **kwargs): pass
        @staticmethod
        def CloseHandle(*args, **kwargs): pass


class WindowsFileSystemMonitor(FileSystemMonitor):
    """
    [Class intent]
    Windows-specific file system monitor implementation using the Win32 API
    function ReadDirectoryChangesW via the 'pywin32' library.
    
    [Design principles]
    - Uses pywin32 for efficient native file system monitoring
    - Inherits filter logic from MonitorBase to prevent log file events
    - No generation of logs for log file events to prevent infinite loops
    
    [Implementation details]
    - Uses ReadDirectoryChangesW for efficient async file system monitoring
    - Manages multiple background threads for watch operations
    - Silently skips log file events without generating logs
    """

    # Flags for ReadDirectoryChangesW
    _WATCH_FLAGS = (
        win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
        win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
        # win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES | # Often noisy
        win32con.FILE_NOTIFY_CHANGE_SIZE |
        win32con.FILE_NOTIFY_CHANGE_LAST_WRITE #|
        # win32con.FILE_NOTIFY_CHANGE_CREATION # Included in ADDED action
    )

    def __init__(self, config, change_queue):
        """
        Initializes the WindowsFileSystemMonitor.

        Raises:
            ImportError: If the 'pywin32' library is not installed or fails to import.
        """
        super().__init__(config, change_queue)

        if not HAS_WIN32:
            raise ImportError("The 'pywin32' library is required to use WindowsFileSystemMonitor.")

        self._watches: Dict[str, Any] = {}  # Maps normalized paths to directory handles
        self._buffers: Dict[str, Any] = {}  # Maps paths to read buffers
        self._overlapped: Dict[str, Any] = {} # Maps paths to OVERLAPPED structures
        self._threads: Dict[str, threading.Thread] = {} # Maps paths to monitoring threads
        self._thread_stop_events: Dict[str, threading.Event] = {} # Events to signal thread stop
        self._rename_old_path: Optional[str] = None # Track old path for renames

    def start(self):
        """Starts monitoring threads for all initially configured directories."""
        with self._lock:
            if self.running:
                logger.warning("WindowsFileSystemMonitor is already running.")
                return
            super().start() # Sets self._running = True

            initial_dirs = self.get_watched_directories() # Get a copy
            logger.info(f"Starting Windows monitor for {len(initial_dirs)} initial directories.")
            for directory in initial_dirs:
                # _add_watch starts the thread for each directory
                self._add_watch(directory)

            logger.info("Windows file system monitor started.")

    def stop(self):
        """Stops all monitoring threads and closes directory handles."""
        with self._lock:
            if not self.running:
                logger.warning("WindowsFileSystemMonitor is not running.")
                return
            logger.info("Stopping Windows file system monitor...")
            # Signal all threads to stop *before* calling super().stop() which joins them
            for path, stop_event in self._thread_stop_events.items():
                 logger.debug(f"Signaling stop for monitor thread: {path}")
                 stop_event.set()
                 # Attempt to cancel pending I/O - might help thread exit faster
                 if path in self._watches and self._watches[path]:
                     try:
                         win32file.CancelIo(self._watches[path])
                     except pywintypes.error as e:
                         # Ignore errors like "handle is invalid" if already closed
                         if e.winerror != 6: # ERROR_INVALID_HANDLE
                             logger.warning(f"Error cancelling I/O for {path}: {e}")
                     except Exception as e:
                          logger.warning(f"Unexpected error cancelling I/O for {path}: {e}")


        # Call super().stop() to set running flag and join threads
        super().stop()

        # Clean up remaining resources (handles should ideally be closed by threads)
        with self._lock:
            paths_to_clean = list(self._watches.keys())
            for path in paths_to_clean:
                self._close_handle_safe(path) # Ensure handles are closed

            self._watches.clear()
            self._buffers.clear()
            self._overlapped.clear()
            self._threads.clear()
            self._thread_stop_events.clear()

        logger.info("Windows file system monitor stopped.")

    def _close_handle_safe(self, path: str):
        """Safely closes the Win32 handle associated with a path."""
        handle = self._watches.pop(path, None)
        overlapped = self._overlapped.pop(path, None) # Also remove associated overlapped
        self._buffers.pop(path, None) # Remove buffer too

        if handle:
            try:
                win32file.CloseHandle(handle)
                logger.debug(f"Closed handle for path: {path}")
            except pywintypes.error as e:
                logger.warning(f"Error closing handle for {path}: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error closing handle for {path}: {e}", exc_info=True)
        if overlapped and overlapped.hEvent:
             try:
                  win32file.CloseHandle(overlapped.hEvent)
             except Exception as e:
                  logger.warning(f"Error closing event handle for {path}: {e}")


    def add_directory(self, directory: str):
        """Adds a directory watch and starts its monitoring thread."""
        # Base class handles adding to self._watched_directories and path normalization
        super().add_directory(directory)
        abs_path = str(Path(directory).resolve())

        # If monitor is running, add the actual watch and start thread
        if self.running:
            with self._lock:
                 if abs_path in self._watched_directories: # Check if successfully added by super()
                     self._add_watch(abs_path)

    def remove_directory(self, directory: str):
        """Stops the monitoring thread and removes the watch for a directory."""
        # Base class handles removing from self._watched_directories and path normalization
        super().remove_directory(directory)
        abs_path = str(Path(directory).resolve())

        # If monitor is running, stop the thread and remove the watch
        if self.running:
            with self._lock:
                self._remove_watch(abs_path)


    def _add_watch(self, path: str):
        """Creates Win32 handles and starts the monitoring thread for a path."""
        if not self.running: return
        if not Path(path).is_dir():
            logger.warning(f"Attempted to watch non-directory with Win32 monitor: {path}")
            return
        if path in self._watches:
            # logger.debug(f"Watch already exists for: {path}")
            return

        logger.debug(f"Adding Win32 watch for: {path}")
        try:
            # Create directory handle
            handle = win32file.CreateFile(
                path,
                win32con.FILE_LIST_DIRECTORY, # Required permission
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None, # Security attributes
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED, # Required flags
                None # Template file handle
            )

            # Create OVERLAPPED structure and event handle
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32file.CreateEvent(None, True, False, None) # Manual reset event

            # Allocate buffer for change notifications
            # Buffer size might need tuning based on expected event volume
            buffer = win32file.AllocateReadBuffer(8192)

            # Store watch resources
            self._watches[path] = handle
            self._overlapped[path] = overlapped
            self._buffers[path] = buffer
            stop_event = threading.Event()
            self._thread_stop_events[path] = stop_event

            # Start the dedicated monitoring thread for this directory
            thread = threading.Thread(
                target=self._monitor_directory_loop,
                args=(path, handle, buffer, overlapped, stop_event),
                daemon=True,
                name=f"WinFSMonitor-{Path(path).name}"
            )
            self._threads[path] = thread
            thread.start()
            logger.info(f"Started monitoring thread for: {path}")

            # Recursively add subdirectories if needed (AFTER starting parent watch)
            # This avoids race conditions where subdirs might be created before parent watch starts
            if self.config.get('monitor.recursive', True):
                 self._add_subdirectories_recursive(path)

        except pywintypes.error as e:
            logger.error(f"Win32 error adding watch for {path}: ({e.winerror}) {e.strerror}", exc_info=True)
            self._close_handle_safe(path) # Clean up if handle creation failed partially
        except Exception as e:
            logger.error(f"Failed to add Win32 watch for {path}: {e}", exc_info=True)
            self._close_handle_safe(path)

    def _add_subdirectories_recursive(self, parent_path: str):
        """Recursively adds watches for subdirectories."""
        try:
            for item in os.scandir(parent_path):
                if item.is_dir(follow_symlinks=False):
                    # Add watch for subdirectory (will handle recursion internally)
                    self._add_watch(item.path)
        except OSError as e:
            logger.warning(f"Could not scan directory {parent_path} for recursive watch: {e}")


    def _remove_watch(self, path: str):
        """Signals the monitoring thread to stop and cleans up resources."""
        if path not in self._watches:
            # logger.debug(f"No watch exists to remove for: {path}")
            return

        logger.debug(f"Removing Win32 watch for: {path}")

        # Signal the thread to stop
        stop_event = self._thread_stop_events.pop(path, None)
        if stop_event:
            stop_event.set()

        # Cancel pending I/O (might help thread exit faster)
        handle = self._watches.get(path)
        if handle:
             try:
                 win32file.CancelIo(handle)
             except pywintypes.error as e:
                 if e.winerror != 6: # ERROR_INVALID_HANDLE
                     logger.warning(f"Error cancelling I/O for {path} during removal: {e}")
             except Exception as e:
                  logger.warning(f"Unexpected error cancelling I/O for {path} during removal: {e}")


        # Thread joining is handled in the main stop() method
        # Clean up handles immediately if possible (thread might still hold them)
        self._close_handle_safe(path)

        # Recursively remove watches for subdirectories that might have been added
        # This is complex because subdirs might be watched independently.
        # A simpler approach is to let the main stop() handle cleanup or rely
        # on the fact that deleting the parent often triggers events for children.
        # For now, we only remove the specific watch requested.

        logger.info(f"Signaled stop for monitoring thread: {path}")


    def _monitor_directory_loop(self, path: str, handle: Any, buffer: Any, overlapped: Any, stop_event: threading.Event):
        """
        The monitoring loop run in a separate thread for each watched directory.
        Uses overlapped I/O with ReadDirectoryChangesW.
        """
        recursive = self.config.get('monitor.recursive', True)
        logger.debug(f"Monitoring loop started for: {path}")

        while not stop_event.is_set():
            try:
                # Initiate asynchronous read for directory changes
                win32file.ReadDirectoryChangesW(
                    handle,
                    buffer,
                    recursive,  # Watch subdirectories if True
                    self._WATCH_FLAGS,
                    overlapped, # Overlapped structure for async I/O
                    None # Completion routine (not used here)
                )

                # Wait for changes or stop signal
                # Wait indefinitely (-1) for the overlapped event or the stop event
                rc = win32file.WaitForMultipleObjects(
                    [overlapped.hEvent, stop_event.native_handle], # Wait on directory change OR stop signal
                    False, # Wait for either event, not both
                    win32file.INFINITE # Wait forever
                )

                if stop_event.is_set() or rc == win32con.WAIT_OBJECT_0 + 1:
                    # Stop event was signaled
                    logger.debug(f"Stop signal received for monitor thread: {path}")
                    break

                if rc == win32con.WAIT_OBJECT_0:
                    # Directory change event occurred
                    # Get the result of the overlapped operation
                    try:
                        bytes_returned = win32file.GetOverlappedResult(handle, overlapped, True)
                    except pywintypes.error as e:
                         if e.winerror == win32con.ERROR_OPERATION_ABORTED:
                              logger.debug(f"ReadDirectoryChangesW aborted for {path}, likely due to stop signal.")
                              break # Exit loop if operation was aborted
                         else:
                              logger.error(f"GetOverlappedResult error for {path}: ({e.winerror}) {e.strerror}")
                              time.sleep(1) # Avoid tight loop on error
                              continue # Try reading again

                    if bytes_returned > 0:
                        # Process the changes returned in the buffer
                        results = win32file.FILE_NOTIFY_INFORMATION(buffer, bytes_returned)
                        logger.debug(f"Received {len(results)} change events for {path}")
                        for action, file_name in results:
                            if stop_event.is_set(): break # Check stop signal frequently

                            full_path = str(Path(path) / file_name) # Construct full path
                            change_type = ChangeType.UNKNOWN
                            event_old_path = None

                            # Map Win32 action code to ChangeType enum
                            if action == win32con.FILE_ACTION_ADDED:
                                change_type = ChangeType.CREATED
                                # If a new directory is added and recursive, start watching it
                                if recursive and Path(full_path).is_dir():
                                     # Need to call add_watch from the main thread context or use a queue
                                     # For simplicity here, we might miss watching dirs created during runtime
                                     # A better approach involves a central manager queueing add/remove watch tasks.
                                     logger.debug(f"New directory detected, recursive watch add needed: {full_path}")
                                     # self._add_watch(full_path) # Careful with threading here

                            elif action == win32con.FILE_ACTION_REMOVED:
                                change_type = ChangeType.DELETED
                                # If a directory is removed, stop watching it
                                if full_path in self._watches:
                                     logger.debug(f"Watched directory deleted, removing watch: {full_path}")
                                     # self._remove_watch(full_path) # Careful with threading

                            elif action == win32con.FILE_ACTION_MODIFIED:
                                change_type = ChangeType.MODIFIED

                            elif action == win32con.FILE_ACTION_RENAMED_OLD_NAME:
                                # Store the old path, wait for the NEW_NAME action
                                self._rename_old_path = full_path
                                logger.debug(f"Rename detected (old name): {full_path}")
                                continue # Skip queueing event until new name arrives

                            elif action == win32con.FILE_ACTION_RENAMED_NEW_NAME:
                                if self._rename_old_path:
                                    change_type = ChangeType.RENAMED
                                    event_old_path = self._rename_old_path
                                    logger.debug(f"Rename detected (new name): {full_path} (from {event_old_path})")
                                    self._rename_old_path = None # Reset state
                                    # Handle recursive watch for renamed directory
                                    if recursive and Path(full_path).is_dir():
                                         logger.debug(f"Renamed directory detected, recursive watch add needed: {full_path}")
                                         # self._add_watch(full_path)
                                else:
                                    # Got NEW_NAME without OLD_NAME, treat as CREATED
                                    logger.warning(f"Rename new name '{full_path}' received without old name, treating as CREATED.")
                                    change_type = ChangeType.CREATED

                            # Queue the event if type is known
                            if change_type != ChangeType.UNKNOWN:
                                change_event = ChangeEvent(full_path, change_type, old_path=event_old_path)
                                logger.debug(f"Queueing event from Win32 monitor: {change_event}")
                                self.change_queue.add_event(change_event)

                        # Reset rename state if NEW_NAME didn't follow OLD_NAME immediately
                        if action != win32con.FILE_ACTION_RENAMED_OLD_NAME:
                             self._rename_old_path = None

                    else:
                         logger.debug(f"ReadDirectoryChangesW returned 0 bytes for {path}.")

                elif rc == win32con.WAIT_TIMEOUT:
                     # This shouldn't happen with INFINITE timeout, but handle defensively
                     logger.debug(f"WaitForMultipleObjects timed out for {path} (unexpected).")
                     continue
                else:
                     # Some other error occurred
                     logger.error(f"WaitForMultipleObjects failed for {path} with code: {rc}")
                     # Consider breaking or sleeping before retrying
                     time.sleep(1)


            except pywintypes.error as e:
                if e.winerror == win32con.ERROR_OPERATION_ABORTED:
                    logger.info(f"Monitoring operation aborted for {path}, likely stopping.")
                elif self.running and not stop_event.is_set(): # Log error only if not stopping
                    logger.error(f"Win32 error in monitoring loop for {path}: ({e.winerror}) {e.strerror}", exc_info=True)
                    time.sleep(1) # Avoid tight loop on error
                else:
                     logger.debug(f"Win32 error during shutdown for {path}: {e.strerror}")
                break # Exit loop on most errors or stop signal
            except Exception as e:
                if self.running and not stop_event.is_set():
                    logger.error(f"Unexpected error in monitoring loop for {path}: {e}", exc_info=True)
                    time.sleep(1)
                else:
                     logger.debug(f"Unexpected exception during shutdown for {path}: {e}")
                break # Exit loop

        # Cleanup handle when thread exits
        self._close_handle_safe(path)
        logger.info(f"Monitoring loop stopped for: {path}")
