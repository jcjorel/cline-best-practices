# File System Monitoring Implementation Plan

## Overview

This plan details the implementation of the file system monitoring system for the Documentation-Based Programming MCP Server. The file system monitoring component will detect changes to files in the project directory and queue them for processing by the metadata extraction system.

## Documentation Context

The file system monitoring implementation is informed by these key documentation files:
- [doc/DESIGN.md](../../doc/DESIGN.md) - Describes the file monitoring approach using system-specific APIs
- [doc/design/BACKGROUND_TASK_SCHEDULER.md](../../doc/design/BACKGROUND_TASK_SCHEDULER.md) - Details the background task scheduler
- [doc/CONFIGURATION.md](../../doc/CONFIGURATION.md) - Configuration parameters for file system monitoring
- [doc/SECURITY.md](../../doc/SECURITY.md) - Security considerations for file access

## Implementation Requirements

### Functional Requirements

1. Detection of file creation, modification, deletion, and renaming events
2. Platform-specific file notification mechanisms:
   - `inotify()` on Linux/WSL environments
   - `FSEvents` on macOS
   - `ReadDirectoryChangesW` on Windows
3. Filtering of events based on .gitignore patterns and system configurations
4. Buffering and debouncing of change events
5. Thread-safe change notification queue
6. Recursive directory monitoring
7. Support for handling large numbers of file changes efficiently
8. Automatic exclusion of scratchpad/ directory and files with "deprecated" in path

### Non-Functional Requirements

1. Low resource usage (<5% CPU, <50MB RAM)
2. Fast event detection (within seconds)
3. Efficient handling of large codebases
4. Resilience to rapid file changes
5. Graceful degradation under high load
6. Proper error handling for filesystem access issues
7. Support for different operating systems
8. Configurable monitoring behavior

## Architecture

The file system monitoring system consists of these main components:

1. **FileSystemMonitorFactory**: Creates platform-specific monitor implementations
2. **FileSystemMonitor**: Abstract base class for file monitoring
3. **LinuxFileSystemMonitor**: Linux-specific implementation using inotify
4. **MacOSFileSystemMonitor**: macOS-specific implementation using FSEvents
5. **WindowsFileSystemMonitor**: Windows implementation using ReadDirectoryChangesW
6. **FallbackFileSystemMonitor**: Polling-based fallback implementation
7. **ChangeDetectionQueue**: Thread-safe queue for file change events
8. **ChangeEvent**: Data structure for file change events
9. **GitIgnoreFilter**: Filtering system based on .gitignore patterns

## Implementation Details

### File System Monitor Interface

The system will define a common interface for all platform-specific implementations:

```python
# fs_monitor/base.py
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Set, Callable, Optional, Dict, Any
from pathlib import Path
import logging
import threading
import time

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    """Types of file system changes."""
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    RENAMED = auto()
    UNKNOWN = auto()

class ChangeEvent:
    """Represents a file system change event."""
    
    def __init__(self, path: str, change_type: ChangeType, old_path: Optional[str] = None):
        """Initialize a change event.
        
        Args:
            path: The path of the changed file
            change_type: The type of change
            old_path: The old path for renamed files
        """
        self.path = path
        self.change_type = change_type
        self.old_path = old_path
        self.timestamp = time.time()
    
    def __eq__(self, other):
        """Check if two events are equal."""
        if not isinstance(other, ChangeEvent):
            return False
        return (self.path == other.path and 
                self.change_type == other.change_type and 
                self.old_path == other.old_path)
    
    def __hash__(self):
        """Return a hash of the event for deduplication."""
        return hash((self.path, self.change_type, self.old_path))
    
    def __repr__(self):
        """Return a string representation of the event."""
        if self.change_type == ChangeType.RENAMED and self.old_path:
            return f"ChangeEvent({self.change_type.name}, {self.old_path} -> {self.path})"
        return f"ChangeEvent({self.change_type.name}, {self.path})"

class FileSystemMonitor(ABC):
    """Abstract base class for file system monitors."""
    
    def __init__(self, config, change_queue):
        """Initialize the file system monitor.
        
        Args:
            config: Configuration manager
            change_queue: Queue to add change events to
        """
        self.config = config
        self.change_queue = change_queue
        self.watched_directories = set()
        self.running = False
        self.monitor_thread = None
        self.lock = threading.RLock()
        
    @abstractmethod
    def start(self):
        """Start monitoring file changes."""
        self.running = True
    
    @abstractmethod
    def stop(self):
        """Stop monitoring file changes."""
        self.running = False
    
    @abstractmethod
    def add_directory(self, directory: str):
        """Add a directory to monitor.
        
        Args:
            directory: Path to directory to monitor
        """
        with self.lock:
            self.watched_directories.add(directory)
    
    @abstractmethod
    def remove_directory(self, directory: str):
        """Remove a directory from monitoring.
        
        Args:
            directory: Path to directory to stop monitoring
        """
        with self.lock:
            if directory in self.watched_directories:
                self.watched_directories.remove(directory)
    
    def get_watched_directories(self) -> List[str]:
        """Return a list of watched directories."""
        with self.lock:
            return list(self.watched_directories)
```

