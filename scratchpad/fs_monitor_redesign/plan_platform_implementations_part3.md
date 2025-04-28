# File System Monitor Redesign: Platform Implementations Part 3 - macOS (FSEvents)

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the macOS-specific file system monitor using the FSEvents API. The FSEvents API allows applications to register for notifications of changes to directories and their contents.

## Implementation Details

### macOS Monitor Implementation

```python
# src/dbp/fs_monitor/macos.py

import os
import threading
import logging
import time
from typing import Dict, Set, List, Optional, Callable, Any
import ctypes
import ctypes.util

from .monitor_base import MonitorBase
from .event_types import EventType, FileSystemEvent
from .exceptions import WatchCreationError
from .watch_manager import WatchManager
from .event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

# Define FSEvents constants
# From FSEvents.h
kFSEventStreamEventFlagNone = 0x00000000
kFSEventStreamEventFlagMustScanSubDirs = 0x00000001
kFSEventStreamEventFlagUserDropped = 0x00000002
kFSEventStreamEventFlagKernelDropped = 0x00000004
kFSEventStreamEventFlagEventIdsWrapped = 0x00000008
kFSEventStreamEventFlagHistoryDone = 0x00000010
kFSEventStreamEventFlagRootChanged = 0x00000020
kFSEventStreamEventFlagMount = 0x00000040
kFSEventStreamEventFlagUnmount = 0x00000080
kFSEventStreamEventFlagItemCreated = 0x00000100
kFSEventStreamEventFlagItemRemoved = 0x00000200
kFSEventStreamEventFlagItemInodeMetaMod = 0x00000400
kFSEventStreamEventFlagItemRenamed = 0x00000800
kFSEventStreamEventFlagItemModified = 0x00001000
kFSEventStreamEventFlagItemFinderInfoMod = 0x00002000
kFSEventStreamEventFlagItemChangeOwner = 0x00004000
kFSEventStreamEventFlagItemXattrMod = 0x00008000
kFSEventStreamEventFlagItemIsFile = 0x00010000
kFSEventStreamEventFlagItemIsDir = 0x00020000
kFSEventStreamEventFlagItemIsSymlink = 0x00040000

# FSEvents callback types
FSEventStreamCallback = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,  # FSEventStreamRef
    ctypes.c_void_p,  # callback_info
    ctypes.c_size_t,  # num_events
    ctypes.c_void_p,  # event_paths
    ctypes.POINTER(ctypes.c_uint32),  # event_flags
    ctypes.POINTER(ctypes.c_uint64)   # event_ids
)


class MacOSMonitor(MonitorBase):
    """
    [Class intent]
    macOS-specific file system monitor using FSEvents.
    
    [Design principles]
    - Direct use of macOS FSEvents API
    - Efficient event translation
    - Resource management
    
    [Implementation details]
    - Uses FSEvents for file system monitoring
    - Translates FSEvents events to our event model
    - Manages FSEvents streams and callbacks
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the macOS monitor.
        
        [Design principles]
        - Clean initialization
        - Resource initialization
        
        [Implementation details]
        - Calls parent constructor
        - Initializes FSEvents resources
        - Sets up data structures for watch mapping
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        super().__init__(watch_manager, event_dispatcher)
        self._streams = {}  # path -> FSEventStreamRef
        self._run_loop_ref = None
        self._run_loop_thread = None
        
        # Load the CoreServices framework
        try:
            self._core_services = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreServices.framework/CoreServices')
            logger.debug("Loaded CoreServices framework")
        except Exception as e:
            logger.error(f"Error loading CoreServices framework: {e}")
            self._core_services = None
    
    def start(self) -> None:
        """
        [Function intent]
        Start the macOS monitor.
        
        [Design principles]
        - Clean startup sequence
        - Error handling
        
        [Implementation details]
        - Creates the run loop thread
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("macOS monitor already running")
                return
            
            if not self._core_services:
                raise WatchCreationError("CoreServices framework not loaded")
            
            try:
                # Start the run loop thread
                self._running = True
                self._run_loop_thread = threading.Thread(
                    target=self._run_loop,
                    daemon=True,
                    name="FSMonitor-macOS"
                )
                self._run_loop_thread.start()
                
                # Wait for the run loop to start
                time.sleep(0.1)
                
                logger.debug("Started macOS monitor")
            except Exception as e:
                self._running = False
                logger.error(f"Error starting macOS monitor: {e}")
                raise
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the macOS monitor.
        
        [Design principles]
        - Clean shutdown sequence
        - Resource cleanup
        
        [Implementation details]
        - Sets running flag to false
        - Stops all FSEvents streams
        - Stops the run loop
        """
        with self._lock:
            if not self._running:
                logger.debug("macOS monitor already stopped")
                return
            
            # Set running flag to false
            self._running = False
            
            # Stop the run loop
            if self._run_loop_ref:
                try:
                    # This will be executed on the run loop thread
                    self._stop_run_loop(self._run_loop_ref)
                except Exception as e:
                    logger.warning(f"Error stopping run loop: {e}")
                
                # Wait for the run loop thread to terminate
                if self._run_loop_thread and self._run_loop_thread.is_alive():
                    self._run_loop_thread.join(timeout=1.0)
            
            # Clear streams
            self._streams.clear()
            
            logger.debug("Stopped macOS monitor")
    
    def add_watch(self, path: str) -> Any:
        """
        [Function intent]
        Add an FSEvents watch for a path.
        
        [Design principles]
        - Platform-specific watch creation
        - Resource tracking
        
        [Implementation details]
        - Creates FSEvents stream for the path
        - Sets up callback for events
        - Starts the stream
        
        Args:
            path: Absolute path to watch
            
        Returns:
            FSEvents stream reference
            
        Raises:
            WatchCreationError: If the watch cannot be added
        """
        with self._lock:
            if not self._running:
                logger.warning("macOS monitor not running, watch will not be added")
                raise WatchCreationError("Monitor not running")
            
            if path in self._streams:
                return self._streams[path]
            
            try:
                # Create the stream
                stream_ref = self._create_fs_events_stream(path)
                if not stream_ref:
                    raise WatchCreationError(f"Failed to create FSEvents stream for {path}")
                
                # Start the stream
                self._start_fs_events_stream(stream_ref)
                
                # Store the stream
                self._streams[path] = stream_ref
                
                logger.debug(f"Added watch for {path}")
                return stream_ref
            except Exception as e:
                logger.error(f"Error adding watch for {path}: {e}")
                raise WatchCreationError(f"Failed to add watch for {path}: {e}")
    
    def remove_watch(self, path: str, stream_ref: Any) -> None:
        """
        [Function intent]
        Remove an FSEvents watch.
        
        [Design principles]
        - Platform-specific watch removal
        - Resource cleanup
        
        [Implementation details]
        - Stops the FSEvents stream
        - Releases stream resources
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path that was being watched
            stream_ref: FSEvents stream reference
        """
        with self._lock:
            if not self._running:
                logger.debug("macOS monitor not running, watch will not be removed")
                return
            
            try:
                # Stop and release the stream
                self._stop_fs_events_stream(stream_ref)
                self._release_fs_events_stream(stream_ref)
                
                # Remove from mapping
                self._streams.pop(path, None)
                
                logger.debug(f"Removed watch for {path}")
            except Exception as e:
                logger.warning(f"Error removing watch for {path}: {e}")
    
    def _run_loop(self) -> None:
        """
        [Function intent]
        Main loop for the FSEvents run loop thread.
        
        [Design principles]
        - Continuous event processing
        
        [Implementation details]
        - Creates and runs the CFRunLoop
        """
        try:
            # Get the CFRunLoop for this thread
            self._run_loop_ref = self._get_cf_run_loop()
            if not self._run_loop_ref:
                logger.error("Failed to get CFRunLoop")
                return
            
            # Run the run loop
            self._run_cf_run_loop(self._run_loop_ref)
            
            # The run loop has been stopped
            logger.debug("CFRunLoop stopped")
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
        finally:
            self._run_loop_ref = None
    
    def _create_fs_events_stream(self, path: str) -> Any:
        """
        [Function intent]
        Create an FSEvents stream for a path.
        
        [Design principles]
        - Direct interface to FSEvents API
        
        [Implementation details]
        - Creates a callback for the stream
        - Sets up stream context
        - Creates the stream
        
        Args:
            path: Path to watch
            
        Returns:
            FSEvents stream reference
        """
        if not self._core_services:
            logger.error("CoreServices framework not loaded")
            return None
        
        try:
            # Create a callback function
            def fs_events_callback(
                stream_ref: Any,
                callback_info: Any,
                num_events: int,
                event_paths: Any,
                event_flags: Any,
                event_ids: Any
            ) -> None:
                self._fs_events_callback(
                    stream_ref, callback_info, num_events,
                    event_paths, event_flags, event_ids
                )
            
            # Convert the callback to a C function pointer
            callback = FSEventStreamCallback(fs_events_callback)
            
            # Create the path array
            path_array = self._create_cf_array_from_paths([path])
            if not path_array:
                logger.error("Failed to create path array")
                return None
            
            # Define the event flags we want to receive
            event_flags = (
                kFSEventStreamEventFlagItemCreated |
                kFSEventStreamEventFlagItemRemoved |
                kFSEventStreamEventFlagItemRenamed |
                kFSEventStreamEventFlagItemModified
            )
            
            # Create the stream
            stream_ref = self._core_services.FSEventStreamCreate(
                None,  # allocator
                callback,  # callback
                None,  # callback_info
                path_array,  # paths_to_watch
                ctypes.c_uint64(0),  # since_when (start with the next event)
                ctypes.c_double(0.1),  # latency (seconds)
                event_flags  # flags
            )
            
            # Clean up
            self._release_cf_object(path_array)
            
            return stream_ref
        except Exception as e:
            logger.error(f"Error creating FSEvents stream for {path}: {e}")
            return None
    
    def _start_fs_events_stream(self, stream_ref: Any) -> None:
        """
        [Function intent]
        Start an FSEvents stream.
        
        [Design principles]
        - Direct interface to FSEvents API
        
        [Implementation details]
        - Schedules the stream on the run loop
        - Starts the stream
        
        Args:
            stream_ref: FSEvents stream reference
        """
        if not self._core_services or not stream_ref:
            return
        
        try:
            # Schedule the stream on the run loop
            self._core_services.FSEventStreamScheduleWithRunLoop(
                stream_ref,
                self._run_loop_ref,
                ctypes.c_void_p.in_dll(self._core_services, 'kCFRunLoopDefaultMode')
            )
            
            # Start the stream
            self._core_services.FSEventStreamStart(stream_ref)
        except Exception as e:
            logger.error(f"Error starting FSEvents stream: {e}")
    
    def _stop_fs_events_stream(self, stream_ref: Any) -> None:
        """
        [Function intent]
        Stop an FSEvents stream.
        
        [Design principles]
        - Direct interface to FSEvents API
        
        [Implementation details]
        - Stops the stream
        - Invalidates the stream
        
        Args:
            stream_ref: FSEvents stream reference
        """
        if not self._core_services or not stream_ref:
            return
        
        try:
            # Stop the stream
            self._core_services.FSEventStreamStop(stream_ref)
            
            # Invalidate the stream
            self._core_services.FSEventStreamInvalidate(stream_ref)
        except Exception as e:
            logger.error(f"Error stopping FSEvents stream: {e}")
    
    def _release_fs_events_stream(self, stream_ref: Any) -> None:
        """
        [Function intent]
        Release an FSEvents stream.
        
        [Design principles]
        - Direct interface to FSEvents API
        
        [Implementation details]
        - Releases the stream
        
        Args:
            stream_ref: FSEvents stream reference
        """
        if not self._core_services or not stream_ref:
            return
        
        try:
            # Release the stream
            self._core_services.FSEventStreamRelease(stream_ref)
        except Exception as e:
            logger.error(f"Error releasing FSEvents stream: {e}")
    
    def _fs_events_callback(self, stream_ref: Any, callback_info: Any,
                           num_events: int, event_paths: Any, event_flags: Any, event_ids: Any) -> None:
        """
        [Function intent]
        Callback for FSEvents stream events.
        
        [Design principles]
        - Event translation
        - Dispatch to event dispatcher
        
        [Implementation details]
        - Translates FSEvents events to our event model
        - Dispatches events to the event dispatcher
        
        Args:
            stream_ref: FSEvents stream reference
            callback_info: User-defined callback info
            num_events: Number of events
            event_paths: Array of paths
            event_flags: Array of event flags
            event_ids: Array of event IDs
        """
        if not self._running:
            return
        
        try:
            # Convert event_paths to a Python list
            paths = self._convert_cf_array_to_paths(event_paths, num_events)
            
            # Process each event
            for i in range(num_events):
                path = paths[i]
                flags = event_flags[i]
                
                # Determine the event type
                is_file = bool(flags & kFSEventStreamEventFlagItemIsFile)
                is_dir = bool(flags & kFSEventStreamEventFlagItemIsDir)
                is_symlink = bool(flags & kFSEventStreamEventFlagItemIsSymlink)
                is_created = bool(flags & kFSEventStreamEventFlagItemCreated)
                is_removed = bool(flags & kFSEventStreamEventFlagItemRemoved)
                is_renamed = bool(flags & kFSEventStreamEventFlagItemRenamed)
                is_modified = bool(flags & kFSEventStreamEventFlagItemModified)
                
                # Dispatch events based on the flags
                if is_created:
                    if is_dir:
                        self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                    elif is_symlink:
                        target = os.readlink(path) if os.path.exists(path) else None
                        self.dispatch_event(EventType.SYMLINK_CREATED, path, None, target)
                    else:
                        self.dispatch_event(EventType.FILE_CREATED, path)
                
                if is_removed:
                    if is_dir:
                        self.dispatch_event(EventType.DIRECTORY_DELETED, path)
                    elif is_symlink:
                        self.dispatch_event(EventType.SYMLINK_DELETED, path)
                    else:
                        self.dispatch_event(EventType.FILE_DELETED, path)
                
                if is_renamed:
                    # Renames are complex and may require additional state tracking
                    # For now, we'll just report a creation or deletion
                    if os.path.exists(path):
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                        elif is_symlink:
                            target = os.readlink(path)
                            self.dispatch_event(EventType.SYMLINK_CREATED, path, None, target)
                        else:
                            self.dispatch_event(EventType.FILE_CREATED, path)
                    else:
                        if is_dir:
                            self.dispatch_event(EventType.DIRECTORY_DELETED, path)
                        elif is_symlink:
                            self.dispatch_event(EventType.SYMLINK_DELETED, path)
                        else:
                            self.dispatch_event(EventType.FILE_DELETED, path)
                
                if is_modified and not is_dir and not is_renamed and not is_created and not is_removed:
                    if is_symlink:
                        # Check if the target has changed
                        # This would require additional state tracking
                        pass
                    else:
                        self.dispatch_event(EventType.FILE_MODIFIED, path)
        except Exception as e:
            logger.error(f"Error in FSEvents callback: {e}")
    
    # Core Foundation API wrappers
    
    def _get_cf_run_loop(self) -> Any:
        """
        [Function intent]
        Get the CFRunLoop for the current thread.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Calls CFRunLoopGetCurrent
        
        Returns:
            CFRunLoopRef
        """
        if not self._core_services:
            return None
        
        try:
            return self._core_services.CFRunLoopGetCurrent()
        except Exception as e:
            logger.error(f"Error getting CFRunLoop: {e}")
            return None
    
    def _run_cf_run_loop(self, run_loop_ref: Any) -> None:
        """
        [Function intent]
        Run the CFRunLoop.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Calls CFRunLoopRun
        
        Args:
            run_loop_ref: CFRunLoopRef
        """
        if not self._core_services or not run_loop_ref:
            return
        
        try:
            self._core_services.CFRunLoopRun()
        except Exception as e:
            logger.error(f"Error running CFRunLoop: {e}")
    
    def _stop_run_loop(self, run_loop_ref: Any) -> None:
        """
        [Function intent]
        Stop the CFRunLoop.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Calls CFRunLoopStop
        
        Args:
            run_loop_ref: CFRunLoopRef
        """
        if not self._core_services or not run_loop_ref:
            return
        
        try:
            self._core_services.CFRunLoopStop(run_loop_ref)
        except Exception as e:
            logger.error(f"Error stopping CFRunLoop: {e}")
    
    def _create_cf_array_from_paths(self, paths: List[str]) -> Any:
        """
        [Function intent]
        Create a CFArray from a list of paths.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Creates CFString objects for each path
        - Creates a CFArray containing the CFStrings
        
        Args:
            paths: List of paths
            
        Returns:
            CFArrayRef
        """
        if not self._core_services:
            return None
        
        try:
            # Create CFString objects for each path
            cf_paths = []
            for path in paths:
                cf_string = self._create_cf_string(path)
                if cf_string:
                    cf_paths.append(cf_string)
            
            # Create a CFArray
            cf_array = self._core_services.CFArrayCreate(
                None,  # allocator
                (ctypes.c_void_p * len(cf_paths))(*cf_paths),  # values
                len(cf_paths),  # numValues
                ctypes.c_void_p.in_dll(self._core_services, 'kCFTypeArrayCallBacks')  # callbacks
            )
            
            # Release the CFString objects
            for cf_string in cf_paths:
                self._release_cf_object(cf_string)
            
            return cf_array
        except Exception as e:
            logger.error(f"Error creating CFArray: {e}")
            return None
    
    def _convert_cf_array_to_paths(self, cf_array: Any, count: int) -> List[str]:
        """
        [Function intent]
        Convert a CFArray of CFStrings to a list of paths.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Extracts CFString objects from the CFArray
        - Converts CFString objects to Python strings
        
        Args:
            cf_array: CFArrayRef
            count: Number of items in the array
            
        Returns:
            List of paths
        """
        if not self._core_services or not cf_array:
            return []
        
        try:
            paths = []
            for i in range(count):
                cf_string = self._core_services.CFArrayGetValueAtIndex(cf_array, i)
                path = self._convert_cf_string_to_string(cf_string)
                if path:
                    paths.append(path)
            return paths
        except Exception as e:
            logger.error(f"Error converting CFArray to paths: {e}")
            return []
    
    def _create_cf_string(self, string: str) -> Any:
        """
        [Function intent]
        Create a CFString from a Python string.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Calls CFStringCreateWithCString
        
        Args:
            string: Python string
            
        Returns:
            CFStringRef
        """
        if not self._core_services:
            return None
        
        try:
            # Create a CFString
            return self._core_services.CFStringCreateWithCString(
                None,  # allocator
                string.encode('utf-8'),  # cStr
                ctypes.c_uint32(0x08000100)  # kCFStringEncodingUTF8
            )
        except Exception as e:
            logger.error(f"Error creating CFString: {e}")
            return None
    
    def _convert_cf_string_to_string(self, cf_string: Any) -> Optional[str]:
        """
        [Function intent]
        Convert a CFString to a Python string.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Gets the length of the CFString
        - Gets the UTF-8 representation of the CFString
        
        Args:
            cf_string: CFStringRef
            
        Returns:
            Python string or None
        """
        if not self._core_services or not cf_string:
            return None
        
        try:
            # Get the length of the CFString
            length = self._core_services.CFStringGetLength(cf_string)
            if length == 0:
                return ""
            
            # Get the maximum size of the string in UTF-8 encoding
            max_size = self._core_services.CFStringGetMaximumSizeForEncoding(
                length,
                ctypes.c_uint32(0x08000100)  # kCFStringEncodingUTF8
            )
            
            # Create a buffer to hold the string
            buffer = ctypes.create_string_buffer(max_size + 1)
            
            # Get the UTF-8 representation of the string
            result = self._core_services.CFStringGetCString(
                cf_string,
                buffer,
                max_size + 1,
                ctypes.c_uint32(0x08000100)  # kCFStringEncodingUTF8
            )
            
            if result:
                return buffer.value.decode('utf-8')
            else:
                return None
        except Exception as e:
            logger.error(f"Error converting CFString to string: {e}")
            return None
    
    def _release_cf_object(self, cf_object: Any) -> None:
        """
        [Function intent]
        Release a Core Foundation object.
        
        [Design principles]
        - Direct interface to Core Foundation API
        
        [Implementation details]
        - Calls CFRelease
        
        Args:
            cf_object: CF object reference
        """
        if not self._core_services or not cf_object:
            return
        
        try:
            self._core_services.CFRelease(cf_object)
        except Exception as e:
            logger.error(f"Error releasing CF object: {e}")
```

