# File System Monitor Redesign: Platform Implementations Part 4 - Windows

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the Windows-specific file system monitor using the ReadDirectoryChangesW API. This API provides detailed information about directory changes, including file creation, deletion, modification, and renaming.

## Windows Implementation Details

```python
# src/dbp/fs_monitor/windows.py

import os
import threading
import logging
import time
import ctypes
import ctypes.wintypes
from typing import Dict, Set, List, Optional, Callable, Any, Tuple

from .monitor_base import MonitorBase
from .event_types import EventType, FileSystemEvent
from .exceptions import WatchCreationError
from .watch_manager import WatchManager
from .event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

# Define Windows constants
FILE_LIST_DIRECTORY = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OVERLAPPED = 0x40000000
FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002
FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x00000004
FILE_NOTIFY_CHANGE_SIZE = 0x00000008
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
FILE_NOTIFY_CHANGE_LAST_ACCESS = 0x00000020
FILE_NOTIFY_CHANGE_CREATION = 0x00000040
FILE_NOTIFY_CHANGE_SECURITY = 0x00000100

FILE_ACTION_ADDED = 0x00000001
FILE_ACTION_REMOVED = 0x00000002
FILE_ACTION_MODIFIED = 0x00000003
FILE_ACTION_RENAMED_OLD_NAME = 0x00000004
FILE_ACTION_RENAMED_NEW_NAME = 0x00000005

ERROR_OPERATION_ABORTED = 995

WAIT_ABANDONED = 0x00000080
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF

# Define structure for ReadDirectoryChangesW
class FILE_NOTIFY_INFORMATION(ctypes.Structure):
    """
    [Class intent]
    Represents the FILE_NOTIFY_INFORMATION structure from winbase.h.
    
    [Design principles]
    - Direct mapping to Win32 structure
    - Efficient binary parsing
    
    [Implementation details]
    - Uses ctypes to define the structure
    - Matches the memory layout of the Win32 structure
    """
    _fields_ = [
        ("NextEntryOffset", ctypes.wintypes.DWORD),
        ("Action", ctypes.wintypes.DWORD),
        ("FileNameLength", ctypes.wintypes.DWORD),
        # FileName is a variable-length array of WCHAR
        # We'll handle this specially when parsing
    ]


class WindowsMonitor(MonitorBase):
    """
    [Class intent]
    Windows-specific file system monitor using ReadDirectoryChangesW.
    
    [Design principles]
    - Direct use of Windows ReadDirectoryChangesW API
    - Efficient event translation
    - Resource management
    
    [Implementation details]
    - Uses ReadDirectoryChangesW for file system monitoring
    - Translates Windows events to our event model
    - Manages directory handles and overlapped I/O
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the Windows monitor.
        
        [Design principles]
        - Clean initialization
        - Resource initialization
        
        [Implementation details]
        - Calls parent constructor
        - Initializes Windows handles
        - Sets up data structures for watch mapping
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        super().__init__(watch_manager, event_dispatcher)
        self._watches = {}  # path -> (handle, thread, stop_event)
        self._rename_cache = {}  # path -> path for tracking renames
    
    def start(self) -> None:
        """
        [Function intent]
        Start the Windows monitor.
        
        [Design principles]
        - Clean startup sequence
        - Error handling
        
        [Implementation details]
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("Windows monitor already running")
                return
            
            try:
                # Load required DLLs
                self._kernel32 = ctypes.windll.kernel32
                if not self._kernel32:
                    raise WatchCreationError("Failed to load kernel32.dll")
                
                # Set running flag
                self._running = True
                
                logger.debug("Started Windows monitor")
            except Exception as e:
                self._running = False
                logger.error(f"Error starting Windows monitor: {e}")
                raise
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the Windows monitor.
        
        [Design principles]
        - Clean shutdown sequence
        - Resource cleanup
        
        [Implementation details]
        - Sets running flag to false
        - Stops all watch threads
        - Closes all directory handles
        """
        with self._lock:
            if not self._running:
                logger.debug("Windows monitor already stopped")
                return
            
            # Set running flag to false
            self._running = False
            
            # Stop all watch threads
            for path, (handle, thread, stop_event) in self._watches.items():
                try:
                    # Signal thread to stop
                    stop_event.set()
                    
                    # Cancel any pending I/O operations
                    self._cancel_io(handle)
                    
                    # Wait for thread to terminate
                    if thread.is_alive():
                        thread.join(timeout=1.0)
                    
                    # Close handle
                    self._close_handle(handle)
                except Exception as e:
                    logger.warning(f"Error stopping watch thread for {path}: {e}")
            
            # Clear data structures
            self._watches.clear()
            self._rename_cache.clear()
            
            logger.debug("Stopped Windows monitor")
    
    def add_watch(self, path: str) -> Tuple[int, threading.Thread, threading.Event]:
        """
        [Function intent]
        Add a watch for a directory.
        
        [Design principles]
        - Platform-specific watch creation
        - Resource tracking
        
        [Implementation details]
        - Creates directory handle
        - Starts monitoring thread
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path to watch
            
        Returns:
            Tuple of (handle, thread, stop_event)
            
        Raises:
            WatchCreationError: If the watch cannot be created
        """
        with self._lock:
            if not self._running:
                logger.warning("Windows monitor not running, watch will not be added")
                raise WatchCreationError("Monitor not running")
            
            if path in self._watches:
                return self._watches[path]
            
            try:
                # Ensure path is a directory
                if not os.path.isdir(path):
                    raise WatchCreationError(f"{path} is not a directory")
                
                # Create a stop event for this watch
                stop_event = threading.Event()
                
                # Create directory handle
                handle = self._create_directory_handle(path)
                if handle == -1:
                    raise WatchCreationError(f"Failed to create directory handle for {path}")
                
                # Start monitoring thread
                thread = threading.Thread(
                    target=self._monitor_directory,
                    args=(path, handle, stop_event),
                    daemon=True,
                    name=f"FSMonitor-Windows-{path}"
                )
                thread.start()
                
                # Store the watch
                watch_data = (handle, thread, stop_event)
                self._watches[path] = watch_data
                
                logger.debug(f"Added watch for {path} with handle {handle}")
                return watch_data
            except Exception as e:
                logger.error(f"Error adding watch for {path}: {e}")
                raise WatchCreationError(f"Failed to add watch for {path}: {e}")
    
    def remove_watch(self, path: str, watch_data: Tuple[int, threading.Thread, threading.Event]) -> None:
        """
        [Function intent]
        Remove a watch for a directory.
        
        [Design principles]
        - Platform-specific watch removal
        - Resource cleanup
        
        [Implementation details]
        - Stops the monitoring thread
        - Closes the directory handle
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path that was being watched
            watch_data: Tuple of (handle, thread, stop_event)
        """
        with self._lock:
            if not self._running:
                logger.debug("Windows monitor not running, watch will not be removed")
                return
            
            try:
                # Unpack the watch data
                handle, thread, stop_event = watch_data
                
                # Signal thread to stop
                stop_event.set()
                
                # Cancel any pending I/O operations
                self._cancel_io(handle)
                
                # Wait for thread to terminate
                if thread.is_alive():
                    thread.join(timeout=1.0)
                
                # Close handle
                self._close_handle(handle)
                
                # Remove from mapping
                self._watches.pop(path, None)
                
                logger.debug(f"Removed watch for {path}")
            except Exception as e:
                logger.warning(f"Error removing watch for {path}: {e}")
    
    def _create_directory_handle(self, path: str) -> int:
        """
        [Function intent]
        Create a directory handle for monitoring.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls CreateFileW with appropriate flags
        
        Args:
            path: Path to the directory
            
        Returns:
            Directory handle or -1 on error
        """
        try:
            # Define function parameter types
            self._kernel32.CreateFileW.argtypes = [
                ctypes.c_wchar_p,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.HANDLE
            ]
            self._kernel32.CreateFileW.restype = ctypes.wintypes.HANDLE
            
            # Create directory handle
            handle = self._kernel32.CreateFileW(
                path,  # lpFileName
                FILE_LIST_DIRECTORY,  # dwDesiredAccess
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,  # dwShareMode
                None,  # lpSecurityAttributes
                OPEN_EXISTING,  # dwCreationDisposition
                FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED,  # dwFlagsAndAttributes
                None  # hTemplateFile
            )
            
            # Check if handle is valid
            if handle == -1 or handle == 0xffffffff:
                error = ctypes.GetLastError()
                logger.error(f"CreateFileW failed with error {error}")
                return -1
            
            return handle
        except Exception as e:
            logger.error(f"Error creating directory handle: {e}")
            return -1
    
    def _close_handle(self, handle: int) -> None:
        """
        [Function intent]
        Close a directory handle.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls CloseHandle
        
        Args:
            handle: Directory handle
        """
        try:
            # Define function parameter types
            self._kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
            self._kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
            
            # Close handle
            self._kernel32.CloseHandle(handle)
        except Exception as e:
            logger.error(f"Error closing handle: {e}")
    
    def _cancel_io(self, handle: int) -> None:
        """
        [Function intent]
        Cancel pending I/O operations on a handle.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls CancelIo
        
        Args:
            handle: Directory handle
        """
        try:
            # Define function parameter types
            self._kernel32.CancelIo.argtypes = [ctypes.wintypes.HANDLE]
            self._kernel32.CancelIo.restype = ctypes.wintypes.BOOL
            
            # Cancel I/O
            self._kernel32.CancelIo(handle)
        except Exception as e:
            logger.error(f"Error canceling I/O: {e}")
    
    def _monitor_directory(self, path: str, handle: int, stop_event: threading.Event) -> None:
        """
        [Function intent]
        Monitor a directory for changes.
        
        [Design principles]
        - Continuous event processing
        - Event translation
        
        [Implementation details]
        - Uses ReadDirectoryChangesW to monitor changes
        - Translates Windows events to our event model
        - Dispatches events to the event dispatcher
        
        Args:
            path: Directory path
            handle: Directory handle
            stop_event: Event to signal thread stop
        """
        try:
            # Create overlapped structure
            overlapped = self._create_overlapped()
            
            # Create buffer for changes
            buffer_size = 8192
            buffer = ctypes.create_string_buffer(buffer_size)
            
            # Define the changes to monitor
            change_flags = (
                FILE_NOTIFY_CHANGE_FILE_NAME |
                FILE_NOTIFY_CHANGE_DIR_NAME |
                FILE_NOTIFY_CHANGE_ATTRIBUTES |
                FILE_NOTIFY_CHANGE_SIZE |
                FILE_NOTIFY_CHANGE_LAST_WRITE |
                FILE_NOTIFY_CHANGE_CREATION
            )
            
            while not stop_event.is_set() and self._running:
                # Start the directory monitoring
                success = self._read_directory_changes(handle, buffer, buffer_size,
                                                     True, change_flags, overlapped)
                
                if not success:
                    error = ctypes.GetLastError()
                    if error != ERROR_OPERATION_ABORTED:  # Not cancelled by us
                        logger.error(f"ReadDirectoryChangesW failed with error {error}")
                        time.sleep(1)  # Avoid tight loop on error
                    continue
                
                # Wait for changes or stop event
                wait_result = self._wait_for_changes(overlapped.hEvent, stop_event)
                
                if wait_result == WAIT_OBJECT_0:
                    # Get the results
                    bytes_returned = self._get_overlapped_result(handle, overlapped)
                    
                    if bytes_returned > 0:
                        # Process the changes
                        self._process_changes(path, buffer, bytes_returned)
                elif wait_result == WAIT_OBJECT_0 + 1:
                    # Stop event was signaled
                    break
                elif wait_result == WAIT_TIMEOUT:
                    # Timeout, just continue
                    continue
                else:
                    # Error
                    error = ctypes.GetLastError()
                    logger.error(f"WaitForMultipleObjects failed with error {error}")
                    time.sleep(1)  # Avoid tight loop on error
            
            # Clean up
            self._close_overlapped(overlapped)
        except Exception as e:
            logger.error(f"Error monitoring directory {path}: {e}")
    
    def _read_directory_changes(self, handle: int, buffer: Any, buffer_size: int,
                              watch_subtree: bool, notify_filter: int, overlapped: Any) -> bool:
        """
        [Function intent]
        Read directory changes.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls ReadDirectoryChangesW
        
        Args:
            handle: Directory handle
            buffer: Buffer to receive changes
            buffer_size: Size of the buffer
            watch_subtree: Whether to watch subdirectories
            notify_filter: Events to watch for
            overlapped: Overlapped I/O structure
            
        Returns:
            True on success, False on error
        """
        try:
            # Define function parameter types
            self._kernel32.ReadDirectoryChangesW.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.c_void_p,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.BOOL,
                ctypes.wintypes.DWORD,
                ctypes.POINTER(ctypes.wintypes.DWORD),
                ctypes.c_void_p,
                ctypes.c_void_p
            ]
            self._kernel32.ReadDirectoryChangesW.restype = ctypes.wintypes.BOOL
            
            # Call ReadDirectoryChangesW
            bytes_returned = ctypes.wintypes.DWORD()
            result = self._kernel32.ReadDirectoryChangesW(
                handle,  # hDirectory
                buffer,  # lpBuffer
                buffer_size,  # nBufferLength
                watch_subtree,  # bWatchSubtree
                notify_filter,  # dwNotifyFilter
                ctypes.byref(bytes_returned),  # lpBytesReturned
                overlapped,  # lpOverlapped
                None  # lpCompletionRoutine
            )
            
            return result != 0
        except Exception as e:
            logger.error(f"Error reading directory changes: {e}")
            return False
    
    def _wait_for_changes(self, event_handle: int, stop_event: threading.Event) -> int:
        """
        [Function intent]
        Wait for changes or thread stop.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls WaitForMultipleObjects
        
        Args:
            event_handle: Handle to the overlapped event
            stop_event: Event to signal thread stop
            
        Returns:
            Wait result code
        """
        try:
            # Get the handle of the stop event
            stop_event_handle = self._kernel32.CreateEventW(None, True, False, None)
            
            # Define function parameter types
            self._kernel32.WaitForMultipleObjects.argtypes = [
                ctypes.wintypes.DWORD,
                ctypes.POINTER(ctypes.wintypes.HANDLE),
                ctypes.wintypes.BOOL,
                ctypes.wintypes.DWORD
            ]
            self._kernel32.WaitForMultipleObjects.restype = ctypes.wintypes.DWORD
            
            # Create array of handles
            handles = (ctypes.wintypes.HANDLE * 2)(event_handle, stop_event_handle)
            
            # Wait for any of the events
            result = self._kernel32.WaitForMultipleObjects(
                2,  # nCount
                handles,  # lpHandles
                False,  # bWaitAll
                1000  # dwMilliseconds (timeout)
            )
            
            return result
        except Exception as e:
            logger.error(f"Error waiting for changes: {e}")
            return WAIT_FAILED
    
    def _get_overlapped_result(self, handle: int, overlapped: Any) -> int:
        """
        [Function intent]
        Get the result of an overlapped operation.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Calls GetOverlappedResult
        
        Args:
            handle: Directory handle
            overlapped: Overlapped I/O structure
            
        Returns:
            Number of bytes transferred
        """
        try:
            # Define function parameter types
            self._kernel32.GetOverlappedResult.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.wintypes.DWORD),
                ctypes.wintypes.BOOL
            ]
            self._kernel32.GetOverlappedResult.restype = ctypes.wintypes.BOOL
            
            # Get the result
            bytes_transferred = ctypes.wintypes.DWORD()
            self._kernel32.GetOverlappedResult(
                handle,  # hFile
                overlapped,  # lpOverlapped
                ctypes.byref(bytes_transferred),  # lpNumberOfBytesTransferred
                False  # bWait
            )
            
            return bytes_transferred.value
        except Exception as e:
            logger.error(f"Error getting overlapped result: {e}")
            return 0
    
    def _process_changes(self, directory: str, buffer: Any, bytes_returned: int) -> None:
        """
        [Function intent]
        Process directory change notifications.
        
        [Design principles]
        - Event translation
        - Efficient binary parsing
        
        [Implementation details]
        - Parses FILE_NOTIFY_INFORMATION structures
        - Translates Windows file actions to our event model
        - Handles renames by caching old names
        
        Args:
            directory: Base directory
            buffer: Buffer containing change information
            bytes_returned: Number of bytes returned
        """
        offset = 0
        
        while offset < bytes_returned:
            # Cast the buffer to FILE_NOTIFY_INFORMATION
            info = FILE_NOTIFY_INFORMATION.from_buffer(buffer, offset)
            
            # Extract the filename (it's a variable-length array of WCHAR)
            filename_bytes = bytearray(buffer[offset + 12:offset + 12 + info.FileNameLength])
            filename = filename_bytes.decode('utf-16le')
            
            # Construct the full path
            path = os.path.join(directory, filename)
            
            # Translate the action to our event model
            if info.Action == FILE_ACTION_ADDED:
                if os.path.isdir(path):
                    self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                elif os.path.islink(path):
                    target = os.readlink(path)
                    self.dispatch_event(EventType.SYMLINK_CREATED, path, None, target)
                else:
                    self.dispatch_event(EventType.FILE_CREATED, path)
            
            elif info.Action == FILE_ACTION_REMOVED:
                # We don't know if it was a file, directory, or symlink
                # For now, assume it was a file
                self.dispatch_event(EventType.FILE_DELETED, path)
            
            elif info.Action == FILE_ACTION_MODIFIED:
                if os.path.isdir(path):
                    # Directories don't have a modified event in our model
                    pass
                elif os.path.islink(path):
                    # Check if the target has changed
                    # This would require additional state tracking
                    pass
                else:
                    self.dispatch_event(EventType.FILE_MODIFIED, path)
            
            elif info.Action == FILE_ACTION_RENAMED_OLD_NAME:
                # Store the old name for the corresponding RENAMED_NEW_NAME event
                self._rename_cache[directory] = path
            
            elif info.Action == FILE_ACTION_RENAMED_NEW_NAME:
                old_path = self._rename_cache.pop(directory, None)
                if old_path:
                    # Report as delete + create
                    if os.path.isdir(path):
                        self.dispatch_event(EventType.DIRECTORY_DELETED, old_path)
                        self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                    elif os.path.islink(path):
                        self.dispatch_event(EventType.SYMLINK_DELETED, old_path)
                        target = os.readlink(path)
                        self.dispatch_event(EventType.SYMLINK_CREATED, path, None, target)
                    else:
                        self.dispatch_event(EventType.FILE_DELETED, old_path)
                        self.dispatch_event(EventType.FILE_CREATED, path)
                else:
                    # We missed the old name event, just report as created
                    if os.path.isdir(path):
                        self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                    elif os.path.islink(path):
                        target = os.readlink(path)
                        self.dispatch_event(EventType.SYMLINK_CREATED, path, None, target)
                    else:
                        self.dispatch_event(EventType.FILE_CREATED, path)
            
            # Move to the next entry
            if info.NextEntryOffset == 0:
                break
            offset += info.NextEntryOffset
    
    def _create_overlapped(self) -> Any:
        """
        [Function intent]
        Create an overlapped I/O structure.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Creates OVERLAPPED structure with an event
        
        Returns:
            Overlapped I/O structure
        """
        # Define OVERLAPPED structure
        class OVERLAPPED(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.POINTER(ctypes.wintypes.ULONG)),
                ("InternalHigh", ctypes.POINTER(ctypes.wintypes.ULONG)),
                ("Offset", ctypes.wintypes.DWORD),
                ("OffsetHigh", ctypes.wintypes.DWORD),
                ("hEvent", ctypes.wintypes.HANDLE)
            ]
        
        # Create event for the overlapped structure
        event = self._kernel32.CreateEventW(None, True, False, None)
        
        # Create and initialize the structure
        overlapped = OVERLAPPED()
        overlapped.Internal = None
        overlapped.InternalHigh = None
        overlapped.Offset = 0
        overlapped.OffsetHigh = 0
        overlapped.hEvent = event
        
        return overlapped
    
    def _close_overlapped(self, overlapped: Any) -> None:
        """
        [Function intent]
        Close an overlapped I/O structure.
        
        [Design principles]
        - Direct interface to Windows API
        
        [Implementation details]
        - Closes the event handle
        
        Args:
            overlapped: Overlapped I/O structure
        """
        if overlapped and overlapped.hEvent:
            self._kernel32.CloseHandle(overlapped.hEvent)
```

