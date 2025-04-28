# File System Monitor Redesign: Event Dispatcher Implementation Plan

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

- [File System Monitor Design](../../doc/design/FILE_SYSTEM_MONITOR.md) - Detailed design document for the redesigned fs_monitor component
- [Design](../../doc/DESIGN.md) - Core architectural principles and design decisions
- [Configuration](../../doc/CONFIGURATION.md) - Configuration options for the fs_monitor component

## Overview

This plan details the implementation of the event dispatcher for the fs_monitor component. The event dispatcher is responsible for:

1. Receiving raw file system events from platform-specific monitors
2. Debouncing events to prevent notification storms
3. Dispatching processed events to appropriate listeners
4. Managing dispatcher threads
5. Providing a central hub for event processing

## Implementation Details

### File Structure

The implementation will involve creating or modifying the following files:

1. `src/dbp/fs_monitor/event_dispatcher.py` - Event dispatcher implementation
2. `src/dbp/fs_monitor/debouncer.py` - Event debouncing logic
3. `src/dbp/fs_monitor/thread_manager.py` - Thread management and scheduling

### Event Debouncing

First, we'll implement a debouncer to efficiently manage and throttle events:

```python
# src/dbp/fs_monitor/debouncer.py

import time
import threading
import logging
from typing import Dict, Set, List, Any, Optional, Callable
from dataclasses import dataclass
import heapq

from .event_types import EventType, FileSystemEvent

logger = logging.getLogger(__name__)

@dataclass(order=True)
class PendingEvent:
    """
    [Class intent]
    Stores a filesystem event that is waiting to be dispatched after its debounce delay.
    
    [Design principles]
    - Efficient event scheduling with variable delays
    - Support for priority queue operations
    
    [Implementation details]
    - Comparable for use in a priority queue
    - Dispatched_time determines when the event should be dispatched
    - Event contains the original filesystem event
    
    Attributes:
        dispatch_time: When the event should be dispatched (in seconds since epoch)
        event: The filesystem event to dispatch
    """
    dispatch_time: float
    event: FileSystemEvent = None  # This will be compared by reference, so it's fine


class Debouncer:
    """
    [Class intent]
    Manages event debouncing for file system events.
    
    [Design principles]
    - Prevent notification storms for rapidly changing files
    - Support per-listener debounce delay configuration
    - Efficient dispatch of debounced events
    
    [Implementation details]
    - Uses a priority queue for event scheduling
    - Maintains a set of pending events for each path
    - Supports listener-specific debounce delays
    """
    
    def __init__(self, dispatch_callback: Callable[[FileSystemEvent, List[int]], None]) -> None:
        """
        [Function intent]
        Initialize a new debouncer.
        
        [Design principles]
        - Clean initialization
        - Thread safety
        
        [Implementation details]
        - Initializes empty data structures
        - Sets up dispatch callback
        
        Args:
            dispatch_callback: Function to call when an event is ready to be dispatched
        """
        self._lock = threading.RLock()
        self._pending_events: List[PendingEvent] = []  # Priority queue (heap)
        self._path_events: Dict[str, Set[EventType]] = {}  # Events pending for each path
        self._dispatch_callback = dispatch_callback
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_running = False
        self._default_debounce_ms = 100  # Default debounce delay in milliseconds
    
    def start(self) -> None:
        """
        [Function intent]
        Start the debouncer scheduler thread.
        
        [Design principles]
        - Automatic event processing
        
        [Implementation details]
        - Creates and starts a daemon thread for event processing
        """
        with self._lock:
            if self._scheduler_thread is not None and self._scheduler_thread.is_alive():
                logger.warning("Debouncer scheduler thread already running")
                return
            
            self._scheduler_running = True
            self._scheduler_thread = threading.Thread(
                target=self._event_scheduler_loop,
                daemon=True,
                name="FSMonitor-Debouncer"
            )
            self._scheduler_thread.start()
            logger.debug("Started debouncer scheduler thread")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the debouncer scheduler thread.
        
        [Design principles]
        - Clean resource management
        
        [Implementation details]
        - Sets flag to stop scheduler thread
        - Clears all pending events
        """
        with self._lock:
            self._scheduler_running = False
            self._pending_events = []
            self._path_events.clear()
            logger.debug("Stopped debouncer scheduler thread")
    
    def add_event(self, event: FileSystemEvent, listener_ids: List[int], 
                  listener_debounce_delays: Dict[int, int]) -> None:
        """
        [Function intent]
        Add a new event to be debounced and eventually dispatched.
        
        [Design principles]
        - Support for listener-specific debounce delays
        - Prevention of duplicate events for same path
        
        [Implementation details]
        - Calculates dispatch time based on debounce delays
        - Adds event to priority queue
        - Updates path events map
        
        Args:
            event: The filesystem event to debounce
            listener_ids: List of listener IDs that should receive the event
            listener_debounce_delays: Dict mapping listener IDs to their debounce delays in ms
        """
        with self._lock:
            # Calculate the maximum debounce delay among listeners
            max_debounce_ms = self._default_debounce_ms
            for listener_id in listener_ids:
                delay = listener_debounce_delays.get(listener_id, self._default_debounce_ms)
                max_debounce_ms = max(max_debounce_ms, delay)
            
            # Calculate dispatch time
            now = time.time()
            dispatch_time = now + (max_debounce_ms / 1000.0)
            
            # Check if we already have events pending for this path
            path = event.path
            if path in self._path_events:
                # We already have events pending for this path
                # Check if we have this specific event type pending
                if event.event_type in self._path_events[path]:
                    # We already have this event type pending, so we'll just update its dispatch time
                    # by removing all pending events of this type and re-adding them with the new time
                    for i in range(len(self._pending_events)):
                        pending_event = self._pending_events[i]
                        if pending_event.event.path == path and pending_event.event.event_type == event.event_type:
                            # Update the dispatch time
                            self._pending_events[i].dispatch_time = dispatch_time
                            # Re-heapify
                            heapq.heapify(self._pending_events)
                            return
                
                # Add the event type to the set of pending events for this path
                self._path_events[path].add(event.event_type)
            else:
                # First event for this path
                self._path_events[path] = {event.event_type}
            
            # Add the event to the priority queue
            pending_event = PendingEvent(dispatch_time, event)
            heapq.heappush(self._pending_events, pending_event)
    
    def _event_scheduler_loop(self) -> None:
        """
        [Function intent]
        Main loop for the event scheduler thread.
        
        [Design principles]
        - Efficient event dispatching
        - Sleep when no events are pending
        
        [Implementation details]
        - Continuously processes events in the priority queue
        - Dispatches events when their scheduled time arrives
        - Sleeps when no events are pending
        """
        while self._scheduler_running:
            dispatch_now = []
            
            with self._lock:
                # Check if we have any events to dispatch
                now = time.time()
                
                while self._pending_events and self._pending_events[0].dispatch_time <= now:
                    # Pop the event from the queue
                    pending_event = heapq.heappop(self._pending_events)
                    event = pending_event.event
                    
                    # Remove from path events map
                    if event.path in self._path_events:
                        self._path_events[event.path].discard(event.event_type)
                        if not self._path_events[event.path]:
                            del self._path_events[event.path]
                    
                    # Add to list of events to dispatch
                    dispatch_now.append(event)
            
            # Dispatch events outside the lock
            for event in dispatch_now:
                try:
                    # Call the dispatch callback
                    from .watch_manager import WatchManager
                    manager = WatchManager()  # This is a placeholder, actual implementation will get the manager instance
                    listener_ids = manager.get_matching_listeners(event.path)
                    if listener_ids:
                        self._dispatch_callback(event, listener_ids)
                except Exception as e:
                    logger.error(f"Error dispatching event {event}: {e}")
            
            # Sleep until next event or a short time
            with self._lock:
                if not self._pending_events:
                    # No events, sleep for a short time
                    time.sleep(0.1)
                else:
                    # Sleep until the next event
                    next_event_time = self._pending_events[0].dispatch_time
                    now = time.time()
                    if next_event_time > now:
                        time.sleep(min(next_event_time - now, 0.1))
                    else:
                        # Don't sleep, process the event immediately
                        pass
    
    def set_default_debounce_ms(self, ms: int) -> None:
        """
        [Function intent]
        Set the default debounce delay in milliseconds.
        
        [Design principles]
        - Configurable behavior
        
        [Implementation details]
        - Updates the default debounce delay
        
        Args:
            ms: Debounce delay in milliseconds
        """
        self._default_debounce_ms = ms
```

