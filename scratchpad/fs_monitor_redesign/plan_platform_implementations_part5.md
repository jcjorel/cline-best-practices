# File System Monitor Redesign: Platform Implementations Part 5 - Fallback

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the fallback file system monitor using polling. This implementation is used when native file system monitoring APIs are not available or fail to work properly. The fallback implementation periodically checks file system state and detects changes by comparing current state with previously recorded state.

## Fallback Implementation Details

```python
# src/dbp/fs_monitor/fallback.py

import os
import threading
import logging
import time
from typing import Dict, Set, List, Optional, Callable, Any, Tuple
import hashlib

from .monitor_base import MonitorBase
from .event_types import EventType, FileSystemEvent
from .exceptions import WatchCreationError
from .watch_manager import WatchManager
from .event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class FileInfo:
    """
    [Class intent]
    Represents information about a file or directory for change detection.
    
    [Design principles]
    - Efficient state tracking
    - Support for all file types
    
    [Implementation details]
    - Stores file metadata
    - Includes file hash for content change detection
    
    Attributes:
        path: Absolute path
        exists: Whether the file exists
        is_dir: Whether it's a directory
        is_symlink: Whether it's a symlink
        mtime: Modification time
        size: File size
        hash: Hash of the file content (for regular files only)
        target: Symlink target (for symlinks only)
    """
    
    def __init__(self, path: str) -> None:
        """
        [Function intent]
        Initialize file information.
        
        [Design principles]
        - Collect all relevant file information
        
        [Implementation details]
        - Gathers file metadata
        - Calculates file hash for regular files
        
        Args:
            path: Absolute path
        """
        self.path = path
        self.exists = os.path.exists(path) or os.path.islink(path)
        self.is_dir = os.path.isdir(path) if self.exists else False
        self.is_symlink = os.path.islink(path) if self.exists else False
        
        if self.exists:
            try:
                stat = os.lstat(path)
                self.mtime = stat.st_mtime
                self.size = stat.st_size if not self.is_dir else 0
            except (FileNotFoundError, PermissionError):
                self.mtime = 0
                self.size = 0
        else:
            self.mtime = 0
            self.size = 0
        
        self.hash = None
        if self.exists and not self.is_dir and not self.is_symlink:
            try:
                with open(path, 'rb') as f:
                    self.hash = hashlib.md5(f.read(4096)).hexdigest()  # Only hash first 4KB for efficiency
            except (FileNotFoundError, PermissionError, IsADirectoryError):
                pass
        
        self.target = None
        if self.is_symlink:
            try:
                self.target = os.readlink(path)
            except (FileNotFoundError, PermissionError):
                pass
    
    def __eq__(self, other: 'FileInfo') -> bool:
        """
        [Function intent]
        Compare two FileInfo objects for equality.
        
        [Design principles]
        - Efficient comparison
        - Appropriate comparison based on file type
        
        [Implementation details]
        - Compares relevant attributes based on file type
        
        Args:
            other: Another FileInfo object
            
        Returns:
            True if the FileInfo objects are equal, False otherwise
        """
        if not isinstance(other, FileInfo):
            return False
            
        if self.exists != other.exists:
            return False
            
        if not self.exists:
            return True
            
        if self.is_dir != other.is_dir:
            return False
            
        if self.is_symlink != other.is_symlink:
            return False
            
        if self.is_symlink and self.target != other.target:
            return False
            
        if not self.is_dir and not self.is_symlink:
            # For regular files, compare size and hash
            if self.size != other.size:
                return False
                
            if self.hash != other.hash:
                return False
        
        return True
    
    def __ne__(self, other: 'FileInfo') -> bool:
        """
        [Function intent]
        Compare two FileInfo objects for inequality.
        
        [Design principles]
        - Consistent with __eq__
        
        [Implementation details]
        - Uses __eq__ and negates result
        
        Args:
            other: Another FileInfo object
            
        Returns:
            True if the FileInfo objects are not equal, False otherwise
        """
        return not (self == other)


class FallbackMonitor(MonitorBase):
    """
    [Class intent]
    Fallback file system monitor using polling.
    
    [Design principles]
    - Cross-platform compatibility
    - Efficient polling
    - Consistent event model
    
    [Implementation details]
    - Uses polling to detect file system changes
    - Translates detected changes to our event model
    - Manages polling threads
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the fallback monitor.
        
        [Design principles]
        - Clean initialization
        - Resource initialization
        
        [Implementation details]
        - Calls parent constructor
        - Initializes data structures for watch mapping
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        super().__init__(watch_manager, event_dispatcher)
        self._watches = {}  # path -> (snapshot, thread, stop_event)
        self._poll_interval = 1.0  # seconds
    
    def start(self) -> None:
        """
        [Function intent]
        Start the fallback monitor.
        
        [Design principles]
        - Clean startup sequence
        
        [Implementation details]
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("Fallback monitor already running")
                return
            
            self._running = True
            logger.debug("Started fallback monitor")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the fallback monitor.
        
        [Design principles]
        - Clean shutdown sequence
        - Resource cleanup
        
        [Implementation details]
        - Sets running flag to false
        - Stops all polling threads
        """
        with self._lock:
            if not self._running:
                logger.debug("Fallback monitor already stopped")
                return
            
            # Set running flag to false
            self._running = False
            
            # Stop all polling threads
            for path, (snapshot, thread, stop_event) in self._watches.items():
                try:
                    # Signal thread to stop
                    stop_event.set()
                    
                    # Wait for thread to terminate
                    if thread.is_alive():
                        thread.join(timeout=1.0)
                except Exception as e:
                    logger.warning(f"Error stopping polling thread for {path}: {e}")
            
            # Clear watches
            self._watches.clear()
            
            logger.debug("Stopped fallback monitor")
    
    def add_watch(self, path: str) -> Tuple[Dict[str, FileInfo], threading.Thread, threading.Event]:
        """
        [Function intent]
        Add a watch for a directory.
        
        [Design principles]
        - Platform-agnostic watch creation
        - Thorough initial snapshot
        
        [Implementation details]
        - Takes initial file system snapshot
        - Starts polling thread
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path to watch
            
        Returns:
            Tuple of (snapshot, thread, stop_event)
            
        Raises:
            WatchCreationError: If the watch cannot be created
        """
        with self._lock:
            if not self._running:
                logger.warning("Fallback monitor not running, watch will not be added")
                raise WatchCreationError("Monitor not running")
            
            if path in self._watches:
                return self._watches[path]
            
            try:
                # Ensure path is a directory
                if not os.path.isdir(path):
                    raise WatchCreationError(f"{path} is not a directory")
                
                # Create a stop event for this watch
                stop_event = threading.Event()
                
                # Take initial snapshot
                snapshot = self._take_snapshot(path)
                
                # Start polling thread
                thread = threading.Thread(
                    target=self._poll_directory,
                    args=(path, snapshot, stop_event),
                    daemon=True,
                    name=f"FSMonitor-Fallback-{path}"
                )
                thread.start()
                
                # Store the watch
                watch_data = (snapshot, thread, stop_event)
                self._watches[path] = watch_data
                
                logger.debug(f"Added watch for {path}")
                return watch_data
            except Exception as e:
                logger.error(f"Error adding watch for {path}: {e}")
                raise WatchCreationError(f"Failed to add watch for {path}: {e}")
    
    def remove_watch(self, path: str, watch_data: Tuple[Dict[str, FileInfo], threading.Thread, threading.Event]) -> None:
        """
        [Function intent]
        Remove a watch for a directory.
        
        [Design principles]
        - Clean resource cleanup
        
        [Implementation details]
        - Stops the polling thread
        - Updates mapping dictionaries
        
        Args:
            path: Absolute path that was being watched
            watch_data: Tuple of (snapshot, thread, stop_event)
        """
        with self._lock:
            if not self._running:
                logger.debug("Fallback monitor not running, watch will not be removed")
                return
            
            try:
                # Unpack the watch data
                snapshot, thread, stop_event = watch_data
                
                # Signal thread to stop
                stop_event.set()
                
                # Wait for thread to terminate
                if thread.is_alive():
                    thread.join(timeout=1.0)
                
                # Remove from mapping
                self._watches.pop(path, None)
                
                logger.debug(f"Removed watch for {path}")
            except Exception as e:
                logger.warning(f"Error removing watch for {path}: {e}")
    
    def _take_snapshot(self, path: str) -> Dict[str, FileInfo]:
        """
        [Function intent]
        Take a snapshot of the file system state.
        
        [Design principles]
        - Thorough file system traversal
        - Efficient file information collection
        
        [Implementation details]
        - Recursively walks the directory tree
        - Collects file information for all files
        
        Args:
            path: Directory path
            
        Returns:
            Dictionary mapping paths to FileInfo objects
        """
        snapshot = {}
        
        try:
            # Add the directory itself
            snapshot[path] = FileInfo(path)
            
            # Walk the directory tree
            for root, dirs, files in os.walk(path):
                # Add directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    snapshot[dir_path] = FileInfo(dir_path)
                
                # Add files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    snapshot[file_path] = FileInfo(file_path)
        except Exception as e:
            logger.error(f"Error taking snapshot of {path}: {e}")
        
        return snapshot
    
    def _poll_directory(self, path: str, snapshot: Dict[str, FileInfo], stop_event: threading.Event) -> None:
        """
        [Function intent]
        Poll a directory for changes.
        
        [Design principles]
        - Efficient change detection
        - Accurate event generation
        
        [Implementation details]
        - Periodically takes snapshots of the file system
        - Compares snapshots to detect changes
        - Dispatches events for detected changes
        
        Args:
            path: Directory path
            snapshot: Initial file system snapshot
            stop_event: Event to signal thread stop
        """
        try:
            while not stop_event.is_set() and self._running:
                # Wait for a bit
                if stop_event.wait(self._poll_interval):
                    # Stop event was set
                    break
                
                # Take a new snapshot
                new_snapshot = self._take_snapshot(path)
                
                # Detect changes
                self._detect_changes(snapshot, new_snapshot)
                
                # Update snapshot
                snapshot.clear()
                snapshot.update(new_snapshot)
        except Exception as e:
            logger.error(f"Error polling directory {path}: {e}")
    
    def _detect_changes(self, old_snapshot: Dict[str, FileInfo], new_snapshot: Dict[str, FileInfo]) -> None:
        """
        [Function intent]
        Detect changes between two snapshots.
        
        [Design principles]
        - Comprehensive change detection
        - Accurate event classification
        
        [Implementation details]
        - Compares old and new snapshots
        - Generates appropriate events for changes
        - Handles all file types (files, directories, symlinks)
        
        Args:
            old_snapshot: Previous file system snapshot
            new_snapshot: Current file system snapshot
        """
        # Find removed files/directories/symlinks
        for path, old_info in old_snapshot.items():
            if path not in new_snapshot:
                # File/directory/symlink was deleted
                if old_info.is_dir:
                    self.dispatch_event(EventType.DIRECTORY_DELETED, path)
                elif old_info.is_symlink:
                    self.dispatch_event(EventType.SYMLINK_DELETED, path)
                else:
                    self.dispatch_event(EventType.FILE_DELETED, path)
        
        # Find new or modified files/directories/symlinks
        for path, new_info in new_snapshot.items():
            if path not in old_snapshot:
                # File/directory/symlink was created
                if new_info.is_dir:
                    self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                elif new_info.is_symlink:
                    self.dispatch_event(EventType.SYMLINK_CREATED, path, None, new_info.target)
                else:
                    self.dispatch_event(EventType.FILE_CREATED, path)
            else:
                # File/directory/symlink exists in both snapshots
                old_info = old_snapshot[path]
                
                if old_info != new_info:
                    if old_info.is_dir != new_info.is_dir or old_info.is_symlink != new_info.is_symlink:
                        # Type changed, report as delete + create
                        if old_info.is_dir:
                            self.dispatch_event(EventType.DIRECTORY_DELETED, path)
                        elif old_info.is_symlink:
                            self.dispatch_event(EventType.SYMLINK_DELETED, path)
                        else:
                            self.dispatch_event(EventType.FILE_DELETED, path)
                        
                        if new_info.is_dir:
                            self.dispatch_event(EventType.DIRECTORY_CREATED, path)
                        elif new_info.is_symlink:
                            self.dispatch_event(EventType.SYMLINK_CREATED, path, None, new_info.target)
                        else:
                            self.dispatch_event(EventType.FILE_CREATED, path)
                    elif new_info.is_symlink and old_info.target != new_info.target:
                        # Symlink target changed
                        self.dispatch_event(EventType.SYMLINK_TARGET_CHANGED, path, old_info.target, new_info.target)
                    elif not new_info.is_dir and not new_info.is_symlink:
                        # Regular file was modified
                        self.dispatch_event(EventType.FILE_MODIFIED, path)
    
    def configure(self, poll_interval: float) -> None:
        """
        [Function intent]
        Configure the fallback monitor.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates polling interval
        
        Args:
            poll_interval: Polling interval in seconds
        """
        with self._lock:
            self._poll_interval = max(0.1, poll_interval)  # Ensure minimum interval of 100ms
```