### Platform-Specific Implementations

#### Linux Implementation (inotify)

```python
# fs_monitor/linux.py
import os
import select
import struct
import threading
import logging
from typing import Dict, Set, Optional

# Try to import inotify
try:
    import inotify.adapters
    import inotify.constants
    HAS_INOTIFY = True
except ImportError:
    HAS_INOTIFY = False

from .base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class LinuxFileSystemMonitor(FileSystemMonitor):
    """Linux file system monitor using inotify."""
    
    def __init__(self, config, change_queue):
        """Initialize the Linux file system monitor."""
        super().__init__(config, change_queue)
        
        if not HAS_INOTIFY:
            raise ImportError("inotify package is required for Linux monitoring")
        
        self._inotify = None
        self._watch_descriptors = {}  # Maps paths to watch descriptors
        self._path_by_descriptor = {}  # Maps watch descriptors to paths
    
    def start(self):
        """Start monitoring file changes."""
        super().start()
        
        # Initialize inotify
        self._inotify = inotify.adapters.Inotify()
        
        # Add existing directories
        for directory in self.watched_directories:
            self._add_watch(directory)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="LinuxFSMonitor"
        )
        self.monitor_thread.start()
        
        logger.info("Linux file system monitor started")
    
    def stop(self):
        """Stop monitoring file changes."""
        super().stop()
        
        # Wait for monitoring thread to exit
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Clean up inotify
        if self._inotify:
            for path in list(self._watch_descriptors.keys()):
                self._remove_watch(path)
            self._inotify = None
        
        logger.info("Linux file system monitor stopped")
    
    def add_directory(self, directory: str):
        """Add a directory to monitor."""
        super().add_directory(directory)
        
        if self._inotify and os.path.isdir(directory):
            self._add_watch(directory)
            
            # Add subdirectories if recursive monitoring is enabled
            if self.config.get('monitor.recursive', True):
                for root, dirs, _ in os.walk(directory):
                    for subdir in dirs:
                        subdir_path = os.path.join(root, subdir)
                        if os.path.isdir(subdir_path):
                            self._add_watch(subdir_path)
    
    def remove_directory(self, directory: str):
        """Remove a directory from monitoring."""
        super().remove_directory(directory)
        
        if self._inotify:
            self._remove_watch(directory)
            
            # Remove subdirectories if they were being watched
            for path in list(self._watch_descriptors.keys()):
                if path.startswith(directory + os.sep):
                    self._remove_watch(path)
    
    def _add_watch(self, path: str):
        """Add a watch for the specified path."""
        if not os.path.isdir(path):
            return
        
        if path in self._watch_descriptors:
            return
        
        try:
            # Watch for all relevant events
            mask = (
                inotify.constants.IN_CREATE |
                inotify.constants.IN_DELETE |
                inotify.constants.IN_MODIFY |
                inotify.constants.IN_MOVED_FROM |
                inotify.constants.IN_MOVED_TO
            )
            self._inotify.add_watch(path, mask)
            
            # Store watch descriptor
            wd = self._inotify._inotify_fd
            self._watch_descriptors[path] = wd
            self._path_by_descriptor[wd] = path
            
            logger.debug(f"Added watch for: {path}")
        except Exception as e:
            logger.error(f"Failed to add watch for {path}: {e}")
    
    def _remove_watch(self, path: str):
        """Remove a watch for the specified path."""
        if path not in self._watch_descriptors:
            return
        
        try:
            wd = self._watch_descriptors[path]
            self._inotify.remove_watch(path)
            
            # Clean up mappings
            del self._watch_descriptors[path]
            if wd in self._path_by_descriptor:
                del self._path_by_descriptor[wd]
                
            logger.debug(f"Removed watch for: {path}")
        except Exception as e:
            logger.error(f"Failed to remove watch for {path}: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Process inotify events
                for event in self._inotify.event_gen(yield_nones=False, timeout_s=1):
                    if not self.running:
                        break
                    
                    # Parse event
                    (_, type_names, watch_path, filename) = event
                    
                    # Handle different event types
                    if not filename:
                        continue
                    
                    # Create file path
                    path = os.path.join(watch_path, filename)
                    
                    # Determine change type
                    change_type = ChangeType.UNKNOWN
                    
                    if 'IN_CREATE' in type_names:
                        change_type = ChangeType.CREATED
                        # Add watch if it's a directory and recursive monitoring is enabled
                        if os.path.isdir(path) and self.config.get('monitor.recursive', True):
                            self._add_watch(path)
                    elif 'IN_DELETE' in type_names:
                        change_type = ChangeType.DELETED
                        # Remove watch if it's a directory
                        if path in self._watch_descriptors:
                            self._remove_watch(path)
                    elif 'IN_MODIFY' in type_names:
                        change_type = ChangeType.MODIFIED
                    elif 'IN_MOVED_FROM' in type_names:
                        # Store moved_from info for potential RENAMED event
                        self._moved_from_path = path
                        continue
                    elif 'IN_MOVED_TO' in type_names:
                        # Check if we have a moved_from path for a rename event
                        if hasattr(self, '_moved_from_path'):
                            change_type = ChangeType.RENAMED
                            old_path = self._moved_from_path
                            delattr(self, '_moved_from_path')
                            
                            # Add event to queue
                            event = ChangeEvent(path, change_type, old_path)
                            self.change_queue.add_event(event)
                            
                            # Add watch if it's a directory and recursive monitoring is enabled
                            if os.path.isdir(path) and self.config.get('monitor.recursive', True):
                                self._add_watch(path)
                            continue
                        else:
                            # If no moved_from, treat as created
                            change_type = ChangeType.CREATED
                    
                    # Add event to queue
                    if change_type != ChangeType.UNKNOWN:
                        event = ChangeEvent(path, change_type)
                        self.change_queue.add_event(event)
                    
            except Exception as e:
                logger.error(f"Error in Linux file monitor: {e}")
                # Brief pause to avoid tight loop in case of persistent error
                time.sleep(0.1)
```