### Thread Manager

Next, let's implement a thread manager to handle event dispatching threads:

```python
# src/dbp/fs_monitor/thread_manager.py

import threading
import logging
import time
import queue
from typing import Dict, List, Callable, Optional
from enum import Enum, auto
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ThreadPriority(Enum):
    """
    [Class intent]
    Defines priorities for dispatcher threads.
    
    [Design principles]
    - Simple prioritization of tasks
    - Alignment with OS thread priorities
    
    [Implementation details]
    - Enum values correspond to priority levels
    """
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


@dataclass
class DispatchTask:
    """
    [Class intent]
    Represents a task to be executed by a dispatcher thread.
    
    [Design principles]
    - Encapsulate task information
    - Support for task prioritization
    
    [Implementation details]
    - Contains target function and arguments
    - Stores creation time for diagnostics
    
    Attributes:
        target: Function to call
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        created_at: When the task was created (for diagnostics)
    """
    target: Callable
    args: tuple = ()
    kwargs: dict = None
    created_at: float = 0.0
    
    def __post_init__(self):
        """Initialize default values and record creation time"""
        if self.kwargs is None:
            self.kwargs = {}
        self.created_at = time.time()


class ThreadManager:
    """
    [Class intent]
    Manages threads for event dispatching.
    
    [Design principles]
    - Efficient thread utilization
    - Support for task prioritization
    - Graceful shutdown handling
    
    [Implementation details]
    - Maintains a pool of worker threads
    - Uses a queue for task distribution
    - Supports thread priority configuration
    """
    
    def __init__(self, num_threads: int = 1, priority: ThreadPriority = ThreadPriority.NORMAL) -> None:
        """
        [Function intent]
        Initialize a new thread manager.
        
        [Design principles]
        - Configurable thread pool size
        - Support for thread priority
        
        [Implementation details]
        - Creates task queue
        - Initializes worker threads
        
        Args:
            num_threads: Number of worker threads to create
            priority: Priority level for the worker threads
        """
        self._num_threads = max(1, num_threads)  # At least one thread
        self._priority = priority
        self._task_queue = queue.Queue()
        self._threads: List[threading.Thread] = []
        self._running = False
        self._lock = threading.RLock()
    
    def start(self) -> None:
        """
        [Function intent]
        Start the thread manager.
        
        [Design principles]
        - Automatic thread initialization
        
        [Implementation details]
        - Creates and starts worker threads
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("ThreadManager already running")
                return
            
            self._running = True
            
            for i in range(self._num_threads):
                thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name=f"FSMonitor-Worker-{i}"
                )
                self._threads.append(thread)
                thread.start()
            
            logger.debug(f"Started {self._num_threads} worker threads")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the thread manager.
        
        [Design principles]
        - Graceful shutdown
        
        [Implementation details]
        - Clears running flag
        - Adds poison pills to task queue
        - Waits for threads to terminate
        """
        with self._lock:
            if not self._running:
                logger.debug("ThreadManager already stopped")
                return
            
            self._running = False
            
            # Add poison pills to wake up all threads
            for _ in range(self._num_threads):
                self._task_queue.put(None)
            
            # Wait for threads to terminate
            for thread in self._threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)
            
            # Clear thread list
            self._threads.clear()
            logger.debug("Stopped all worker threads")
    
    def submit_task(self, target: Callable, *args, **kwargs) -> None:
        """
        [Function intent]
        Submit a task for execution by a worker thread.
        
        [Design principles]
        - Simple API for task submission
        
        [Implementation details]
        - Creates a task object
        - Adds it to the task queue
        
        Args:
            target: Function to call
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
        """
        if not self._running:
            logger.warning("ThreadManager not running, task will not be executed")
            return
        
        task = DispatchTask(target, args, kwargs)
        self._task_queue.put(task)
    
    def _worker_loop(self) -> None:
        """
        [Function intent]
        Main loop for worker threads.
        
        [Design principles]
        - Continuous task processing
        - Error handling
        
        [Implementation details]
        - Gets tasks from queue
        - Executes tasks
        - Handles errors
        """
        while self._running:
            try:
                # Get a task from the queue
                task = self._task_queue.get()
                
                # Check for poison pill
                if task is None:
                    break
                
                # Execute the task
                try:
                    task.target(*task.args, **(task.kwargs or {}))
                except Exception as e:
                    logger.error(f"Error executing task: {e}")
                finally:
                    # Mark the task as done
                    self._task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
        
        logger.debug("Worker thread exiting")
    
    def set_thread_priority(self, priority: ThreadPriority) -> None:
        """
        [Function intent]
        Set the priority for worker threads.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates the priority setting
        - This is a placeholder, actual implementation varies by platform
        
        Args:
            priority: New priority level
        """
        self._priority = priority
        
        # Actual implementation of thread priority setting depends on the platform
        # This would require platform-specific code for Windows, Linux, and macOS
        # For now, this is just a placeholder
```