## Key Implementation Features

### Low-level FSEvents API Access

The macOS implementation uses `ctypes` to directly interface with the FSEvents API provided by the Core Services framework:

1. **FSEventStreamCreate**: Creates a new FSEvents stream
2. **FSEventStreamScheduleWithRunLoop**: Schedules a stream on a run loop
3. **FSEventStreamStart**: Starts a stream
4. **FSEventStreamStop**: Stops a stream
5. **FSEventStreamInvalidate**: Invalidates a stream
6. **FSEventStreamRelease**: Releases a stream

### Core Foundation Integration

The implementation also interfaces with the Core Foundation framework for various supporting functions:

1. **CFRunLoopGetCurrent**: Gets the run loop for the current thread
2. **CFRunLoopRun**: Runs a run loop
3. **CFRunLoopStop**: Stops a run loop
4. **CFStringCreateWithCString**: Creates a CF string from a C string
5. **CFArrayCreate**: Creates a CF array
6. **CFRelease**: Releases a CF object

### Event Translation

The implementation translates FSEvents events to our unified event model:

| FSEvents Flag | Our Event Model |
|---------------|-----------------|
| kFSEventStreamEventFlagItemCreated & kFSEventStreamEventFlagItemIsFile | FILE_CREATED |
| kFSEventStreamEventFlagItemCreated & kFSEventStreamEventFlagItemIsDir | DIRECTORY_CREATED |
| kFSEventStreamEventFlagItemCreated & kFSEventStreamEventFlagItemIsSymlink | SYMLINK_CREATED |
| kFSEventStreamEventFlagItemRemoved & kFSEventStreamEventFlagItemIsFile | FILE_DELETED |
| kFSEventStreamEventFlagItemRemoved & kFSEventStreamEventFlagItemIsDir | DIRECTORY_DELETED |
| kFSEventStreamEventFlagItemRemoved & kFSEventStreamEventFlagItemIsSymlink | SYMLINK_DELETED |
| kFSEventStreamEventFlagItemModified & kFSEventStreamEventFlagItemIsFile | FILE_MODIFIED |
| kFSEventStreamEventFlagItemRenamed | Treated as creation/deletion based on path existence |