#### macOS Implementation (FSEvents)

```python
# fs_monitor/macos.py
import os
import threading
import logging
import time
from typing import Dict, Set, Optional

# Try to import pyfsevents
try:
    import fsevents
    HAS_FSEVENTS = True
except ImportError:
    HAS_FSEVENTS = False

from .base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class MacOSFileSystemMonitor(FileSystemMonitor):
    """macOS file system monitor using FSEvents."""
    
    def __init__(self, config, change_queue):
        """Initialize the macOS file system monitor."""
        super().__init__(config, change_queue)
        
        if not HAS_FSEVENTS:
            raise ImportError("fsevents package is required for macOS monitoring")
        
        self._observer = None
        self._watches = {}  # Maps paths to watch objects
        self._last_event_time = {}  # Maps paths to last event time
        
        # File state cache to detect renames and modifications
        self._file_state = {}
    
    def start(self):
        """Start monitoring file changes."""
        super().start()
        
        # Initialize observer
        self._observer = fsevents.Observer()
        self._observer.start()
        
        # Add existing directories
        for directory in self.watched_directories:
            self._add_watch(directory)
        
        logger.info("macOS file system monitor started")
    
    def stop(self):
        """Stop monitoring file changes."""
        super().stop()
        
        # Clean up watches
        for path in list(self._watches.keys()):
            self._remove_watch(path)
        
        # Stop observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        
        logger.info("macOS file system monitor stopped")
    
    def add_directory(self, directory: str):
        """Add a directory to monitor."""
        super().add_directory(directory)
        
        if self._observer and os.path.isdir(directory):
            self._add_watch(directory)
    
    def remove_directory(self, directory: str):
        """Remove a directory from monitoring."""
        super().remove_directory(directory)
        
        if self._observer:
            self._remove_watch(directory)
    
    def _add_watch(self, path: str):
        """Add a watch for the specified path."""
        if not os.path.isdir(path):
            return
        
        if path in self._watches:
            return
        
        try:
            # Create stream
            stream = fsevents.Stream(
                callback=self._handle_event,
                paths=[path],
                file_events=True
            )
            
            # Start stream
            self._observer.schedule(stream)
            stream.start()
            
            # Store watch
            self._watches[path] = stream
            
            logger.debug(f"Added watch for: {path}")
        except Exception as e:
            logger.error(f"Failed to add watch for {path}: {e}")
    
    def _remove_watch(self, path: str):
        """Remove a watch for the specified path."""
        if path not in self._watches:
            return
        
        try:
            stream = self._watches[path]
            stream.stop()
            self._observer.unschedule(stream)
            
            # Clean up mappings
            del self._watches[path]
            
            logger.debug(f"Removed watch for: {path}")
        except Exception as e:
            logger.error(f"Failed to remove watch for {path}: {e}")
    
    def _handle_event(self, event):
        """Handle a file system event."""
        # Get event path
        path = event.name
        
        # Check if path is valid
        if not path or not os.path.exists(os.path.dirname(path)):
            return
        
        # Determine change type
        change_type = ChangeType.UNKNOWN
        
        # FSEvents flags
        is_created = bool(event.mask & fsevents.IN_CREATE)
        is_deleted = bool(event.mask & fsevents.IN_DELETE)
        is_modified = bool(event.mask & fsevents.IN_MODIFY)
        is_renamed = bool(event.mask & fsevents.IN_MOVED_FROM or event.mask & fsevents.IN_MOVED_TO)
        
        # Handle different event types
        if is_created:
            change_type = ChangeType.CREATED
            
            # Add watch if it's a directory and recursive monitoring is enabled
            if os.path.isdir(path) and self.config.get('monitor.recursive', True):
                self._add_watch(path)
                
        elif is_deleted:
            change_type = ChangeType.DELETED
            
            # Remove watch if it's a directory
            if path in self._watches:
                self._remove_watch(path)
                
        elif is_renamed:
            # FSEvents doesn't provide old path information directly
            # We would need to implement a more complex tracking system
            # For now, treat it as a deletion + creation
            change_type = ChangeType.MODIFIED
            
        elif is_modified:
            change_type = ChangeType.MODIFIED
        
        # Add event to queue
        if change_type != ChangeType.UNKNOWN:
            event = ChangeEvent(path, change_type)
            self.change_queue.add_event(event)
```