### Event Dispatcher

Now, let's implement the event dispatcher, which ties together the debouncer and thread manager:

```python
# src/dbp/fs_monitor/event_dispatcher.py

import threading
import logging
from typing import Dict, List, Optional, Any, Set, Callable

from .event_types import EventType, FileSystemEvent
from .listener import FileSystemEventListener
from .debouncer import Debouncer
from .thread_manager import ThreadManager, ThreadPriority
from .watch_manager import WatchManager

logger = logging.getLogger(__name__)

class EventDispatcher:
    """
    [Class intent]
    Dispatches file system events to registered listeners.
    
    [Design principles]
    - Central hub for event processing
    - Thread safety
    - Efficient event routing
    - Support for debounced events
    
    [Implementation details]
    - Uses Debouncer for event throttling
    - Uses ThreadManager for dispatching events
    - Maintains a connection to the WatchManager
    """
    
    def __init__(self, watch_manager: WatchManager) -> None:
        """
        [Function intent]
        Initialize a new event dispatcher.
        
        [Design principles]
        - Clean initialization
        - Component linking
        
        [Implementation details]
        - Stores reference to watch manager
        - Creates debouncer and thread manager
        
        Args:
            watch_manager: Reference to the watch manager
        """
        self._watch_manager = watch_manager
        self._lock = threading.RLock()
        self._debouncer = Debouncer(self._dispatch_debounced_event)
        self._thread_manager = ThreadManager(num_threads=1, priority=ThreadPriority.NORMAL)
        self._started = False
    
    def start(self) -> None:
        """
        [Function intent]
        Start the event dispatcher.
        
        [Design principles]
        - Clean startup sequence
        
        [Implementation details]
        - Starts the debouncer and thread manager
        - Sets started flag
        """
        with self._lock:
            if self._started:
                logger.warning("EventDispatcher already started")
                return
            
            self._debouncer.start()
            self._thread_manager.start()
            self._started = True
            
            logger.debug("Started event dispatcher")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the event dispatcher.
        
        [Design principles]
        - Clean shutdown sequence
        
        [Implementation details]
        - Stops the debouncer and thread manager
        - Clears started flag
        """
        with self._lock:
            if not self._started:
                logger.debug("EventDispatcher already stopped")
                return
            
            self._debouncer.stop()
            self._thread_manager.stop()
            self._started = False
            
            logger.debug("Stopped event dispatcher")
    
    def dispatch_event(self, event: FileSystemEvent) -> None:
        """
        [Function intent]
        Dispatch a file system event to interested listeners.
        
        [Design principles]
        - Event routing based on path patterns
        - Support for debouncing
        
        [Implementation details]
        - Gets matching listeners from watch manager
        - Adds event to debouncer
        
        Args:
            event: The file system event to dispatch
        """
        if not self._started:
            logger.warning("EventDispatcher not started, event will not be dispatched")
            return
        
        # Get matching listeners from watch manager
        listener_ids = self._watch_manager.get_matching_listeners(event.path)
        
        if not listener_ids:
            logger.debug(f"No listeners found for path {event.path}, event will not be dispatched")
            return
        
        # Collect debounce delays for each listener
        listener_debounce_delays = {}
        for listener_id in listener_ids:
            listener = self._watch_manager.get_listener(listener_id)
            if listener:
                listener_debounce_delays[listener_id] = listener.debounce_delay_ms
        
        # Add event to debouncer
        self._debouncer.add_event(event, listener_ids, listener_debounce_delays)
    
    def _dispatch_debounced_event(self, event: FileSystemEvent, listener_ids: List[int]) -> None:
        """
        [Function intent]
        Dispatch a debounced event to interested listeners.
        
        [Design principles]
        - Thread safety
        - Error handling for individual listeners
        
        [Implementation details]
        - Retrieves listeners from watch manager
        - Submits dispatcher tasks to thread manager
        
        Args:
            event: The file system event to dispatch
            listener_ids: List of listener IDs to dispatch to
        """
        if not self._started:
            logger.warning("EventDispatcher not started, event will not be dispatched")
            return
        
        # For each listener, submit a task to the thread manager
        for listener_id in listener_ids:
            listener = self._watch_manager.get_listener(listener_id)
            if not listener:
                logger.warning(f"Listener {listener_id} not found, skipping event dispatch")
                continue
            
            # Submit task to thread manager
            self._thread_manager.submit_task(
                self._call_listener_method,
                listener,
                event
            )
    
    def _call_listener_method(self, listener: FileSystemEventListener, event: FileSystemEvent) -> None:
        """
        [Function intent]
        Call the appropriate method on a listener based on the event type.
        
        [Design principles]
        - Error handling
        - Event type routing
        
        [Implementation details]
        - Selects listener method based on event type
        - Handles exceptions from listener methods
        
        Args:
            listener: The listener to call
            event: The file system event
        """
        try:
            # Call the appropriate method based on the event type
            if event.event_type == EventType.FILE_CREATED:
                listener.on_file_created(event.path)
            elif event.event_type == EventType.FILE_MODIFIED:
                listener.on_file_modified(event.path)
            elif event.event_type == EventType.FILE_DELETED:
                listener.on_file_deleted(event.path)
            elif event.event_type == EventType.DIRECTORY_CREATED:
                listener.on_directory_created(event.path)
            elif event.event_type == EventType.DIRECTORY_DELETED:
                listener.on_directory_deleted(event.path)
            elif event.event_type == EventType.SYMLINK_CREATED:
                listener.on_symlink_created(event.path, event.new_target)
            elif event.event_type == EventType.SYMLINK_DELETED:
                listener.on_symlink_deleted(event.path)
            elif event.event_type == EventType.SYMLINK_TARGET_CHANGED:
                listener.on_symlink_target_changed(event.path, event.old_target, event.new_target)
            else:
                logger.warning(f"Unknown event type: {event.event_type}")
        except Exception as e:
            logger.error(f"Error calling listener method: {e}")
    
    def configure(self, thread_count: int, thread_priority: ThreadPriority, default_debounce_ms: int) -> None:
        """
        [Function intent]
        Configure the event dispatcher.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates thread manager and debouncer configuration
        
        Args:
            thread_count: Number of worker threads
            thread_priority: Priority of worker threads
            default_debounce_ms: Default debounce delay in milliseconds
        """
        with self._lock:
            # Need to stop and restart components for configuration to take effect
            was_started = self._started
            
            if was_started:
                self.stop()
            
            # Update thread manager
            self._thread_manager = ThreadManager(num_threads=thread_count, priority=thread_priority)
            
            # Update debouncer
            self._debouncer.set_default_debounce_ms(default_debounce_ms)
            
            if was_started:
                self.start()
```