## Key Implementation Features

### Low-level ReadDirectoryChangesW API Access

The Windows implementation uses `ctypes` to directly interface with the ReadDirectoryChangesW API provided by the Windows kernel:

1. **CreateFileW**: Opens a directory with appropriate flags
2. **ReadDirectoryChangesW**: Sets up monitoring for directory changes
3. **WaitForMultipleObjects**: Waits for changes or stop events
4. **GetOverlappedResult**: Gets the results of an overlapped I/O operation
5. **CancelIo**: Cancels pending I/O operations
6. **CloseHandle**: Closes file and event handles

### Overlapped I/O

The implementation uses overlapped I/O to asynchronously monitor directory changes:

1. Creates an OVERLAPPED structure with an event handle
2. Sets up asynchronous ReadDirectoryChangesW calls
3. Waits for event signaling or timeout
4. Processes results as they arrive

### Event Translation

The implementation translates Windows file actions to our unified event model:

| Windows File Action | Our Event Model |
|--------------------|-----------------|
| FILE_ACTION_ADDED & isDir | DIRECTORY_CREATED |
| FILE_ACTION_ADDED & isSymlink | SYMLINK_CREATED |
| FILE_ACTION_ADDED & isFile | FILE_CREATED |
| FILE_ACTION_REMOVED | FILE_DELETED or DIRECTORY_DELETED |
| FILE_ACTION_MODIFIED & isFile | FILE_MODIFIED |
| FILE_ACTION_RENAMED_* | Handled specially with delete + create events |