#### Windows Implementation (ReadDirectoryChangesW)

```python
# fs_monitor/windows.py
import os
import threading
import logging
import time
from typing import Dict, Set, Optional
import ctypes
from ctypes import wintypes

# Try to import win32 modules
try:
    import win32file
    import win32con
    import pywintypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from .base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class WindowsFileSystemMonitor(FileSystemMonitor):
    """Windows file system monitor using ReadDirectoryChangesW."""
    
    def __init__(self, config, change_queue):
        """Initialize the Windows file system monitor."""
        super().__init__(config, change_queue)
        
        if not HAS_WIN32:
            raise ImportError("pywin32 is required for Windows monitoring")
        
        self._watches = {}  # Maps paths to watch handles
        self._buffers = {}  # Maps paths to read buffers
        self._overlapped = {}  # Maps paths to overlapped structures
        self._threads = {}  # Maps paths to monitoring threads
    
    def start(self):
        """Start monitoring file changes."""
        super().start()
        
        # Add existing directories
        for directory in self.watched_directories:
            self._add_watch(directory)
        
        logger.info("Windows file system monitor started")
    
    def stop(self):
        """Stop monitoring file changes."""
        super().stop()
        
        # Clean up watches
        for path in list(self._watches.keys()):
            self._remove_watch(path)
        
        # Wait for threads to exit
        for thread in self._threads.values():
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        logger.info("Windows file system monitor stopped")
    
    def add_directory(self, directory: str):
        """Add a directory to monitor."""
        super().add_directory(directory)
        
        if os.path.isdir(directory):
            self._add_watch(directory)
    
    def remove_directory(self, directory: str):
        """Remove a directory from monitoring."""
        super().remove_directory(directory)
        self._remove_watch(directory)
    
    def _add_watch(self, path: str):
        """Add a watch for the specified path."""
        if not os.path.isdir(path):
            return
        
        if path in self._watches:
            return
        
        try:
            # Create directory handle
            handle = win32file.CreateFile(
                path,
                win32con.FILE_LIST_DIRECTORY,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED,
                None
            )
            
            # Create overlapped structure
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32file.CreateEvent(None, False, False, None)
            
            # Create buffer for reading changes
            buffer = win32file.AllocateReadBuffer(8192)
            
            # Store watch data
            self._watches[path] = handle
            self._overlapped[path] = overlapped
            self._buffers[path] = buffer
            
            # Start monitoring thread
            thread = threading.Thread(
                target=self._monitor_directory,
                args=(path,),
                daemon=True,
                name=f"WinFSMonitor-{os.path.basename(path)}"
            )
            self._threads[path] = thread
            thread.start()
            
            logger.debug(f"Added watch for: {path}")
            
            # Add subdirectories if recursive monitoring is enabled
            if self.config.get('monitor.recursive', True):
                for root, dirs, _ in os.walk(path):
                    for subdir in dirs:
                        subdir_path = os.path.join(root, subdir)
                        if os.path.isdir(subdir_path) and subdir_path not in self._watches:
                            self._add_watch(subdir_path)
        
        except Exception as e:
            logger.error(f"Failed to add watch for {path}: {e}")
    
    def _remove_watch(self, path: str):
        """Remove a watch for the specified path."""
        if path not in self._watches:
            return
        
        try:
            # Cancel I/O operations
            handle = self._watches[path]
            overlapped = self._overlapped[path]
            
            # Close handle
            handle.close()
            
            # Clean up mappings
            del self._watches[path]
            del self._buffers[path]
            del self._overlapped[path]
            
            # Thread will exit when running becomes False
            
            logger.debug(f"Removed watch for: {path}")
        except Exception as e:
            logger.error(f"Failed to remove watch for {path}: {e}")
    
    def _monitor_directory(self, path: str):
        """Monitor a directory for changes."""
        recursive = self.config.get('monitor.recursive', True)
        
        while self.running and path in self._watches:
            try:
                handle = self._watches[path]
                buffer = self._buffers[path]
                overlapped = self._overlapped[path]
                
                # Begin async read
                win32file.ReadDirectoryChangesW(
                    handle,
                    buffer,
                    recursive,  # Watch subdirectories
                    win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                    win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                    win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                    win32con.FILE_NOTIFY_CHANGE_SIZE |
                    win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                    win32con.FILE_NOTIFY_CHANGE_CREATION,
                    overlapped
                )
                
                # Wait for changes
                result = win32file.GetOverlappedResult(handle, overlapped, True)
                
                # Process changes
                if result > 0:
                    # Parse buffer
                    changes = win32file.FILE_NOTIFY_INFORMATION(buffer, result)
                    
                    # Process each change
                    for action, file_name in changes:
                        # Convert file name to full path
                        file_path = os.path.join(path, file_name)
                        
                        # Determine change type
                        change_type = ChangeType.UNKNOWN
                        
                        if action == win32con.FILE_ACTION_ADDED:
                            change_type = ChangeType.CREATED
                            # Add watch for new directory
                            if os.path.isdir(file_path) and recursive:
                                self._add_watch(file_path)
                        elif action == win32con.FILE_ACTION_REMOVED:
                            change_type = ChangeType.DELETED
                            # Remove watch for deleted directory
                            if file_path in self._watches:
                                self._remove_watch(file_path)
                        elif action == win32con.FILE_ACTION_MODIFIED:
                            change_type = ChangeType.MODIFIED
                        elif action == win32con.FILE_ACTION_RENAMED_OLD_NAME:
                            # Store old name for potential rename event
                            self._old_name = file_path
                            continue
                        elif action == win32con.FILE_ACTION_RENAMED_NEW_NAME:
                            # Check if we have an old name for a rename event
                            if hasattr(self, '_old_name'):
                                change_type = ChangeType.RENAMED
                                old_path = self._old_name
                                delattr(self, '_old_name')
                                
                                # Add event to queue
                                event = ChangeEvent(file_path, change_type, old_path)
                                self.change_queue.add_event(event)
                                
                                # Add watch for renamed directory
                                if os.path.isdir(file_path) and recursive:
                                    self._add_watch(file_path)
                                continue
                            else:
                                # If no old name, treat as created
                                change_type = ChangeType.CREATED
                        
                        # Add event to queue
                        if change_type != ChangeType.UNKNOWN:
                            event = ChangeEvent(file_path, change_type)
                            self.change_queue.add_event(event)
            
            except Exception as e:
                if self.running and path in self._watches:
                    logger.error(f"Error monitoring {path}: {e}")
                    # Brief pause to avoid tight loop in case of persistent error
                    time.sleep(0.1)
                else:
                    # Monitor has been stopped, exit loop
                    break
```