## Key Implementation Features

### Snapshot-Based Change Detection

The fallback implementation uses a snapshot-based approach to detect file system changes:

1. Takes an initial snapshot of the file system structure
2. Periodically takes new snapshots
3. Compares snapshots to detect changes

### File Information Collection

The implementation collects detailed information about files, directories, and symlinks:

1. For all files: existence, type, modification time
2. For regular files: size, hash (of the first 4KB)
3. For symlinks: target path

### Comprehensive Change Detection

The implementation detects various types of changes:

1. File/directory/symlink creation
2. File/directory/symlink deletion
3. File modification
4. Symlink target changes
5. Type changes (e.g., file to directory)

### Efficient Resource Usage

The implementation is designed to be efficient:

1. Uses a configurable polling interval
2. Only calculates hashes for regular files
3. Only calculates hashes for the first 4KB of files (to detect most changes while remaining efficient)
4. Uses separate threads for each watched directory

## Performance Considerations

While the fallback implementation is designed to be as efficient as possible, it has some inherent limitations:

1. **CPU Usage**: Polling requires periodic CPU usage, which scales with the number of watched directories and files.
2. **Memory Usage**: The implementation needs to maintain snapshots of watched directories, which can use significant memory for large directory trees.
3. **Event Latency**: Changes are only detected during the next polling cycle, leading to higher event latency compared to native APIs.
4. **Accuracy**: Some rapid changes (e.g., create and delete between polls) might be missed entirely.

