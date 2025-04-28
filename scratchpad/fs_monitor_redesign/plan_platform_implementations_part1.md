# File System Monitor Redesign: Platform Implementations Part 1 - Overview and Base Class

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of platform-specific file system monitors for the fs_monitor component. The component needs to support multiple platforms with different file system monitoring APIs:

1. Linux - Using inotify
2. macOS - Using FSEvents
3. Windows - Using ReadDirectoryChangesW
4. Fallback - For unsupported platforms or when native APIs fail

Each implementation needs to:
- Detect file system events at the OS level
- Convert platform-specific events to our uniform event model
- Forward events to the event dispatcher
- Support efficient resource management
- Handle platform-specific edge cases

## Implementation Structure

The platform-specific implementations will be organized into the following files:

1. `src/dbp/fs_monitor/monitor_base.py` - Abstract base class for platform monitors
2. `src/dbp/fs_monitor/linux.py` - Linux implementation using inotify
3. `src/dbp/fs_monitor/macos.py` - macOS implementation using FSEvents
4. `src/dbp/fs_monitor/windows.py` - Windows implementation using ReadDirectoryChangesW
5. `src/dbp/fs_monitor/fallback.py` - Fallback polling implementation
6. `src/dbp/fs_monitor/factory.py` - Factory for creating the appropriate monitor

## Monitor Base Class

The abstract base class will define the common interface for all platform-specific monitors:

```python
# src/dbp/fs_monitor/monitor_base.py

import abc
import threading
import logging
from typing import Dict, Set, List, Optional, Callable, Any

from .event_types import EventType, FileSystemEvent
from .event_dispatcher import EventDispatcher
from .watch_manager import WatchManager

logger = logging.getLogger(__name__)

class MonitorBase(abc.ABC):
    """
    [Class intent]
    Abstract base class for platform-specific file system monitors.
    
    [Design principles]
    - Common interface for all platform implementations
    - Platform-specific event detection and conversion
    - Resource management abstraction
    
    [Implementation details]
    - Defines common monitor interface
    - Provides platform-independent utility methods
    - Abstracts platform-specific resource handling
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the base monitor.
        
        [Design principles]
        - Common initialization for all monitors
        - Reference to shared components
        
        [Implementation details]
        - Stores references to watch_manager and event_dispatcher
        - Initializes basic state tracking
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        self._watch_manager = watch_manager
        self._event_dispatcher = event_dispatcher
        self._running = False
        self._lock = threading.RLock()
    
    @abc.abstractmethod
    def start(self) -> None:
        """
        [Function intent]
        Start the file system monitor.
        
        [Design principles]
        - Platform-specific startup sequence
        
        [Implementation details]
        - Each platform must implement its own startup logic
        """
        pass
    
    @abc.abstractmethod
    def stop(self) -> None:
        """
        [Function intent]
        Stop the file system monitor.
        
        [Design principles]
        - Platform-specific cleanup
        
        [Implementation details]
        - Each platform must implement its own cleanup logic
        """
        pass
    
    @abc.abstractmethod
    def add_watch(self, path: str) -> Any:
        """
        [Function intent]
        Add a watch for a path.
        
        [Design principles]
        - Platform-specific watch creation
        
        [Implementation details]
        - Each platform must implement its own watch creation logic
        
        Args:
            path: Absolute path to watch
            
        Returns:
            Platform-specific watch descriptor or handle
        """
        pass
    
    @abc.abstractmethod
    def remove_watch(self, path: str, descriptor: Any) -> None:
        """
        [Function intent]
        Remove a watch for a path.
        
        [Design principles]
        - Platform-specific watch removal
        
        [Implementation details]
        - Each platform must implement its own watch removal logic
        
        Args:
            path: Absolute path that was being watched
            descriptor: Platform-specific watch descriptor or handle
        """
        pass
    
    def dispatch_event(self, event_type: EventType, path: str, old_target: Optional[str] = None,
                       new_target: Optional[str] = None) -> None:
        """
        [Function intent]
        Dispatch an event to the event dispatcher.
        
        [Design principles]
        - Common event dispatch logic
        - Uniform event creation
        
        [Implementation details]
        - Creates FileSystemEvent object
        - Passes it to the event dispatcher
        
        Args:
            event_type: Type of the event
            path: Path affected by the event
            old_target: Previous target path for symlink target change events
            new_target: New target path for symlink creation or target change events
        """
        if not self._running:
            logger.debug(f"Monitor not running, event {event_type} for {path} will not be dispatched")
            return
        
        event = FileSystemEvent(event_type, path, old_target, new_target)
        self._event_dispatcher.dispatch_event(event)
    
    @property
    def is_running(self) -> bool:
        """
        [Function intent]
        Check if the monitor is running.
        
        [Design principles]
        - Simple state access
        
        [Implementation details]
        - Returns the current running state
        
        Returns:
            True if the monitor is running, False otherwise
        """
        return self._running
```

## Factory Implementation

The factory will be responsible for creating the appropriate monitor based on the platform:

```python
# src/dbp/fs_monitor/factory.py

import platform
import logging
from typing import Optional

from .monitor_base import MonitorBase
from .event_dispatcher import EventDispatcher
from .watch_manager import WatchManager
from .exceptions import WatchCreationError

logger = logging.getLogger(__name__)

def create_platform_monitor(watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> MonitorBase:
    """
    [Function intent]
    Create the appropriate platform-specific monitor.
    
    [Design principles]
    - Platform detection and selection
    - Graceful fallback
    
    [Implementation details]
    - Detects the current platform
    - Creates the appropriate monitor
    - Falls back to polling monitor if native monitor fails
    
    Args:
        watch_manager: Reference to the watch manager
        event_dispatcher: Reference to the event dispatcher
        
    Returns:
        Platform-specific monitor instance
        
    Raises:
        WatchCreationError: If no monitor can be created
    """
    system = platform.system().lower()
    
    # Try to create the appropriate monitor
    monitor = None
    
    try:
        if system == 'linux':
            from .linux import LinuxMonitor
            monitor = LinuxMonitor(watch_manager, event_dispatcher)
            logger.info("Created Linux monitor (inotify)")
        elif system == 'darwin':
            from .macos import MacOSMonitor
            monitor = MacOSMonitor(watch_manager, event_dispatcher)
            logger.info("Created macOS monitor (FSEvents)")
        elif system == 'windows':
            from .windows import WindowsMonitor
            monitor = WindowsMonitor(watch_manager, event_dispatcher)
            logger.info("Created Windows monitor (ReadDirectoryChangesW)")
        else:
            logger.warning(f"Unsupported platform: {system}")
    except Exception as e:
        logger.error(f"Error creating platform monitor: {e}")
    
    # Fall back to polling monitor if native monitor failed or platform is unsupported
    if monitor is None:
        try:
            from .fallback import FallbackMonitor
            monitor = FallbackMonitor(watch_manager, event_dispatcher)
            logger.warning("Using fallback polling monitor")
        except Exception as e:
            logger.error(f"Error creating fallback monitor: {e}")
            raise WatchCreationError(f"Failed to create any monitor: {e}")
    
    return monitor
```

In subsequent parts, we will detail the implementation of each platform-specific monitor:
- Part 2: Linux Implementation (inotify)
- Part 3: macOS Implementation (FSEvents)
- Part 4: Windows Implementation (ReadDirectoryChangesW)
- Part 5: Fallback Implementation