### Fallback Polling Implementation

```python
# fs_monitor/fallback.py
import os
import threading
import logging
import time
from typing import Dict, Any, Set

from .base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class FallbackFileSystemMonitor(FileSystemMonitor):
    """Fallback file system monitor using directory polling."""
    
    def __init__(self, config, change_queue):
        """Initialize the fallback file system monitor."""
        super().__init__(config, change_queue)
        self._file_states = {}  # Maps paths to {size, mtime, exists}
        self._polling_interval = config.get('monitor.polling_interval', 2.0)
    
    def start(self):
        """Start monitoring file changes."""
        super().start()
        
        # Initialize file states for watched directories
        for directory in self.watched_directories:
            self._initialize_file_states(directory)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="FallbackFSMonitor"
        )
        self.monitor_thread.start()
        
        logger.info("Fallback file system monitor started")
    
    def stop(self):
        """Stop monitoring file changes."""
        super().stop()
        
        # Wait for monitoring thread to exit
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Clear file states
        self._file_states = {}
        
        logger.info("Fallback file system monitor stopped")
    
    def add_directory(self, directory: str):
        """Add a directory to monitor."""
        super().add_directory(directory)
        
        if os.path.isdir(directory):
            self._initialize_file_states(directory)
    
    def remove_directory(self, directory: str):
        """Remove a directory from monitoring."""
        super().remove_directory(directory)
        
        # Remove file states for this directory and its subdirectories
        paths_to_remove = [path for path in self._file_states if path.startswith(directory + os.sep)]
        for path in paths_to_remove:
            del self._file_states[path]
    
    def _initialize_file_states(self, directory: str):
        """Initialize file states for the specified directory."""
        if not os.path.isdir(directory):
            return
        
        # Add directory itself
        self._file_states[directory] = self._get_file_state(directory)
        
        # Add files in directory
        try:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                self._file_states[path] = self._get_file_state(path)
                
                # Recursively add subdirectories if enabled
                if os.path.isdir(path) and self.config.get('monitor.recursive', True):
                    self._initialize_file_states(path)
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Failed to initialize file states for {directory}: {e}")
    
    def _polling_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                # Sleep first to avoid immediate polling at startup
                time.sleep(self._polling_interval)
                
                # Check each watched directory
                for directory in list(self.watched_directories):
                    self._check_directory(directory)
                    
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
    
    def _check_directory(self, directory: str):
        """Check a directory for changes."""
        if not os.path.isdir(directory):
            return
        
        # Get current files in directory
        try:
            current_files = set(os.path.join(directory, item) for item in os.listdir(directory))
            
            # Check for deleted files
            for path in list(self._file_states.keys()):
                if os.path.dirname(path) == directory and path not in current_files and path != directory:
                    # File has been deleted
                    event = ChangeEvent(path, ChangeType.DELETED)
                    self.change_queue.add_event(event)
                    del self._file_states[path]
            
            # Check for new or modified files
            for path in current_files:
                current_state = self._get_file_state(path)
                
                if path not in self._file_states:
                    # New file
                    self._file_states[path] = current_state
                    event = ChangeEvent(path, ChangeType.CREATED)
                    self.change_queue.add_event(event)
                    
                    # Add watch for new directory
                    if os.path.isdir(path) and self.config.get('monitor.recursive', True):
                        self._check_directory(path)
                else:
                    # Check if file has been modified
                    old_state = self._file_states[path]
                    if (current_state['size'] != old_state['size'] or
                            current_state['mtime'] != old_state['mtime']):
                        self._file_states[path] = current_state
                        event = ChangeEvent(path, ChangeType.MODIFIED)
                        self.change_queue.add_event(event)
            
            # Recursively check subdirectories if enabled
            if self.config.get('monitor.recursive', True):
                for path in current_files:
                    if os.path.isdir(path) and path not in self.watched_directories:
                        self._check_directory(path)
                        
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Failed to check directory {directory}: {e}")
    
    def _get_file_state(self, path: str) -> Dict[str, Any]:
        """Get the current state of a file."""
        try:
            stat = os.stat(path)
            return {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True,
                'is_dir': os.path.isdir(path)
            }
        except (FileNotFoundError, PermissionError):
            return {
                'size': 0,
                'mtime': 0,
                'exists': False,
                'is_dir': False
            }
```

