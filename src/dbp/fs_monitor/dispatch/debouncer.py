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
# This file implements the debouncing mechanism for the file system monitor component.
# It prevents notification storms by delaying and consolidating rapid file system events,
# reducing the number of notifications sent to listeners for rapidly changing files.
###############################################################################
# [Source file design principles]
# - Prevent notification storms for rapidly changing files
# - Support per-listener debounce delay configuration
# - Efficient dispatching through priority queue scheduling
# - Thread-safe operations for concurrent access
# - Minimal resource utilization during idle periods
###############################################################################
# [Source file constraints]
# - Must handle concurrent event additions from multiple sources
# - Must properly manage dispatch timing for all events
# - Must support variable debounce delays per listener
# - Must ensure proper resource cleanup during shutdown
# - Must support high event rates without excessive CPU usage
###############################################################################
# [Dependencies]
# system:time
# system:threading
# system:logging
# system:typing
# system:dataclasses
# system:heapq
# codebase:src/dbp/fs_monitor/event_types.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T15:25:00Z : Renamed Debouncer class to EventDebouncer by CodeAssistant
# * Changed class name to match import in dispatch/__init__.py
# * Fixed "cannot import name 'EventDebouncer'" error during server startup
# 2025-04-29T14:00:00Z : Fixed import path for watch_manager by CodeAssistant
# * Changed import from .watch_manager to ..watch_manager
# * Fixed import error causing server startup failure
# 2025-04-29T13:40:00Z : Fixed import path for event_types by CodeAssistant
# * Changed import from .event_types to ..core.event_types 
# * Fixed "No module named 'dbp.fs_monitor.dispatch.event_types'" error
# 2025-04-29T00:08:00Z : Initial implementation of debouncer for fs_monitor redesign by CodeAssistant
# * Created Debouncer class for event debouncing
# * Implemented PendingEvent dataclass for priority queue
# * Added scheduler thread for efficient event processing
###############################################################################

import time
import threading
import logging
from typing import Dict, Set, List, Any, Optional, Callable
from dataclasses import dataclass
import heapq

from ..core.event_types import EventType, FileSystemEvent

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


class EventDebouncer:
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
                    # Get matching listeners - we can't import WatchManager here due to circular imports
                    # The watch manager instance must be passed in by the event dispatcher
                    from ..watch_manager import WatchManager  # This is a placeholder
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