## Testing Strategy

The event dispatcher implementation should be tested with the following strategies:

1. **Unit Tests**:
   - Test debouncer with various delays
   - Test thread manager with multiple threads
   - Test event dispatcher dispatching to multiple listeners

2. **Integration Tests**:
   - Test debouncer and thread manager working together
   - Test event dispatcher with watch manager and mock listeners

3. **Performance Tests**:
   - Test with high event rates
   - Measure dispatch latency
   - Verify thread resource usage

## Key Test Cases

1. **Debouncer Tests**:
   - Test events are dispatched after delay
   - Test events with same path and type are debounced
   - Test events with different paths are not debounced
   - Test listener-specific debounce delays

2. **Thread Manager Tests**:
   - Test submitting and executing tasks
   - Test graceful shutdown
   - Test task execution order
   - Test error handling during task execution

3. **Event Dispatcher Tests**:
   - Test dispatching various event types
   - Test events are routed to correct listener methods
   - Test error handling during dispatch
   - Test configuration changes

## Integration with Other Components

The event dispatcher is a critical component that connects platform-specific monitors with the watch manager:

1. **Platform-Specific Monitors**: Send raw events to the dispatcher
2. **Watch Manager**: Provides information about listeners and patterns
3. **Listeners**: Receive processed events from the dispatcher

## Configuration Parameters

The event dispatcher should respect the following configuration parameters:

1. `fs_monitor.default_debounce_ms`: Default debounce delay in milliseconds
2. `fs_monitor.thread_priority`: Priority for dispatcher threads
3. `fs_monitor.thread_count`: Number of worker threads for event dispatching

## Next Steps

After implementing the event dispatcher:

1. Update plan_progress.md to mark this task as completed
2. Implement platform-specific monitors
3. Integrate all components into a cohesive system