### Change Detection Queue

```python
# fs_monitor/queue.py
import threading
import time
import logging
import heapq
from typing import List, Set, Dict, Any, Optional
import copy

from .base import ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class ChangeDetectionQueue:
    """Thread-safe queue for file change events with debouncing."""
    
    def __init__(self, config):
        """Initialize the change detection queue.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self._queue = []  # Priority queue ordered by timestamp
        self._events = {}  # Maps path to event for deduplication
        self._lock = threading.RLock()
        self._event_available = threading.Event()
        self._filter = None  # Optional GitIgnoreFilter
    
    def add_event(self, event: ChangeEvent) -> None:
        """Add an event to the queue.
        
        Args:
            event: The change event to add
        """
        with self._lock:
            # Check if path should be ignored
            if self._filter and self._filter.should_ignore(event.path):
                logger.debug(f"Ignoring event for filtered path: {event.path}")
                return
            
            # Check if we have an existing event for this path
            if event.path in self._events:
                existing_event = self._events[event.path]
                
                # Replace existing event if this is more recent
                if existing_event.timestamp < event.timestamp:
                    # Remove old event from priority queue
                    self._queue = [e for e in self._queue if e[1].path != event.path]
                    heapq.heapify(self._queue)
                    
                    # Coalesce events if possible
                    if existing_event.change_type == ChangeType.CREATED and event.change_type == ChangeType.DELETED:
                        # Created then deleted, remove both
                        del self._events[event.path]
                        return
                    
                    if existing_event.change_type == ChangeType.MODIFIED and event.change_type == ChangeType.MODIFIED:
                        # Multiple modifications, keep the latest
                        pass
                    
                    # Store new event
                    self._events[event.path] = event
                    
                    # Calculate delay based on configuration
                    delay_seconds = self.config.get('scheduler.delay_seconds', 10)
                    max_delay_seconds = self.config.get('scheduler.max_delay_seconds', 120)
                    
                    # For frequently changing files, increase delay to avoid excessive processing
                    if existing_event.timestamp > time.time() - delay_seconds:
                        # File changed twice in short period, increase delay
                        delay_seconds = min(delay_seconds * 2, max_delay_seconds)
                    
                    # Calculate ready time
                    ready_time = event.timestamp + delay_seconds
                    
                    # Add to priority queue
                    heapq.heappush(self._queue, (ready_time, event))
            else:
                # New event
                self._events[event.path] = event
                
                # Calculate delay based on configuration
                delay_seconds = self.config.get('scheduler.delay_seconds', 10)
                
                # Calculate ready time
                ready_time = event.timestamp + delay_seconds
                
                # Add to priority queue
                heapq.heappush(self._queue, (ready_time, event))
            
            # Signal that an event is available
            self._event_available.set()
    
    def get_next_event(self, block: bool = True, timeout: Optional[float] = None) -> Optional[ChangeEvent]:
        """Get the next event from the queue.
        
        Args:
            block: Whether to block until an event is available
            timeout: Maximum time to block in seconds
        
        Returns:
            The next ready event, or None if no events are ready or the queue is empty
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                # Check if queue is empty
                if not self._queue:
                    if not block:
                        return None
                    self._event_available.clear()
                    self._lock.release()
                    try:
                        # Wait for event
                        if not self._event_available.wait(timeout):
                            # Timeout
                            return None
                    finally:
                        self._lock.acquire()
                    continue
                
                # Peek at first event
                ready_time, event = self._queue[0]
                now = time.time()
                
                if ready_time <= now:
                    # Event is ready, remove it
                    heapq.heappop(self._queue)
                    
                    # Only remove from events dict if this is the most recent event for this path
                    if self._events.get(event.path) is event:
                        del self._events[event.path]
                    
                    return event
                
                # No events ready yet
                if not block:
                    return None
                
                # Calculate remaining timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        # Timeout
                        return None
                    wait_time = min(ready_time - now, remaining)
                else:
                    wait_time = ready_time - now
                
                # Wait until event is ready or new event arrives
                self._event_available.clear()
                self._lock.release()
                try:
                    self._event_available.wait(wait_time)
                finally:
                    self._lock.acquire()
    
    def get_pending_count(self) -> int:
        """Get the number of pending events."""
        with self._lock:
            return len(self._queue)
    
    def clear(self) -> None:
        """Clear all pending events."""
        with self._lock:
            self._queue = []
            self._events = {}
            self._event_available.clear()
    
    def set_filter(self, filter_obj) -> None:
        """Set a filter for events.
        
        Args:
            filter_obj: GitIgnoreFilter instance
        """
        with self._lock:
            self._filter = filter_obj
```