## Configuration Parameters

The fallback implementation should respect the following configuration parameters:

1. `fs_monitor.fallback.poll_interval`: The interval between polls in seconds (default: 1.0)
2. `fs_monitor.fallback.hash_size`: The number of bytes to hash for regular files (default: 4096)

## Testing Strategy

The fallback implementation should be tested with the following strategies:

1. **Unit Tests**:
   - Test snapshot comparison logic
   - Test file information collection
   - Test change detection

2. **Integration Tests**:
   - Test with the watch manager and event dispatcher
   - Test with real file system changes

3. **Edge Cases**:
   - Test with large directories
   - Test with rapid changes
   - Test with files of various types
   - Test with special characters in file names
   - Test with various poll intervals

4. **Performance Testing**:
   - Test CPU usage with various directory sizes
   - Test memory usage with various directory sizes
   - Test event latency with various poll intervals

## Platform Compatibility

The fallback implementation relies only on Python's standard library and should work on all platforms that support Python:

1. Windows
2. Linux
3. macOS
4. BSD variants
5. Any other platform with Python support

## Component Integration

With the completion of the fallback monitor implementation, all platform-specific implementations have been covered:

1. Linux (inotify)
2. macOS (FSEvents)
3. Windows (ReadDirectoryChangesW)
4. Fallback (polling)

The factory implementation will select the appropriate monitor based on the platform and fall back to the polling implementation if needed.

## Next Steps

1. Update plan_progress.md to mark platform implementations as completed
2. Implement component integration plan
3. Begin implementation phase