### Event Callback

The implementation uses a callback function to receive events from the FSEvents API:

```
typedef void(*FSEventStreamCallback)(
  ConstFSEventStreamRef streamRef,
  void *clientCallBackInfo,
  size_t numEvents,
  void *eventPaths,
  const FSEventStreamEventFlags eventFlags[],
  const FSEventStreamEventId eventIds[]
);
```

### Run Loop Integration

FSEvents relies on the Core Foundation run loop for event handling. The implementation:
1. Creates a dedicated thread for the run loop
2. Creates and schedules FSEvents streams on this run loop
3. Handles communication between the run loop thread and the main thread

## macOS-Specific Considerations

1. **Framework Loading**: The implementation needs to load the CoreServices framework to access the FSEvents API.

2. **Run Loop Management**: FSEvents requires a run loop to function properly. The implementation creates a dedicated thread with a run loop for event processing.

3. **Event Flags**: FSEvents provides detailed flags for events, which can be used to determine the type of event (file/directory/symlink, created/modified/removed/renamed).

4. **Resource Management**: The implementation needs to manage CoreServices objects (CFString, CFArray, FSEventStreamRef) to prevent memory leaks.

5. **Error Handling**: The implementation needs to handle various error cases, such as:
   - Framework loading failure
   - Stream creation failure
   - Run loop initialization failure

## Testing Strategy

The macOS implementation should be tested with the following strategies:

1. **Unit Tests**:
   - Test event translation
   - Test CF object conversion
   - Test run loop management

2. **Integration Tests**:
   - Test with the watch manager and event dispatcher
   - Test with multiple watches

3. **Edge Cases**:
   - Test with nested directories
   - Test with symlinks
   - Test with file moves and renames
   - Test with large numbers of events
   - Test with paths containing special characters