### GitIgnore Filter

```python
# fs_monitor/filter.py
import os
import re
import logging
from typing import List, Set, Dict, Any, Optional
import fnmatch

logger = logging.getLogger(__name__)

class GitIgnoreFilter:
    """Filter for file system events based on .gitignore patterns."""
    
    def __init__(self, config):
        """Initialize the filter.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self._patterns = []  # List of (pattern, is_negative) tuples
        self._cached_results = {}  # Maps paths to filter results
        
        # Add mandatory patterns
        self._add_mandatory_patterns()
        
        # Add patterns from configuration
        self._add_config_patterns()
    
    def _add_mandatory_patterns(self):
        """Add mandatory patterns that are always ignored."""
        # Scratchpad directory
        self._patterns.append(('**/scratchpad/**', False))
        
        # Files or directories with "deprecated" in the path
        self._patterns.append(('**deprecated**', False))
    
    def _add_config_patterns(self):
        """Add patterns from configuration."""
        patterns = self.config.get('monitor.ignore_patterns', [])
        for pattern in patterns:
            self._patterns.append((pattern, False))
    
    def add_gitignore_file(self, path: str) -> bool:
        """Add patterns from a .gitignore file.
        
        Args:
            path: Path to .gitignore file
            
        Returns:
            True if file was loaded successfully, False otherwise
        """
        try:
            with open(path, 'r') as f:
                directory = os.path.dirname(path)
                
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle negative patterns
                    is_negative = line.startswith('!')
                    if is_negative:
                        line = line[1:].strip()
                    
                    # Convert to relative pattern
                    rel_pattern = os.path.join(directory, line).replace(os.sep, '/')
                    
                    # Add pattern
                    self._patterns.append((rel_pattern, is_negative))
                    
                # Clear cache after adding patterns
                self._cached_results.clear()
                
                return True
        except Exception as e:
            logger.warning(f"Failed to load .gitignore file {path}: {e}")
            return False
    
    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored.
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be ignored, False otherwise
        """
        # Check cache first
        if path in self._cached_results:
            return self._cached_results[path]
        
        # Convert to forward slashes for pattern matching
        path = path.replace(os.sep, '/')
        
        # Default is not ignored
        result = False
        
        # Check patterns in order
        for pattern, is_negative in self._patterns:
            if self._matches_pattern(path, pattern):
                # Pattern matches, apply ignore or include
                result = not is_negative
        
        # Cache result
        self._cached_results[path] = result
        
        return result
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a pattern.
        
        Args:
            path: Path to check
            pattern: Pattern to match
            
        Returns:
            True if path matches pattern, False otherwise
        """
        # Handle directory-only patterns
        if pattern.endswith('/'):
            if not os.path.isdir(path):
                return False
            pattern = pattern[:-1]
        
        # Handle simple glob patterns
        if '*' in pattern or '?' in pattern or '[' in pattern:
            return fnmatch.fnmatch(path, pattern)
        
        # Handle exact matches
        if pattern == path:
            return True
        
        # Handle directory prefix matches
        if pattern.endswith('/'):
            return path.startswith(pattern)
        
        # Handle file matches in directories
        if os.path.isdir(path):
            return False
        
        # Handle path prefix matches
        dir_path = os.path.dirname(path)
        base_name = os.path.basename(path)
        pattern_dir = os.path.dirname(pattern)
        pattern_base = os.path.basename(pattern)
        
        if pattern_dir and dir_path.endswith(pattern_dir):
            return fnmatch.fnmatch(base_name, pattern_base)
        
        return False
```