### Binary Parsing

The implementation parses the FILE_NOTIFY_INFORMATION structure returned by ReadDirectoryChangesW:

```
typedef struct _FILE_NOTIFY_INFORMATION {
    DWORD NextEntryOffset;
    DWORD Action;
    DWORD FileNameLength;
    WCHAR FileName[1]; // Variable-length array
} FILE_NOTIFY_INFORMATION;
```

### Rename Handling

Renames in Windows are reported as two separate events:
1. FILE_ACTION_RENAMED_OLD_NAME with the original path
2. FILE_ACTION_RENAMED_NEW_NAME with the new path

The implementation caches the old name when the first event arrives, then uses it when processing the second event to generate appropriate delete/create events.

## Windows-Specific Considerations

1. **Access Rights**: The implementation needs appropriate file system permissions to monitor directories.

2. **Subtree Monitoring**: ReadDirectoryChangesW can watch subdirectories recursively.

3. **Buffer Size**: The buffer must be large enough to hold multiple change notifications.

4. **Error Handling**: The implementation needs to handle various error cases, such as:
   - Access denied errors
   - Handle closure
   - I/O cancellation

5. **Resource Cleanup**: The implementation must properly close handles and clean up resources.

## Testing Strategy

The Windows implementation should be tested with the following strategies:

1. **Unit Tests**:
   - Test event translation
   - Test handle creation and closure
   - Test overlapped I/O operations

2. **Integration Tests**:
   - Test with the watch manager and event dispatcher
   - Test with multiple watches
   - Test recursive watching

3. **Edge Cases**:
   - Test with nested directories
   - Test with symlinks
   - Test with file moves and renames
   - Test with large numbers of events
   - Test with long file paths