### File System Monitor Factory

```python
# fs_monitor/factory.py
import platform
import logging
import os
from typing import Optional

from .base import FileSystemMonitor
from .linux import LinuxFileSystemMonitor, HAS_INOTIFY
from .macos import MacOSFileSystemMonitor, HAS_FSEVENTS
from .windows import WindowsFileSystemMonitor, HAS_WIN32
from .fallback import FallbackFileSystemMonitor
from .queue import ChangeDetectionQueue
from .filter import GitIgnoreFilter

logger = logging.getLogger(__name__)

class FileSystemMonitorFactory:
    """Factory for creating file system monitors based on platform."""
    
    @staticmethod
    def create_monitor(config) -> FileSystemMonitor:
        """Create a file system monitor.
        
        Args:
            config: Configuration manager
            
        Returns:
            An instance of FileSystemMonitor
        """
        # Create filter
        filter_obj = GitIgnoreFilter(config)
        
        # Create change queue
        change_queue = ChangeDetectionQueue(config)
        change_queue.set_filter(filter_obj)
        
        # Determine platform
        system = platform.system()
        
        # Create platform-specific monitor
        monitor = None
        if system == 'Linux' and HAS_INOTIFY:
            try:
                monitor = LinuxFileSystemMonitor(config, change_queue)
                logger.info("Using Linux inotify monitor")
            except ImportError:
                logger.warning("Failed to create Linux monitor, falling back to polling")
                
        elif system == 'Darwin' and HAS_FSEVENTS:
            try:
                monitor = MacOSFileSystemMonitor(config, change_queue)
                logger.info("Using macOS FSEvents monitor")
            except ImportError:
                logger.warning("Failed to create macOS monitor, falling back to polling")
                
        elif system == 'Windows' and HAS_WIN32:
            try:
                monitor = WindowsFileSystemMonitor(config, change_queue)
                logger.info("Using Windows monitor")
            except ImportError:
                logger.warning("Failed to create Windows monitor, falling back to polling")
        
        # Fall back to polling monitor if platform-specific monitor couldn't be created
        if monitor is None:
            monitor = FallbackFileSystemMonitor(config, change_queue)
            logger.info("Using fallback polling monitor")
        
        return monitor
```

## Testing Strategy

To ensure that the file system monitoring component works correctly across different platforms, we will implement comprehensive tests:

1. **Unit Tests**:
   - Test each monitor implementation independently
   - Test the change queue with various event scenarios
   - Test the GitIgnoreFilter with different patterns

2. **Integration Tests**:
   - Test full file system monitoring with actual file changes
   - Verify that events are properly detected and processed

3. **Platform-Specific Tests**:
   - Test Linux inotify implementation
   - Test macOS FSEvents implementation
   - Test Windows ReadDirectoryChangesW implementation
   - Test fallback polling implementation

4. **Performance Tests**:
   - Test with large number of files
   - Test with rapid file changes
   - Test resource usage under load

## Implementation Plan

1. Implement the base classes and interfaces
   - FileSystemMonitor abstract base class
   - ChangeEvent data structure
   - ChangeDetectionQueue

2. Implement the platform-specific monitors
   - LinuxFileSystemMonitor
   - MacOSFileSystemMonitor
   - WindowsFileSystemMonitor
   - FallbackFileSystemMonitor

3. Implement the event filtering
   - GitIgnoreFilter
   - Configuration-based filtering

4. Implement the factory and initialization
   - FileSystemMonitorFactory
   - Environment detection

5. Implement tests for each component

6. Implement end-to-end integration tests

## Conclusion

This implementation plan provides a comprehensive approach to file system monitoring that:

1. Uses efficient platform-specific APIs when available
2. Gracefully falls back to polling when needed
3. Provides debouncing and filtering of events
4. Handles large codebases efficiently
5. Automatically respects .gitignore patterns
6. Manages resources carefully
7. Provides a thread-safe interface for other components

The implementation will be tested across different platforms to ensure reliable operation in all environments.
